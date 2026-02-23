from __future__ import annotations

from typing import Any

from agentic_maas.types import AlgorithmProfile


class AlgorithmTemplateMapper:
    """Map baseline algorithm profiles into agent-template-ready config."""

    DEFAULT_PARAMETER_MAP = {
        "alert_threshold": "decision_threshold",
        "window_size": "context_window",
        "sampling_interval": "sampling_seconds",
    }

    def map_profile(self, profile: AlgorithmProfile, baseline_params: dict[str, Any]) -> dict[str, Any]:
        mapped_params = self._map_parameters(baseline_params)

        return {
            "baseline_algo": profile.baseline_algo,
            "agent_template": profile.agent_template,
            "feature_set": profile.feature_set,
            "constraints": profile.constraints,
            "agent_parameters": mapped_params,
        }

    def _map_parameters(self, baseline_params: dict[str, Any]) -> dict[str, Any]:
        mapped: dict[str, Any] = {}
        for key, value in baseline_params.items():
            target_key = self.DEFAULT_PARAMETER_MAP.get(key, key)
            mapped[target_key] = value
        return mapped
