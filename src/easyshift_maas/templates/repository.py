from __future__ import annotations

import json
from typing import Protocol

from easyshift_maas.core.contracts import ScenarioTemplate


class TemplateRepositoryProtocol(Protocol):
    def publish(self, template: ScenarioTemplate) -> ScenarioTemplate: ...

    def get(self, template_id: str, version: str | None = None) -> ScenarioTemplate: ...

    def list_versions(self, template_id: str) -> list[str]: ...

    def export_template(self, template_id: str, version: str | None = None, fmt: str = "json") -> str: ...

    def import_template(self, payload: str, fmt: str = "json") -> ScenarioTemplate: ...


class InMemoryTemplateRepository:
    def __init__(self) -> None:
        self._storage: dict[str, dict[str, ScenarioTemplate]] = {}

    def publish(self, template: ScenarioTemplate) -> ScenarioTemplate:
        versions = self._storage.setdefault(template.template_id, {})
        if template.version in versions:
            raise ValueError(
                f"template already exists: {template.template_id}@{template.version}"
            )
        versions[template.version] = template
        return template

    def get(self, template_id: str, version: str | None = None) -> ScenarioTemplate:
        if template_id not in self._storage:
            raise KeyError(f"template not found: {template_id}")

        versions = self._storage[template_id]
        if version is None:
            latest = sorted(versions.keys())[-1]
            return versions[latest]

        if version not in versions:
            raise KeyError(f"template version not found: {template_id}@{version}")
        return versions[version]

    def list_versions(self, template_id: str) -> list[str]:
        if template_id not in self._storage:
            return []
        return sorted(self._storage[template_id].keys())

    def list_template_ids(self) -> list[str]:
        return sorted(self._storage.keys())

    def export_template(self, template_id: str, version: str | None = None, fmt: str = "json") -> str:
        template = self.get(template_id, version)
        payload = template.model_dump(mode="json")

        if fmt == "json":
            return json.dumps(payload, indent=2, ensure_ascii=False)
        if fmt == "yaml":
            try:
                import yaml  # type: ignore
            except Exception as exc:  # noqa: BLE001
                raise RuntimeError("YAML export requires PyYAML dependency") from exc
            return yaml.safe_dump(payload, sort_keys=False)

        raise ValueError(f"unsupported format: {fmt}")

    def import_template(self, payload: str, fmt: str = "json") -> ScenarioTemplate:
        if fmt == "json":
            data = json.loads(payload)
            return ScenarioTemplate.model_validate(data)
        if fmt == "yaml":
            try:
                import yaml  # type: ignore
            except Exception as exc:  # noqa: BLE001
                raise RuntimeError("YAML import requires PyYAML dependency") from exc
            data = yaml.safe_load(payload)
            return ScenarioTemplate.model_validate(data)

        raise ValueError(f"unsupported format: {fmt}")
