from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from agentic_maas.types import PointMappingRule, SensorPoint


class MappedPoint(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_point_id: str
    target_field: str
    value_expr: str
    unit: str
    sampling_hz: float = Field(gt=0)


class MigrationDiff(BaseModel):
    model_config = ConfigDict(extra="forbid")

    missing_points: list[str] = Field(default_factory=list)
    duplicate_targets: list[str] = Field(default_factory=list)
    unit_conflicts: list[str] = Field(default_factory=list)
    sampling_conflicts: list[str] = Field(default_factory=list)


class MigrationEngine:
    """Migrates raw sensor points into semantic target fields using mapping rules."""

    def migrate_points(
        self,
        points: list[SensorPoint],
        rules: list[PointMappingRule],
    ) -> tuple[list[MappedPoint], MigrationDiff]:
        mapped: list[MappedPoint] = []
        missing_points: list[str] = []
        target_units: dict[str, set[str]] = defaultdict(set)
        target_sampling: dict[str, set[float]] = defaultdict(set)

        for rule in rules:
            candidates = self._match_points(points, rule.source_expr)
            if not candidates:
                missing_points.append(rule.source_expr)
                continue

            for point in candidates:
                target_units[rule.target_field].add(point.unit)
                target_sampling[rule.target_field].add(point.sampling_hz)
                mapped.append(
                    MappedPoint(
                        source_point_id=point.point_id,
                        target_field=rule.target_field,
                        value_expr=self._build_value_expr(point, rule),
                        unit=point.unit,
                        sampling_hz=point.sampling_hz,
                    )
                )

        duplicates = [
            target
            for target, count in Counter(m.target_field for m in mapped).items()
            if count > 1
        ]
        unit_conflicts = [target for target, units in target_units.items() if len(units) > 1]
        sampling_conflicts = [
            target for target, rates in target_sampling.items() if len(rates) > 1
        ]

        diff = MigrationDiff(
            missing_points=sorted(missing_points),
            duplicate_targets=sorted(duplicates),
            unit_conflicts=sorted(unit_conflicts),
            sampling_conflicts=sorted(sampling_conflicts),
        )
        return mapped, diff

    def validate_mapped_values(
        self,
        mapped_values: dict[str, float],
        rules: list[PointMappingRule],
    ) -> dict[str, list[str]]:
        """Return validation errors keyed by target field."""
        errors: dict[str, list[str]] = defaultdict(list)
        rule_by_target = {rule.target_field: rule for rule in rules}

        for target_field, value in mapped_values.items():
            rule = rule_by_target.get(target_field)
            if not rule:
                continue
            validation = rule.validation_rule
            min_v = validation.get("min")
            max_v = validation.get("max")
            if min_v is not None and value < min_v:
                errors[target_field].append(f"value {value} < min {min_v}")
            if max_v is not None and value > max_v:
                errors[target_field].append(f"value {value} > max {max_v}")

        return dict(errors)

    def _match_points(self, points: list[SensorPoint], source_expr: str) -> list[SensorPoint]:
        if source_expr.startswith("point_id:"):
            expected = source_expr.split(":", 1)[1]
            return [point for point in points if point.point_id == expected]

        if source_expr.startswith("address:"):
            expected = source_expr.split(":", 1)[1]
            return [point for point in points if point.address == expected]

        return [point for point in points if point.point_id == source_expr]

    def _build_value_expr(self, point: SensorPoint, rule: PointMappingRule) -> str:
        scale = rule.unit_transform.get("scale", 1.0)
        offset = rule.unit_transform.get("offset", 0.0)
        if scale == 1.0 and offset == 0.0:
            return point.point_id
        return f"({point.point_id} * {scale}) + {offset}"

    @staticmethod
    def diff_summary(diff: MigrationDiff) -> dict[str, Any]:
        return {
            "missing_points": len(diff.missing_points),
            "duplicate_targets": len(diff.duplicate_targets),
            "unit_conflicts": len(diff.unit_conflicts),
            "sampling_conflicts": len(diff.sampling_conflicts),
        }
