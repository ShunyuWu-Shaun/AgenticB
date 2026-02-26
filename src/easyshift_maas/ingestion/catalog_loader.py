from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Protocol

import yaml
from pydantic import BaseModel, ConfigDict, Field

from easyshift_maas.core.contracts import (
    CatalogLoadMode,
    DataSourceKind,
    DataSourceProfile,
    FieldDefinition,
    FieldDictionary,
    PointBinding,
    PointCatalog,
    SceneMetadata,
)


class CatalogLoadResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    catalog: PointCatalog
    field_dictionary: FieldDictionary
    source_profiles: list[DataSourceProfile] = Field(default_factory=list)
    scene_metadata: SceneMetadata
    template_override: dict[str, Any] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    pending_confirmations: list[str] = Field(default_factory=list)


class CatalogLoaderProtocol(Protocol):
    def load(
        self,
        *,
        yaml_text: str | None = None,
        yaml_path: str | None = None,
        mode: CatalogLoadMode = CatalogLoadMode.STANDARD,
    ) -> CatalogLoadResult: ...


class YamlCatalogLoader:
    """Load point catalogs from standard/legacy YAML into canonical contracts."""

    _LEGACY_RESERVED_KEYS = {
        "scene",
        "datasources",
        "point_catalog",
        "field_dictionary",
        "template_override",
        "redis_config",
        "mysql_config",
        "historical_data",
        "duration",
        "heartbeat_db",
        "threshold",
        "raw_keys",
        "realtime_raw_keys",
        "nox_keys",
        "safety_limits",
        "safety_realtime_keys",
        "output_var",
        "inputs",
        "real_time_inputs",
        "reference_values_send",
    }
    _LEGACY_SECTION_HINTS = {
        "inputs",
        "real_time_inputs",
        "realtime_inputs",
        "raw_keys",
        "realtime_raw_keys",
        "reference_values_send",
        "output_var",
    }

    def load(
        self,
        *,
        yaml_text: str | None = None,
        yaml_path: str | None = None,
        mode: CatalogLoadMode = CatalogLoadMode.STANDARD,
    ) -> CatalogLoadResult:
        payload = self._read_payload(yaml_text=yaml_text, yaml_path=yaml_path)
        if mode == CatalogLoadMode.STANDARD:
            return self._load_standard(payload)
        return self._load_legacy(payload)

    def _read_payload(self, *, yaml_text: str | None, yaml_path: str | None) -> dict[str, Any]:
        if bool(yaml_text) == bool(yaml_path):
            raise ValueError("exactly one of yaml_text or yaml_path must be provided")

        if yaml_text is not None:
            loaded = yaml.safe_load(yaml_text)
        else:
            loaded = yaml.safe_load(Path(str(yaml_path)).read_text(encoding="utf-8"))

        if not isinstance(loaded, dict):
            raise ValueError("yaml root must be a mapping")
        return loaded

    def _load_standard(self, payload: dict[str, Any]) -> CatalogLoadResult:
        warnings: list[str] = []
        pending: list[str] = []

        scene_data = payload.get("scene", {"scene_id": "catalog-scene"})
        if "scene_id" not in scene_data:
            scene_data["scene_id"] = "catalog-scene"
        scene = SceneMetadata.model_validate(scene_data)

        profiles = self._parse_source_profiles(payload.get("datasources"), warnings)
        template_override = payload.get("template_override", {})
        if not isinstance(template_override, dict):
            warnings.append("template_override ignored: expected mapping")
            template_override = {}

        catalog_data = payload.get("point_catalog", {})
        bindings_raw = catalog_data.get("bindings", [])
        bindings: list[PointBinding] = []
        for idx, item in enumerate(bindings_raw):
            if not isinstance(item, dict):
                warnings.append(f"invalid binding at index {idx}: expected mapping")
                continue
            point_id = str(item.get("point_id") or item.get("id") or f"point_{idx}")
            source_type = str(item.get("source_type") or "redis").lower()
            source_ref = str(item.get("source_ref") or point_id)
            field_name = str(item.get("field_name") or self._sanitize_field_name(point_id))
            unit = str(item.get("unit") or "dimensionless")
            tags = item.get("tags") or []
            transform = item.get("transform")
            enabled = bool(item.get("enabled", True))
            try:
                binding = PointBinding(
                    point_id=point_id,
                    source_type=DataSourceKind(source_type),
                    source_ref=source_ref,
                    field_name=field_name,
                    unit=unit,
                    transform=None if transform is None else str(transform),
                    enabled=enabled,
                    tags=[str(tag) for tag in tags] if isinstance(tags, list) else [],
                )
                bindings.append(binding)
            except Exception as exc:  # noqa: BLE001
                warnings.append(f"invalid binding {point_id}: {exc}")

        if not bindings:
            raise ValueError("point_catalog.bindings cannot be empty in standard mode")
        bindings = self._deduplicate_binding_ids(bindings, warnings)

        catalog = PointCatalog(
            catalog_id=str(catalog_data.get("catalog_id") or f"{scene.scene_id}-catalog"),
            version=str(catalog_data.get("version") or "v1"),
            bindings=bindings,
            refresh_sec=int(catalog_data.get("refresh_sec") or 30),
            source_profile=str(catalog_data.get("source_profile") or "default"),
        )

        field_dictionary_raw = payload.get("field_dictionary")
        if field_dictionary_raw is not None:
            try:
                field_dictionary = FieldDictionary.model_validate(field_dictionary_raw)
            except Exception as exc:  # noqa: BLE001
                warnings.append(f"invalid field_dictionary, fallback to inferred fields: {exc}")
                field_dictionary = self._infer_field_dictionary(bindings)
        else:
            field_dictionary = self._infer_field_dictionary(bindings)
            pending.append("Field semantics were inferred from bindings; confirm semantic_label and controllable flags")

        if not profiles:
            pending.append("No datasource profile provided; configure conn_ref via env/file secret before runtime")

        return CatalogLoadResult(
            catalog=catalog,
            field_dictionary=field_dictionary,
            source_profiles=profiles,
            scene_metadata=scene,
            template_override=template_override,
            warnings=warnings,
            pending_confirmations=pending,
        )

    def _load_legacy(self, payload: dict[str, Any]) -> CatalogLoadResult:
        warnings: list[str] = []
        pending: list[str] = [
            "Legacy YAML converted with heuristics; manually confirm field mappings and units"
        ]

        scene = SceneMetadata(
            scene_id=str(payload.get("scene_id") or "legacy-scene"),
            scenario_type=str(payload.get("scenario_type") or "legacy"),
        )

        profiles = self._parse_legacy_profiles(payload, warnings)

        bindings: list[PointBinding] = []
        for key, value in payload.items():
            if key in self._LEGACY_RESERVED_KEYS:
                continue
            if self._looks_like_point_entry(key, value):
                field_name = self._sanitize_field_name(key)
                source_kind = DataSourceKind.REDIS
                if isinstance(value, dict):
                    source_name = str(value.get("source_type") or value.get("provider") or "redis").lower()
                    source_kind = DataSourceKind(source_name) if source_name in {"redis", "mysql"} else DataSourceKind.REDIS
                    source_ref = str(value.get("source_ref") or value.get("tag") or value.get("key") or key)
                    unit = str(value.get("unit") or "dimensionless")
                    tags = value.get("tags") or []
                    transform = value.get("transform")
                else:
                    source_ref = str(value) if isinstance(value, str) and value else key
                    unit = "dimensionless"
                    tags = []
                    transform = None

                bindings.append(
                    PointBinding(
                        point_id=str(key),
                        source_type=source_kind,
                        source_ref=source_ref,
                        field_name=field_name,
                        unit=unit,
                        transform=None if transform is None else str(transform),
                        enabled=True,
                        tags=[str(item) for item in tags] if isinstance(tags, list) else [],
                    )
                )

        if not bindings:
            bindings = self._extract_from_nested_inputs(payload)
            if bindings:
                warnings.append(
                    "legacy fallback parser used nested sections and auto-mapped point tags"
                )

        if not bindings:
            raise ValueError("no point-like entries found in legacy yaml")
        bindings = self._deduplicate_binding_ids(bindings, warnings)

        catalog = PointCatalog(
            catalog_id=f"{scene.scene_id}-catalog",
            version="legacy-v1",
            bindings=bindings,
            refresh_sec=int(payload.get("duration") or 30),
            source_profile="legacy-default",
        )

        field_dictionary = self._infer_field_dictionary(bindings)

        return CatalogLoadResult(
            catalog=catalog,
            field_dictionary=field_dictionary,
            source_profiles=profiles,
            scene_metadata=scene,
            template_override={},
            warnings=warnings,
            pending_confirmations=pending,
        )

    def _parse_source_profiles(self, datasources: Any, warnings: list[str]) -> list[DataSourceProfile]:
        if datasources is None:
            return []

        profiles: list[DataSourceProfile] = []
        items: list[tuple[str, Any]] = []

        if isinstance(datasources, dict):
            items = list(datasources.items())
        elif isinstance(datasources, list):
            items = [
                (str(item.get("name") or f"source_{idx}"), item)
                for idx, item in enumerate(datasources)
                if isinstance(item, dict)
            ]
        else:
            warnings.append("datasources ignored: expected mapping or list")
            return []

        for name, item in items:
            try:
                payload = dict(item)
                payload.setdefault("name", name)
                profiles.append(DataSourceProfile.model_validate(payload))
            except Exception as exc:  # noqa: BLE001
                warnings.append(f"invalid datasource profile '{name}': {exc}")

        return profiles

    def _parse_legacy_profiles(self, payload: dict[str, Any], warnings: list[str]) -> list[DataSourceProfile]:
        profiles: list[DataSourceProfile] = []

        if isinstance(payload.get("redis_config"), dict):
            profiles.append(
                DataSourceProfile(
                    name="legacy-redis",
                    kind=DataSourceKind.REDIS,
                    conn_ref="env:REFLEXFLOW_REDIS_CONN",
                )
            )
            warnings.append("legacy redis_config detected; using conn_ref=env:REFLEXFLOW_REDIS_CONN")

        if isinstance(payload.get("mysql_config"), dict):
            profiles.append(
                DataSourceProfile(
                    name="legacy-mysql",
                    kind=DataSourceKind.MYSQL,
                    conn_ref="env:REFLEXFLOW_MYSQL_CONN",
                )
            )
            warnings.append("legacy mysql_config detected; using conn_ref=env:REFLEXFLOW_MYSQL_CONN")

        if not profiles:
            profiles.append(
                DataSourceProfile(
                    name="legacy-redis",
                    kind=DataSourceKind.REDIS,
                    conn_ref="env:REFLEXFLOW_REDIS_CONN",
                )
            )
            warnings.append("no datasource block found; defaulted to redis env connection")

        return profiles

    def _infer_field_dictionary(self, bindings: list[PointBinding]) -> FieldDictionary:
        seen: set[str] = set()
        fields: list[FieldDefinition] = []
        for binding in bindings:
            if binding.field_name in seen:
                continue
            fields.append(
                FieldDefinition(
                    field_name=binding.field_name,
                    semantic_label=binding.field_name,
                    unit=binding.unit,
                    dimension="dimensionless",
                    observable=True,
                    controllable=False,
                )
            )
            seen.add(binding.field_name)
        return FieldDictionary(fields=fields)

    def _extract_from_nested_inputs(self, payload: dict[str, Any]) -> list[PointBinding]:
        bindings: list[PointBinding] = []
        for section_name, section in payload.items():
            if not isinstance(section, dict):
                continue
            if section_name not in self._LEGACY_SECTION_HINTS and not self._section_looks_like_points(section):
                continue

            for key, value in section.items():
                if isinstance(value, str) and self._value_looks_like_point_tag(value):
                    point_id = f"{section_name}:{key}"
                    field_name = self._sanitize_field_name(key)
                    bindings.append(
                        PointBinding(
                            point_id=point_id,
                            source_type=DataSourceKind.REDIS,
                            source_ref=value,
                            field_name=field_name,
                            unit="dimensionless",
                        )
                    )
                elif isinstance(value, list):
                    for idx, item in enumerate(value):
                        if not isinstance(item, str) or not self._value_looks_like_point_tag(item):
                            continue
                        point_id = f"{section_name}:{key}:{idx}"
                        field_name = self._sanitize_field_name(f"{key}_{idx}")
                        bindings.append(
                            PointBinding(
                                point_id=point_id,
                                source_type=DataSourceKind.REDIS,
                                source_ref=item,
                                field_name=field_name,
                                unit="dimensionless",
                            )
                        )
        return bindings

    def _sanitize_field_name(self, raw: str) -> str:
        name = re.sub(r"[^a-zA-Z0-9]+", "_", raw).strip("_").lower()
        return name or "field"

    def _looks_like_point_entry(self, key: str, value: Any) -> bool:
        if isinstance(value, dict):
            if any(name in value for name in ("source_ref", "field_name", "tag", "key")):
                return True
        if isinstance(value, str) and value:
            if self._value_looks_like_point_tag(value):
                return True
            return bool(re.search(r"[A-Z]{2,}[0-9]", key)) or key.isupper()
        return False

    def _section_looks_like_points(self, section: dict[str, Any]) -> bool:
        if not section:
            return False
        total = len(section)
        tag_like = 0
        for value in section.values():
            if isinstance(value, str) and self._value_looks_like_point_tag(value):
                tag_like += 1
            elif isinstance(value, list):
                if any(isinstance(item, str) and self._value_looks_like_point_tag(item) for item in value):
                    tag_like += 1
        return tag_like >= max(3, int(total * 0.3))

    def _value_looks_like_point_tag(self, value: str) -> bool:
        text = value.strip()
        if not text:
            return False
        # Industrial tags are usually uppercase/digit/underscore mixed codes.
        return bool(re.fullmatch(r"[A-Za-z0-9_:-]{4,}", text)) and bool(re.search(r"[A-Z]", text))

    def _deduplicate_binding_ids(self, bindings: list[PointBinding], warnings: list[str]) -> list[PointBinding]:
        deduped: list[PointBinding] = []
        used: dict[str, int] = {}
        for binding in bindings:
            count = used.get(binding.point_id, 0)
            used[binding.point_id] = count + 1
            if count == 0:
                deduped.append(binding)
                continue

            new_id = f"{binding.point_id}__{count + 1}"
            warnings.append(f"duplicate point_id '{binding.point_id}' renamed to '{new_id}'")
            deduped.append(
                binding.model_copy(update={"point_id": new_id})
            )
        return deduped
