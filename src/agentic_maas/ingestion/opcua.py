from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from agentic_maas.types import ProtocolType, SensorPoint


class OpcUaAdapter:
    protocol = ProtocolType.OPC_UA.value

    def discover_points(self, endpoint: str, auth: dict[str, str] | None) -> list[SensorPoint]:
        mock_points = auth.get("mock_points", "") if auth else ""
        if mock_points:
            items = [item.strip() for item in mock_points.split(",") if item.strip()]
            return [
                SensorPoint(
                    point_id=f"opcua-{idx}",
                    protocol=ProtocolType.OPC_UA,
                    address=f"ns=2;s={name}",
                    unit="C",
                    sampling_hz=1.0,
                    quality_flags=["GOOD"],
                    tags={"source": endpoint},
                )
                for idx, name in enumerate(items, start=1)
            ]

        return [
            SensorPoint(
                point_id="opcua-temp-001",
                protocol=ProtocolType.OPC_UA,
                address="ns=2;s=Boiler.Temp",
                unit="C",
                sampling_hz=1.0,
                quality_flags=["GOOD"],
                tags={"source": endpoint},
            )
        ]

    def stream(self, subscription: dict[str, Any]) -> Iterator[dict[str, Any]]:
        frames = subscription.get("frames", [])
        for frame in frames:
            yield frame
