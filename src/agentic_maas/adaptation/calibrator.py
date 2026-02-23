from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class CalibrationResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    temperature: float = Field(ge=0.0, le=2.0)
    threshold: float = Field(ge=0.0, le=1.0)
    score: float = Field(ge=0.0, le=1.0)


class OfflineCalibrator:
    """Grid-search calibration for temperature/threshold before online rollout."""

    def tune(
        self,
        replay_samples: list[dict[str, float | bool]],
        temperatures: list[float] | None = None,
        thresholds: list[float] | None = None,
    ) -> CalibrationResult:
        temperatures = temperatures or [0.1, 0.2, 0.4, 0.7]
        thresholds = thresholds or [0.5, 0.6, 0.7, 0.8]

        best = CalibrationResult(temperature=temperatures[0], threshold=thresholds[0], score=0.0)
        for t in temperatures:
            for thr in thresholds:
                score = self._score(replay_samples, temperature=t, threshold=thr)
                if score > best.score:
                    best = CalibrationResult(temperature=t, threshold=thr, score=score)
        return best

    def _score(self, replay_samples: list[dict[str, float | bool]], temperature: float, threshold: float) -> float:
        if not replay_samples:
            return 0.0
        correct = 0
        for sample in replay_samples:
            probability = float(sample.get("probability", 0.0))
            expected = bool(sample.get("expected", False))
            # Temperature-aware soft scaling as an approximation for offline tuning.
            adjusted = max(0.0, min(1.0, probability * (1 - 0.1 * temperature)))
            predicted = adjusted >= threshold
            if predicted == expected:
                correct += 1

        accuracy = correct / len(replay_samples)
        # Mild regularization so very high temperature is discouraged in industrial setting.
        return max(0.0, min(1.0, accuracy - 0.02 * temperature))
