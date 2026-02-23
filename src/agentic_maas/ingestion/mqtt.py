from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from agentic_maas.types import ProtocolType, SensorPoint


class MqttAdapter:
    protocol = ProtocolType.MQTT.value

    def discover_points(self, endpoint: str, auth: dict[str, str] | None) -> list[SensorPoint]:
        topic = "plant/line1/temp"
        if auth and auth.get("topic"):
            topic = auth["topic"]
        return [
            SensorPoint(
                point_id="mqtt-temp-001",
                protocol=ProtocolType.MQTT,
                address=topic,
                unit="C",
                sampling_hz=1.0,
                quality_flags=["RETAINED"],
                tags={"source": endpoint},
            )
        ]

    def stream(self, subscription: dict[str, Any]) -> Iterator[dict[str, Any]]:
        for frame in subscription.get("frames", []):
            yield frame
