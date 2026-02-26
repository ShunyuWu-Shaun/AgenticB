from __future__ import annotations

import os
from typing import Any, Protocol

from easyshift_maas.core.contracts import LLMProviderConfig
from easyshift_maas.llm.providers.openai_compatible import OpenAICompatibleProvider
from easyshift_maas.llm.providers.profiles import build_role_configs_from_env


class LLMClientProtocol(Protocol):
    def complete_json(
        self,
        *,
        role: str,
        system_prompt: str,
        user_payload: dict[str, Any],
        temperature: float = 0.1,
    ) -> tuple[dict[str, Any], dict[str, Any]]: ...


class RoleBasedLLMClient:
    """Role-aware LLM router backed by OpenAI-compatible chat completions."""

    def __init__(self, role_configs: dict[str, LLMProviderConfig] | None = None) -> None:
        self.role_configs = role_configs or build_role_configs_from_env()
        self._providers: dict[str, OpenAICompatibleProvider] = {}

    def complete_json(
        self,
        *,
        role: str,
        system_prompt: str,
        user_payload: dict[str, Any],
        temperature: float = 0.1,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        config = self.role_configs.get(role)
        if config is None:
            raise KeyError(f"unknown llm role config: {role}")

        provider = self._get_provider(role, config)
        payload = provider.chat_json(
            model=config.model,
            system_prompt=system_prompt,
            user_payload=user_payload,
            temperature=temperature,
        )
        meta = {
            "role": role,
            "provider": config.provider_name,
            "vendor": config.vendor,
            "model": config.model,
            "base_url": config.base_url,
        }
        return payload, meta

    def is_available(self) -> bool:
        for config in self.role_configs.values():
            if config.base_url and os.getenv(config.api_key_env):
                return True
        return False

    def _get_provider(self, role: str, config: LLMProviderConfig) -> OpenAICompatibleProvider:
        key = f"{role}:{config.base_url}:{config.api_key_env}:{config.timeout_s}"
        provider = self._providers.get(key)
        if provider is not None:
            return provider

        if not config.base_url:
            raise RuntimeError(
                "missing EASYSHIFT_LLM_BASE_URL (or EASYSHIFT_LLM_VENDOR preset) for LLM provider"
            )

        api_key = os.getenv(config.api_key_env)
        if not api_key:
            raise RuntimeError(f"missing API key env var: {config.api_key_env}")

        provider = OpenAICompatibleProvider(
            base_url=config.base_url,
            api_key=api_key,
            timeout_s=config.timeout_s,
        )
        self._providers[key] = provider
        return provider
