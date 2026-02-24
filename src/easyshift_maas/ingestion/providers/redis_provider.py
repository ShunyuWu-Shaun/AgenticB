from __future__ import annotations

import time
from typing import Any

from easyshift_maas.core.contracts import (
    DataSourceKind,
    DataSourceProfile,
    PointBinding,
    SnapshotRequest,
    SnapshotResult,
)
from easyshift_maas.ingestion.snapshot_provider import apply_transform
from easyshift_maas.security.secrets import SecretResolverProtocol


class RedisSnapshotProvider:
    kind = DataSourceKind.REDIS

    def fetch_bindings(
        self,
        bindings: list[PointBinding],
        profile: DataSourceProfile,
        request: SnapshotRequest,
        secret_resolver: SecretResolverProtocol,
    ) -> SnapshotResult:
        started = time.perf_counter()
        values: dict[str, float] = {}
        quality_flags: dict[str, str] = {}
        missing_fields: list[str] = []

        try:
            import redis  # type: ignore
        except Exception:  # noqa: BLE001
            latency = int((time.perf_counter() - started) * 1000)
            return SnapshotResult(
                values=values,
                quality_flags={item.field_name: "redis_dependency_missing" for item in bindings},
                missing_fields=[item.field_name for item in bindings],
                source_latency_ms={"redis": latency},
            )

        try:
            conn = secret_resolver.resolve(profile.conn_ref)
            host = str(conn.get("host", "127.0.0.1"))
            port = int(conn.get("port", 6379))
            db = int(conn.get("db", 0))
            password = conn.get("password")
            client = redis.Redis(
                host=host,
                port=port,
                db=db,
                password=password,
                ssl=bool(profile.options.tls or conn.get("tls", False)),
                socket_timeout=profile.options.timeout_ms / 1000.0,
                decode_responses=False,
            )

            batch_size = profile.options.batch_size
            for idx in range(0, len(bindings), batch_size):
                chunk = bindings[idx : idx + batch_size]
                keys = [item.source_ref for item in chunk]
                raw_values = client.mget(keys)
                for item, raw in zip(chunk, raw_values):
                    if raw is None:
                        missing_fields.append(item.field_name)
                        quality_flags[item.field_name] = "missing"
                        continue

                    parsed = self._to_float(raw)
                    if parsed is None:
                        missing_fields.append(item.field_name)
                        quality_flags[item.field_name] = "parse_error"
                        continue

                    try:
                        values[item.field_name] = apply_transform(parsed, item.transform)
                        quality_flags[item.field_name] = "ok"
                    except Exception as exc:  # noqa: BLE001
                        missing_fields.append(item.field_name)
                        quality_flags[item.field_name] = f"transform_error:{exc}"
        except Exception as exc:  # noqa: BLE001
            for item in bindings:
                if item.field_name not in quality_flags:
                    missing_fields.append(item.field_name)
                    quality_flags[item.field_name] = f"redis_error:{type(exc).__name__}"

        latency = int((time.perf_counter() - started) * 1000)
        return SnapshotResult(
            values=values,
            quality_flags=quality_flags,
            missing_fields=sorted(set(missing_fields)),
            source_latency_ms={"redis": latency},
        )

    def _to_float(self, raw: Any) -> float | None:
        if isinstance(raw, (int, float)):
            return float(raw)
        if isinstance(raw, bytes):
            text = raw.decode("utf-8", errors="ignore")
            try:
                return float(text)
            except ValueError:
                return None
        if isinstance(raw, str):
            try:
                return float(raw)
            except ValueError:
                return None
        return None
