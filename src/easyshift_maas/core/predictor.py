from __future__ import annotations

from typing import Protocol

from easyshift_maas.core.contracts import PredictionResult, PredictionSpec, SceneContext


class PredictorProtocol(Protocol):
    def predict(self, context: SceneContext, spec: PredictionSpec) -> PredictionResult: ...


class PredictorRegistry:
    def __init__(self) -> None:
        self._predictors: dict[str, PredictorProtocol] = {}

    def register(self, name: str, predictor: PredictorProtocol) -> None:
        self._predictors[name] = predictor

    def get(self, name: str) -> PredictorProtocol:
        if name not in self._predictors:
            raise KeyError(f"predictor not found: {name}")
        return self._predictors[name]

    def names(self) -> list[str]:
        return sorted(self._predictors.keys())


class HeuristicPredictor:
    """A deterministic reference predictor for synthetic examples and tests."""

    def predict(self, context: SceneContext, spec: PredictionSpec) -> PredictionResult:
        predictions: dict[str, float] = {}
        for field in spec.feature_fields:
            baseline = context.values.get(field, 0.0)
            horizon_gain = 1.0 + min(spec.horizon_steps, 10) * 0.005
            predictions[field] = baseline * horizon_gain

        return PredictionResult(
            predictions=predictions,
            model_signature=spec.model_signature,
            diagnostics={
                "strategy": "heuristic",
                "horizon_steps": spec.horizon_steps,
                "covered_features": len(predictions),
            },
        )
