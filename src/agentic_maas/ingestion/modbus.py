from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from agentic_maas.types import ProtocolType, SensorPoint


class ModbusAdapter:
    protocol = ProtocolType.MODBUS.value

    def discover_points(self, endpoint: str, auth: dict[str, str] | None) -> list[SensorPoint]:
        _ = auth
        return [
            SensorPoint(
                point_id="modbus-flow-001",
                protocol=ProtocolType.MODBUS,
                address="holding:40001",
                unit="m3/h",
                sampling_hz=2.0,
                quality_flags=["VALID"],
                tags={"source": endpoint},
            )
        ]

    def stream(self, subscription: dict[str, Any]) -> Iterator[dict[str, Any]]:
        frames = subscription.get("frames", [])
        for frame in frames:
            yield frame
