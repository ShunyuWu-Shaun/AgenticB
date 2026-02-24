from __future__ import annotations

import re
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


class MySQLSnapshotProvider:
    kind = DataSourceKind.MYSQL

    _IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

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
            import pymysql  # type: ignore
        except Exception:  # noqa: BLE001
            latency = int((time.perf_counter() - started) * 1000)
            return SnapshotResult(
                values=values,
                quality_flags={item.field_name: "mysql_dependency_missing" for item in bindings},
                missing_fields=[item.field_name for item in bindings],
                source_latency_ms={"mysql": latency},
            )

        try:
            conn = secret_resolver.resolve(profile.conn_ref)
            host = str(conn.get("host", "127.0.0.1"))
            port = int(conn.get("port", 3306))
            user = str(conn.get("user", "root"))
            password = str(conn.get("password", ""))
            database = str(conn.get("database", conn.get("db", "")))

            table = self._ident(profile.options.mysql_table)
            point_col = self._ident(profile.options.mysql_point_column)
            value_col = self._ident(profile.options.mysql_value_column)

            ts_col = profile.options.mysql_ts_column
            if ts_col is not None:
                ts_col = self._ident(ts_col)

            source_refs = [item.source_ref for item in bindings]
            placeholders = ",".join(["%s"] * len(source_refs))

            query = f"SELECT {point_col}, {value_col} FROM {table} WHERE {point_col} IN ({placeholders})"
            args: list[Any] = list(source_refs)

            if request.at is not None and ts_col is not None:
                query += f" AND {ts_col} <= %s"
                args.append(request.at)

            ssl_options = None
            if profile.options.tls:
                ssl_options = {"ssl": {}}

            by_point: dict[str, float] = {}
            connection = pymysql.connect(
                host=host,
                port=port,
                user=user,
                password=password,
                database=database,
                connect_timeout=max(1, int(profile.options.timeout_ms / 1000)),
                read_timeout=max(1, int(profile.options.timeout_ms / 1000)),
                write_timeout=max(1, int(profile.options.timeout_ms / 1000)),
                cursorclass=pymysql.cursors.Cursor,
                **(ssl_options or {}),
            )

            try:
                with connection.cursor() as cursor:
                    cursor.execute(query, args)
                    rows = cursor.fetchall()
                    for point_id, raw_value in rows:
                        parsed = self._to_float(raw_value)
                        if parsed is None:
                            continue
                        by_point[str(point_id)] = parsed
            finally:
                connection.close()
        except Exception as exc:  # noqa: BLE001
            latency = int((time.perf_counter() - started) * 1000)
            return SnapshotResult(
                values=values,
                quality_flags={item.field_name: f"mysql_error:{type(exc).__name__}" for item in bindings},
                missing_fields=[item.field_name for item in bindings],
                source_latency_ms={"mysql": latency},
            )

        for item in bindings:
            raw = by_point.get(item.source_ref)
            if raw is None:
                missing_fields.append(item.field_name)
                quality_flags[item.field_name] = "missing"
                continue
            try:
                values[item.field_name] = apply_transform(raw, item.transform)
                quality_flags[item.field_name] = "ok"
            except Exception as exc:  # noqa: BLE001
                missing_fields.append(item.field_name)
                quality_flags[item.field_name] = f"transform_error:{exc}"

        latency = int((time.perf_counter() - started) * 1000)
        return SnapshotResult(
            values=values,
            quality_flags=quality_flags,
            missing_fields=sorted(set(missing_fields)),
            source_latency_ms={"mysql": latency},
        )

    def _ident(self, value: str) -> str:
        if not self._IDENTIFIER_RE.match(value):
            raise ValueError(f"invalid SQL identifier: {value}")
        return value

    def _to_float(self, raw: Any) -> float | None:
        if isinstance(raw, (int, float)):
            return float(raw)
        if isinstance(raw, str):
            try:
                return float(raw)
            except ValueError:
                return None
        return None
