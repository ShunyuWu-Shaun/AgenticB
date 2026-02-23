from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from agentic_maas.migration.engine import MigrationEngine
from agentic_maas.types import PointMappingRule, ProtocolType, SensorPoint


def _load_json(path: str) -> Any:
    return json.loads(Path(path).read_text())


def _dump_json(payload: Any) -> None:
    print(json.dumps(payload, indent=2, ensure_ascii=False))


def draft_mapping(points_path: str) -> None:
    raw_points = _load_json(points_path)
    points = [SensorPoint.model_validate(item) for item in raw_points]

    rules = [
        PointMappingRule(
            source_expr=f"point_id:{point.point_id}",
            target_field=point.point_id.replace("-", "_"),
            unit_transform={"scale": 1.0, "offset": 0.0},
            validation_rule={},
        )
        for point in points
    ]
    _dump_json([rule.model_dump() for rule in rules])


def apply_mapping(points_path: str, rules_path: str) -> None:
    raw_points = _load_json(points_path)
    raw_rules = _load_json(rules_path)

    points = [SensorPoint.model_validate(item) for item in raw_points]
    rules = [PointMappingRule.model_validate(item) for item in raw_rules]

    engine = MigrationEngine()
    mapped, diff = engine.migrate_points(points, rules)

    _dump_json(
        {
            "mapped": [item.model_dump() for item in mapped],
            "diff": diff.model_dump(),
            "summary": engine.diff_summary(diff),
        }
    )


def generate_sample_points() -> None:
    sample = [
        SensorPoint(
            point_id="opcua-temp-001",
            protocol=ProtocolType.OPC_UA,
            address="ns=2;s=Boiler.Temp",
            unit="C",
            sampling_hz=1.0,
            quality_flags=["GOOD"],
            tags={"line": "L1"},
        ).model_dump(),
        SensorPoint(
            point_id="modbus-flow-001",
            protocol=ProtocolType.MODBUS,
            address="holding:40001",
            unit="m3/h",
            sampling_hz=2.0,
            quality_flags=["VALID"],
            tags={"line": "L1"},
        ).model_dump(),
    ]
    _dump_json(sample)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="agentic-maas CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    draft = sub.add_parser("draft-mapping", help="Generate initial mapping rules from points JSON")
    draft.add_argument("--points", required=True, help="Path to sensor points JSON file")

    apply_cmd = sub.add_parser("apply-mapping", help="Apply mapping rules to sensor points")
    apply_cmd.add_argument("--points", required=True, help="Path to sensor points JSON file")
    apply_cmd.add_argument("--rules", required=True, help="Path to mapping rules JSON file")

    sub.add_parser("sample-points", help="Print sample sensor points JSON")
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "draft-mapping":
        draft_mapping(args.points)
        return

    if args.command == "apply-mapping":
        apply_mapping(args.points, args.rules)
        return

    if args.command == "sample-points":
        generate_sample_points()
        return

    parser.error(f"unknown command: {args.command}")
