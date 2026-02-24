from __future__ import annotations

from collections import defaultdict
from typing import Protocol

from easyshift_maas.core.contracts import (
    DataSourceKind,
    DataSourceProfile,
    PointBinding,
    PointCatalog,
    SnapshotMissingPolicy,
    SnapshotRequest,
    SnapshotResult,
)
from easyshift_maas.security.secrets import SecretResolverProtocol


class SourceSnapshotProviderProtocol(Protocol):
    kind: DataSourceKind

    def fetch_bindings(
        self,
        bindings: list[PointBinding],
        profile: DataSourceProfile,
        request: SnapshotRequest,
        secret_resolver: SecretResolverProtocol,
    ) -> SnapshotResult: ...


class SnapshotProviderProtocol(Protocol):
    def fetch(
        self,
        request: SnapshotRequest,
        catalog: PointCatalog,
        profiles: list[DataSourceProfile],
        secret_resolver: SecretResolverProtocol,
    ) -> SnapshotResult: ...


class CompositeSnapshotProvider:
    def __init__(self, providers: list[SourceSnapshotProviderProtocol]) -> None:
        self._providers = {provider.kind: provider for provider in providers}

    def fetch(
        self,
        request: SnapshotRequest,
        catalog: PointCatalog,
        profiles: list[DataSourceProfile],
        secret_resolver: SecretResolverProtocol,
    ) -> SnapshotResult:
        selected_fields = set(request.fields or [])
        selected_bindings = [
            item
            for item in catalog.bindings
            if item.enabled and (not selected_fields or item.field_name in selected_fields)
        ]

        grouped: dict[DataSourceKind, list[PointBinding]] = defaultdict(list)
        for binding in selected_bindings:
            grouped[binding.source_type].append(binding)

        merged_values: dict[str, float] = {}
        merged_flags: dict[str, str] = {}
        merged_missing: list[str] = []
        merged_latency: dict[str, int] = {}

        for kind, bindings in grouped.items():
            provider = self._providers.get(kind)
            if provider is None:
                for binding in bindings:
                    merged_missing.append(binding.field_name)
                    merged_flags[binding.field_name] = f"provider_missing:{kind.value}"
                continue

            profile = self._select_profile(kind=kind, preferred_name=catalog.source_profile, profiles=profiles)
            if profile is None:
                for binding in bindings:
                    merged_missing.append(binding.field_name)
                    merged_flags[binding.field_name] = f"profile_missing:{kind.value}"
                continue

            partial = provider.fetch_bindings(
                bindings=bindings,
                profile=profile,
                request=request,
                secret_resolver=secret_resolver,
            )
            merged_values.update(partial.values)
            merged_flags.update(partial.quality_flags)
            merged_missing.extend(partial.missing_fields)
            merged_latency.update(partial.source_latency_ms)

        merged_missing = sorted(set(merged_missing))

        if request.missing_policy == SnapshotMissingPolicy.ZERO:
            for field in merged_missing:
                merged_values.setdefault(field, 0.0)
                merged_flags[field] = "filled_zero"
            merged_missing = []

        if request.missing_policy == SnapshotMissingPolicy.DROP:
            for field in merged_missing:
                merged_flags.pop(field, None)
                merged_values.pop(field, None)
            merged_missing = []

        return SnapshotResult(
            values=merged_values,
            quality_flags=merged_flags,
            missing_fields=merged_missing,
            source_latency_ms=merged_latency,
        )

    def _select_profile(
        self,
        *,
        kind: DataSourceKind,
        preferred_name: str,
        profiles: list[DataSourceProfile],
    ) -> DataSourceProfile | None:
        kind_profiles = [item for item in profiles if item.kind == kind]
        if not kind_profiles:
            return None

        for profile in kind_profiles:
            if profile.name == preferred_name:
                return profile
        return kind_profiles[0]


def apply_transform(raw: float, transform: str | None) -> float:
    if transform is None or not transform.strip():
        return raw

    text = transform.strip()
    if text.startswith("scale:"):
        scale = float(text.split(":", 1)[1])
        return raw * scale
    if text.startswith("offset:"):
        offset = float(text.split(":", 1)[1])
        return raw + offset
    if text.startswith("muladd:"):
        values = text.split(":", 1)[1].split(",")
        if len(values) != 2:
            raise ValueError(f"invalid muladd transform: {transform}")
        mul = float(values[0])
        add = float(values[1])
        return raw * mul + add
    raise ValueError(f"unsupported transform: {transform}")
