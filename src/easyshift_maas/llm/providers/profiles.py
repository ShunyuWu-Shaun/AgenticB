from __future__ import annotations

import os
from dataclasses import dataclass

from easyshift_maas.core.contracts import LLMProviderConfig


@dataclass(frozen=True)
class VendorPreset:
    vendor: str
    base_url: str
    default_model: str


VENDOR_PRESETS: dict[str, VendorPreset] = {
    "kimi": VendorPreset(
        vendor="kimi",
        base_url="https://api.moonshot.cn/v1",
        default_model="moonshot-v1-8k",
    ),
    "qwen": VendorPreset(
        vendor="qwen",
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        default_model="qwen-plus",
    ),
    "deepseek": VendorPreset(
        vendor="deepseek",
        base_url="https://api.deepseek.com/v1",
        default_model="deepseek-chat",
    ),
    "openai": VendorPreset(
        vendor="openai",
        base_url="https://api.openai.com/v1",
        default_model="gpt-4o-mini",
    ),
}


def _pick_vendor() -> str:
    raw = os.getenv("REFLEXFLOW_LLM_VENDOR", os.getenv("EASYSHIFT_LLM_VENDOR", "custom")).strip().lower()
    if raw in VENDOR_PRESETS:
        return raw
    return "custom"


def _resolve_base_url(vendor: str) -> str | None:
    explicit = os.getenv("REFLEXFLOW_LLM_BASE_URL", os.getenv("EASYSHIFT_LLM_BASE_URL"))
    if explicit:
        return explicit.strip()
    preset = VENDOR_PRESETS.get(vendor)
    return preset.base_url if preset else None


def _resolve_default_model(vendor: str) -> str:
    preset = VENDOR_PRESETS.get(vendor)
    if preset:
        return preset.default_model
    return "gpt-4o-mini"


def _default_api_key_env() -> str:
    if os.getenv("REFLEXFLOW_LLM_API_KEY"):
        return "REFLEXFLOW_LLM_API_KEY"
    if os.getenv("EASYSHIFT_LLM_API_KEY"):
        return "EASYSHIFT_LLM_API_KEY"
    return "REFLEXFLOW_LLM_API_KEY"


def build_role_configs_from_env() -> dict[str, LLMProviderConfig]:
    """Build parser/generator/critic role configs from env vars.

    Required runtime vars for actual LLM call:
    - REFLEXFLOW_LLM_BASE_URL (or known vendor preset)
    - REFLEXFLOW_LLM_API_KEY (or custom env via REFLEXFLOW_LLM_API_KEY_ENV)

    Backward compatibility:
    - EASYSHIFT_LLM_* is still accepted.
    """

    vendor = _pick_vendor()
    base_url = _resolve_base_url(vendor)
    api_key_env = os.getenv(
        "REFLEXFLOW_LLM_API_KEY_ENV",
        os.getenv("EASYSHIFT_LLM_API_KEY_ENV", _default_api_key_env()),
    )
    timeout_s = int(os.getenv("REFLEXFLOW_LLM_TIMEOUT_SEC", os.getenv("EASYSHIFT_LLM_TIMEOUT_SEC", "30")))

    default_model = _resolve_default_model(vendor)
    parser_model = os.getenv(
        "REFLEXFLOW_LLM_MODEL_PARSER",
        os.getenv("EASYSHIFT_LLM_MODEL_PARSER", default_model),
    )
    generator_model = os.getenv(
        "REFLEXFLOW_LLM_MODEL_GENERATOR",
        os.getenv("EASYSHIFT_LLM_MODEL_GENERATOR", default_model),
    )
    critic_model = os.getenv(
        "REFLEXFLOW_LLM_MODEL_CRITIC",
        os.getenv("EASYSHIFT_LLM_MODEL_CRITIC", default_model),
    )

    return {
        "parser": LLMProviderConfig(
            provider_name="openai_compatible",
            vendor=vendor,
            base_url=base_url,
            api_key_env=api_key_env,
            model=parser_model,
            timeout_s=timeout_s,
        ),
        "generator": LLMProviderConfig(
            provider_name="openai_compatible",
            vendor=vendor,
            base_url=base_url,
            api_key_env=api_key_env,
            model=generator_model,
            timeout_s=timeout_s,
        ),
        "critic": LLMProviderConfig(
            provider_name="openai_compatible",
            vendor=vendor,
            base_url=base_url,
            api_key_env=api_key_env,
            model=critic_model,
            timeout_s=timeout_s,
        ),
    }
