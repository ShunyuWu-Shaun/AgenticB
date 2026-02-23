from __future__ import annotations

from typing import Protocol

from easyshift_maas.core.contracts import PipelineResult, ScenarioTemplate, SceneContext
from easyshift_maas.core.guardrail import GuardrailProtocol, RuleGuardrail
from easyshift_maas.core.optimizer import OptimizerProtocol, ProjectedHeuristicOptimizer
from easyshift_maas.core.predictor import HeuristicPredictor, PredictorProtocol


class PipelineProtocol(Protocol):
    def run(self, context: SceneContext, template: ScenarioTemplate) -> PipelineResult: ...


class PredictionOptimizationPipeline:
    """Composable predictor -> optimizer -> guardrail pipeline."""

    def __init__(
        self,
        predictor: PredictorProtocol | None = None,
        optimizer: OptimizerProtocol | None = None,
        guardrail: GuardrailProtocol | None = None,
    ) -> None:
        self.predictor = predictor or HeuristicPredictor()
        self.optimizer = optimizer or ProjectedHeuristicOptimizer()
        self.guardrail = guardrail or RuleGuardrail()

    def run(self, context: SceneContext, template: ScenarioTemplate) -> PipelineResult:
        prediction = self.predictor.predict(context, template.prediction)
        plan = self.optimizer.solve(
            prediction=prediction,
            objective=template.objective,
            constraints=template.constraints,
            optimization=template.optimization,
            context=context,
        )
        decision = self.guardrail.validate(plan, context, template.guardrail)
        final_setpoints = (
            decision.adjusted_setpoints if decision.approved else dict(context.values)
        )

        return PipelineResult(
            template_id=template.template_id,
            prediction=prediction,
            plan=plan,
            guardrail=decision,
            final_setpoints=final_setpoints,
            executed=decision.approved,
        )
