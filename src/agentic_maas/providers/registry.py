from __future__ import annotations

from typing import Any

from agentic_maas.protocols import ModelProvider


class ProviderRegistry:
    def __init__(self) -> None:
        self._providers: dict[str, ModelProvider] = {}

    def register(self, provider: ModelProvider) -> None:
        self._providers[provider.name] = provider

    def get(self, name: str) -> ModelProvider:
        if name not in self._providers:
            raise KeyError(f"provider not found: {name}")
        return self._providers[name]

    def health(self) -> list[dict[str, Any]]:
        return [provider.health() for provider in self._providers.values()]
