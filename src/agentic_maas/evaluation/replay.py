from __future__ import annotations

from math import ceil

from agentic_maas.types import EvalReport, ReplayOutcome


class ReplayEvaluator:
    def evaluate(self, scenario_id: str, outcomes: list[ReplayOutcome]) -> EvalReport:
        if not outcomes:
            return EvalReport(
                scenario_id=scenario_id,
                pass_rate=0.0,
                latency_p95=0.0,
                safety_violations=0,
                false_positive_rate=0.0,
                false_negative_rate=0.0,
            )

        total = len(outcomes)
        correct = sum(1 for item in outcomes if item.expected == item.predicted)
        pass_rate = correct / total

        positive_total = sum(1 for item in outcomes if item.expected)
        negative_total = total - positive_total
        false_positive = sum(1 for item in outcomes if (not item.expected) and item.predicted)
        false_negative = sum(1 for item in outcomes if item.expected and (not item.predicted))

        fpr = false_positive / negative_total if negative_total else 0.0
        fnr = false_negative / positive_total if positive_total else 0.0

        p95 = self._p95([item.latency_ms for item in outcomes])
        safety_violations = sum(1 for item in outcomes if item.safety_violation)

        return EvalReport(
            scenario_id=scenario_id,
            pass_rate=pass_rate,
            latency_p95=p95,
            safety_violations=safety_violations,
            false_positive_rate=fpr,
            false_negative_rate=fnr,
        )

    def _p95(self, values: list[float]) -> float:
        if not values:
            return 0.0
        sorted_values = sorted(values)
        idx = max(0, min(len(sorted_values) - 1, ceil(len(sorted_values) * 0.95) - 1))
        return sorted_values[idx]
