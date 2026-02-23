from agentic_maas.migration.engine import MigrationEngine
from agentic_maas.types import PointMappingRule, ProtocolType, SensorPoint


def test_migrate_points_and_detect_diff() -> None:
    points = [
        SensorPoint(
            point_id="p1",
            protocol=ProtocolType.OPC_UA,
            address="ns=2;s=A",
            unit="C",
            sampling_hz=1.0,
            quality_flags=[],
            tags={},
        ),
        SensorPoint(
            point_id="p2",
            protocol=ProtocolType.MODBUS,
            address="holding:1",
            unit="F",
            sampling_hz=2.0,
            quality_flags=[],
            tags={},
        ),
    ]
    rules = [
        PointMappingRule(
            source_expr="point_id:p1",
            target_field="temperature",
            unit_transform={"scale": 1.0, "offset": 0.0},
            validation_rule={},
        ),
        PointMappingRule(
            source_expr="point_id:p2",
            target_field="temperature",
            unit_transform={"scale": 1.0, "offset": 0.0},
            validation_rule={},
        ),
        PointMappingRule(
            source_expr="point_id:missing",
            target_field="x",
            unit_transform={},
            validation_rule={},
        ),
    ]

    engine = MigrationEngine()
    mapped, diff = engine.migrate_points(points, rules)

    assert len(mapped) == 2
    assert diff.missing_points == ["point_id:missing"]
    assert diff.duplicate_targets == ["temperature"]
    assert diff.unit_conflicts == ["temperature"]
    assert diff.sampling_conflicts == ["temperature"]
