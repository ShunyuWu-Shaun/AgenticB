from __future__ import annotations

from typing import Protocol

from easyshift_maas.core.contracts import (
    GuardrailAction,
    GuardrailDecision,
    GuardrailSpec,
    OptimizationPlan,
    SceneContext,
)


class GuardrailProtocol(Protocol):
    def validate(
        self,
        plan: OptimizationPlan,
        context: SceneContext,
        guardrail: GuardrailSpec,
    ) -> GuardrailDecision: ...


class RuleGuardrail:
    """Reference guardrail: reject or clip candidate setpoints by rules."""

    def validate(
        self,
        plan: OptimizationPlan,
        context: SceneContext,
        guardrail: GuardrailSpec,
    ) -> GuardrailDecision:
        adjusted = dict(plan.recommended_setpoints)
        violations: list[str] = []
        dominant_action = GuardrailAction.WARN

        for rule in guardrail.rules:
            if rule.field_name not in adjusted:
                violations.append(f"missing field in plan: {rule.field_name}")
                dominant_action = self._escalate(dominant_action, GuardrailAction.REJECT)
                continue

            value = adjusted[rule.field_name]
            baseline = context.values.get(rule.field_name)

            violated = False
            if rule.min_value is not None and value < rule.min_value:
                violations.append(f"{rule.field_name} below minimum {rule.min_value}")
                violated = True
                if rule.action == GuardrailAction.CLIP:
                    adjusted[rule.field_name] = rule.min_value
            if rule.max_value is not None and value > rule.max_value:
                violations.append(f"{rule.field_name} above maximum {rule.max_value}")
                violated = True
                if rule.action == GuardrailAction.CLIP:
                    adjusted[rule.field_name] = rule.max_value
            if rule.max_delta is not None and baseline is not None:
                if abs(value - baseline) > rule.max_delta:
                    violations.append(
                        f"{rule.field_name} delta {abs(value - baseline):.4f} > {rule.max_delta}"
                    )
                    violated = True
                    if rule.action == GuardrailAction.CLIP:
                        if value > baseline:
                            adjusted[rule.field_name] = baseline + rule.max_delta
                        else:
                            adjusted[rule.field_name] = baseline - rule.max_delta

            if violated:
                dominant_action = self._escalate(dominant_action, rule.action)

        if dominant_action == GuardrailAction.REJECT:
            return GuardrailDecision(
                approved=False,
                violations=violations,
                action=GuardrailAction.REJECT,
                adjusted_setpoints=dict(context.values),
            )

        return GuardrailDecision(
            approved=True,
            violations=violations,
            action=dominant_action,
            adjusted_setpoints=adjusted,
        )

    def _escalate(self, current: GuardrailAction, incoming: GuardrailAction) -> GuardrailAction:
        order = {
            GuardrailAction.WARN: 0,
            GuardrailAction.CLIP: 1,
            GuardrailAction.REJECT: 2,
        }
        return incoming if order[incoming] > order[current] else current
