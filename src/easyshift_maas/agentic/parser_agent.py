from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

from easyshift_maas.agentic.prompts.output_schemas import ParserAgentOutput
from easyshift_maas.core.contracts import FieldDictionary, ParserMapping, ParserResult
from easyshift_maas.llm.client import LLMClientProtocol


class ParserAgent:
    """Map legacy point names to canonical field dictionary."""

    _RESERVED_KEYS = {
        "scene",
        "datasources",
        "point_catalog",
        "field_dictionary",
        "template_override",
        "redis_config",
        "mysql_config",
    }

    def __init__(
        self,
        llm_client: LLMClientProtocol | None = None,
        prompt_path: str | None = None,
    ) -> None:
        self.llm_client = llm_client
        default_path = Path(__file__).with_name("prompts") / "parser_system.md"
        self.prompt = Path(prompt_path).read_text(encoding="utf-8") if prompt_path else default_path.read_text(encoding="utf-8")

    def parse(
        self,
        *,
        field_dictionary: FieldDictionary,
        legacy_points: list[str] | None = None,
        raw_yaml_text: str | None = None,
    ) -> ParserResult:
        points = self._collect_points(legacy_points=legacy_points or [], raw_yaml_text=raw_yaml_text)
        if not points:
            return ParserResult(
                mappings=[],
                unmapped_points=[],
                confidence=0.0,
                strategy="empty_input",
                warnings=["no legacy points provided"],
            )

        if self.llm_client is not None:
            try:
                return self._parse_with_llm(points=points, field_dictionary=field_dictionary)
            except Exception as exc:  # noqa: BLE001
                fallback = self._parse_with_rules(points=points, field_dictionary=field_dictionary)
                fallback.warnings.append(f"llm parser unavailable, fallback to rule mapping: {exc}")
                return fallback

        return self._parse_with_rules(points=points, field_dictionary=field_dictionary)

    def _parse_with_llm(self, *, points: list[str], field_dictionary: FieldDictionary) -> ParserResult:
        last_error: Exception | None = None
        parsed: ParserAgentOutput | None = None
        for _ in range(2):
            try:
                payload, _meta = self.llm_client.complete_json(
                    role="parser",
                    system_prompt=self.prompt,
                    user_payload={
                        "legacy_points": points,
                        "field_dictionary": field_dictionary.model_dump(mode="json"),
                    },
                    temperature=0.0,
                )
                parsed = ParserAgentOutput.model_validate(payload)
                break
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                continue

        if parsed is None:
            raise RuntimeError(f"parser llm output validation failed after retries: {last_error}")

        valid_fields = set(field_dictionary.field_names())
        mappings: list[ParserMapping] = []
        unmapped = set(parsed.unmapped_points)

        for item in parsed.mappings:
            if item.standard_name not in valid_fields:
                unmapped.add(item.legacy_name)
                continue
            mappings.append(
                ParserMapping(
                    legacy_name=item.legacy_name,
                    standard_name=item.standard_name,
                    confidence=item.confidence,
                    reasoning=item.reasoning,
                )
            )

        mapped_points = {item.legacy_name for item in mappings}
        for point in points:
            if point not in mapped_points and point not in unmapped:
                unmapped.add(point)

        confidence = 0.0
        if mappings:
            confidence = sum(item.confidence for item in mappings) / len(mappings)

        return ParserResult(
            mappings=mappings,
            unmapped_points=sorted(unmapped),
            confidence=round(confidence, 4),
            strategy="llm_semantic_mapping",
            warnings=[],
        )

    def _parse_with_rules(self, *, points: list[str], field_dictionary: FieldDictionary) -> ParserResult:
        mappings: list[ParserMapping] = []
        unmapped: list[str] = []

        alias_map = {key.lower(): value for key, value in field_dictionary.alias_map.items()}
        fields = field_dictionary.fields

        for legacy_name in points:
            lower_name = legacy_name.lower()
            if lower_name in alias_map and field_dictionary.has_field(alias_map[lower_name]):
                mappings.append(
                    ParserMapping(
                        legacy_name=legacy_name,
                        standard_name=alias_map[lower_name],
                        confidence=0.98,
                        reasoning="matched alias_map",
                    )
                )
                continue

            if field_dictionary.has_field(legacy_name):
                mappings.append(
                    ParserMapping(
                        legacy_name=legacy_name,
                        standard_name=legacy_name,
                        confidence=0.99,
                        reasoning="exact field name match",
                    )
                )
                continue

            best_field = None
            best_score = 0.0
            legacy_tokens = self._tokens(legacy_name)

            for field in fields:
                target_tokens = self._tokens(field.field_name) | self._tokens(field.semantic_label)
                if not target_tokens:
                    continue
                score = len(legacy_tokens & target_tokens) / len(legacy_tokens | target_tokens)
                if score > best_score:
                    best_score = score
                    best_field = field.field_name

            if best_field is None or best_score < 0.2:
                unmapped.append(legacy_name)
                continue

            mappings.append(
                ParserMapping(
                    legacy_name=legacy_name,
                    standard_name=best_field,
                    confidence=round(min(0.88, 0.45 + best_score), 4),
                    reasoning="token overlap heuristic",
                )
            )

        confidence = 0.0 if not mappings else sum(item.confidence for item in mappings) / len(mappings)
        return ParserResult(
            mappings=mappings,
            unmapped_points=sorted(set(unmapped)),
            confidence=round(confidence, 4),
            strategy="rule_fallback",
            warnings=["rule parser used; verify low-confidence mappings"],
        )

    def _collect_points(self, *, legacy_points: list[str], raw_yaml_text: str | None) -> list[str]:
        points = {item.strip() for item in legacy_points if item and item.strip()}

        if raw_yaml_text:
            try:
                payload = yaml.safe_load(raw_yaml_text)
                points.update(self._extract_from_yaml(payload))
            except Exception:  # noqa: BLE001
                pass

        return sorted(points)

    def _extract_from_yaml(self, payload: Any) -> set[str]:
        found: set[str] = set()
        if isinstance(payload, dict):
            for key, value in payload.items():
                if key in self._RESERVED_KEYS:
                    continue
                if self._looks_like_point(key, value):
                    found.add(str(key))
                found.update(self._extract_from_yaml(value))
        elif isinstance(payload, list):
            for item in payload:
                found.update(self._extract_from_yaml(item))
        return found

    def _looks_like_point(self, key: str, value: Any) -> bool:
        if isinstance(value, (int, float)):
            return False
        if isinstance(value, str) and len(value) <= 3:
            return False
        if re.search(r"[A-Za-z].*\d|\d.*[A-Za-z]", key):
            return True
        if "_" in key and len(key) >= 4:
            return True
        return False

    def _tokens(self, value: str) -> set[str]:
        return {item for item in re.split(r"[^a-zA-Z0-9]+", value.lower()) if item}
