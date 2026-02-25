from easyshift_maas.core.contracts import (
    DataSourceKind,
    DataSourceProfile,
    PointBinding,
    PointCatalog,
    SnapshotMissingPolicy,
    SnapshotRequest,
    SnapshotResult,
)
from easyshift_maas.ingestion.snapshot_provider import CompositeSnapshotProvider


class _DummyResolver:
    def resolve(self, conn_ref: str) -> dict[str, str]:
        return {}


class _RedisStubProvider:
    kind = DataSourceKind.REDIS

    def fetch_bindings(self, bindings, profile, request, secret_resolver) -> SnapshotResult:  # noqa: ANN001
        values = {item.field_name: 1.0 for item in bindings}
        return SnapshotResult(values=values, quality_flags={name: "ok" for name in values})


def _catalog() -> PointCatalog:
    return PointCatalog(
        catalog_id="demo",
        version="v1",
        refresh_sec=30,
        source_profile="default",
        bindings=[
            PointBinding(
                point_id="p1",
                source_type=DataSourceKind.REDIS,
                source_ref="key:p1",
                field_name="known_field",
                unit="dimensionless",
            )
        ],
    )


def _profiles() -> list[DataSourceProfile]:
    return [
        DataSourceProfile(
            name="default",
            kind=DataSourceKind.REDIS,
            conn_ref="env:IGNORED",
        )
    ]


def test_unknown_requested_field_is_reported_missing() -> None:
    provider = CompositeSnapshotProvider(providers=[_RedisStubProvider()])

    result = provider.fetch(
        request=SnapshotRequest(
            catalog_id="demo",
            fields=["known_field", "missing_field"],
            missing_policy=SnapshotMissingPolicy.ERROR,
        ),
        catalog=_catalog(),
        profiles=_profiles(),
        secret_resolver=_DummyResolver(),
    )

    assert result.values["known_field"] == 1.0
    assert "missing_field" in result.missing_fields
    assert result.quality_flags["missing_field"] == "binding_missing"


def test_unknown_requested_field_respects_zero_policy() -> None:
    provider = CompositeSnapshotProvider(providers=[_RedisStubProvider()])

    result = provider.fetch(
        request=SnapshotRequest(
            catalog_id="demo",
            fields=["missing_field"],
            missing_policy=SnapshotMissingPolicy.ZERO,
        ),
        catalog=_catalog(),
        profiles=_profiles(),
        secret_resolver=_DummyResolver(),
    )

    assert result.missing_fields == []
    assert result.values["missing_field"] == 0.0
    assert result.quality_flags["missing_field"] == "filled_zero"
