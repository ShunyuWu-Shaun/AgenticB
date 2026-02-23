from __future__ import annotations

from collections.abc import Iterator, Sequence
from typing import Any, Protocol

from agentic_maas.types import SensorPoint


class ModelProvider(Protocol):
    name: str

    def chat(
        self,
        messages: Sequence[dict[str, Any]],
        tools: Sequence[dict[str, Any]] | None,
        temperature: float,
        timeout_s: float,
    ) -> dict[str, Any]: ...

    def embeddings(self, inputs: Sequence[str]) -> list[list[float]]: ...

    def health(self) -> dict[str, Any]: ...


class IngestionAdapter(Protocol):
    protocol: str

    def discover_points(self, endpoint: str, auth: dict[str, str] | None) -> list[SensorPoint]: ...

    def stream(self, subscription: dict[str, Any]) -> Iterator[dict[str, Any]]: ...
