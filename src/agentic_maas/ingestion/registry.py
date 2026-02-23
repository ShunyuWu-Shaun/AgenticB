from __future__ import annotations

from agentic_maas.protocols import IngestionAdapter


class IngestionRegistry:
    def __init__(self) -> None:
        self._adapters: dict[str, IngestionAdapter] = {}

    def register(self, adapter: IngestionAdapter) -> None:
        self._adapters[adapter.protocol] = adapter

    def get(self, protocol: str) -> IngestionAdapter:
        if protocol not in self._adapters:
            raise KeyError(f"adapter not found: {protocol}")
        return self._adapters[protocol]

    def protocols(self) -> list[str]:
        return sorted(self._adapters.keys())
