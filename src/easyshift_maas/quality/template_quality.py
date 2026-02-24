from __future__ import annotations

from typing import Iterable

from easyshift_maas.agentic.template_validator import TemplateValidator
from easyshift_maas.core.contracts import (
    IssueSeverity,
    MigrationDraft,
    ScenarioTemplate,
    SceneContext,
    SimulationSample,
    TemplateQualityGate,
    TemplateQualityIssue,
    TemplateQualityReport,
)
from easyshift_maas.core.pipeline import PredictionOptimizationPipeline


class TemplateQualityEvaluator:
    """Evaluate template quality with structural/semantic/solvability/guardrail/regression gates."""

    def __init__(
        self,
        pipeline: PredictionOptimizationPipeline | None = None,
        validator: TemplateValidator | None = None,
    ) -> None:
        self.pipeline = pipeline or PredictionOptimizationPipeline()
        self.validator = validator or TemplateValidator()

    def evaluate(
        self,
        template: ScenarioTemplate,
        regression_samples: list[SimulationSample] | None = None,
        gate: TemplateQualityGate | None = None,
    ) -> TemplateQualityReport:
        gate = gate or TemplateQualityGate()
        issues: list[TemplateQualityIssue] = []

        structural_score = self._structural_score(template, issues)

        validation = self.validator.validate(
            MigrationDraft(
                template=template,
                confidence=1.0,
                pending_confirmations=[],
                risks=[],
                generation_strategy="quality_check",
            )
        )

        semantic_score = self._semantic_score(template, validation, issues)

        samples = regression_samples or self._default_samples(template)
        pipeline_results = [self.pipeline.run(sample.context, template) for sample in samples]

        solvability_score = self._solvability_score(pipeline_results)
        guardrail_coverage = self._guardrail_coverage(template)
        regression_score = self._regression_score(samples, pipeline_results)

        overall_score = round(
            (structural_score + semantic_score + solvability_score + guardrail_coverage + regression_score) / 5.0,
            4,
        )

        for item in validation.issues:
            issues.append(
                TemplateQualityIssue(
                    code=item.code,
                    message=item.message,
                    severity=item.severity,
                )
            )

        self._append_threshold_issues(
            issues=issues,
            gate=gate,
            structural_score=structural_score,
            semantic_score=semantic_score,
            solvability_score=solvability_score,
            guardrail_coverage=guardrail_coverage,
            regression_score=regression_score,
            overall_score=overall_score,
        )

        passed = (
            structural_score >= gate.structural_min
            and semantic_score >= gate.semantic_min
            and solvability_score >= gate.solvability_min
            and guardrail_coverage >= gate.guardrail_min
            and regression_score >= gate.regression_min
            and overall_score >= gate.overall_min
        )

        return TemplateQualityReport(
            overall_score=overall_score,
            structural_score=structural_score,
            semantic_score=semantic_score,
            solvability_score=solvability_score,
            guardrail_coverage=guardrail_coverage,
            regression_score=regression_score,
            passed=passed,
            issues=issues,
        )

    def _structural_score(self, template: ScenarioTemplate, issues: list[TemplateQualityIssue]) -> float:
        try:
            ScenarioTemplate.model_validate(template.model_dump(mode="json"))
            return 1.0
        except Exception as exc:  # noqa: BLE001
            issues.append(
                TemplateQualityIssue(
                    code="STRUCTURAL_INVALID",
                    message=f"Template structure invalid: {exc}",
                    severity=IssueSeverity.ERROR,
                )
            )
            return 0.0

    def _semantic_score(self, template, validation, issues: list[TemplateQualityIssue]) -> float:
        fields = set(template.field_dictionary.field_names())

        references: list[str] = []
        references.extend(term.field_name for term in template.objective.terms)
        references.extend(template.prediction.feature_fields)
        references.extend(item.field_name for item in template.constraints)
        references.extend(item.field_name for item in template.guardrail.rules)

        if not references:
            return 1.0

        valid_refs = sum(1 for item in references if item in fields)
        unknown_guardrails = [item.field_name for item in template.guardrail.rules if item.field_name not in fields]
        for field in unknown_guardrails:
            issues.append(
                TemplateQualityIssue(
                    code="GUARDRAIL_FIELD_UNKNOWN",
                    message=f"Unknown field in guardrail: {field}",
                    severity=IssueSeverity.ERROR,
                )
            )

        score = round(valid_refs / len(references), 4)
        if validation.conflict_rate > 0:
            score = max(0.0, round(score - validation.conflict_rate, 4))
        return score

    def _solvability_score(self, pipeline_results: Iterable) -> float:
        results = list(pipeline_results)
        if not results:
            return 0.0
        solved = sum(1 for item in results if item.plan.solver_status == "solved")
        return round(solved / len(results), 4)

    def _guardrail_coverage(self, template: ScenarioTemplate) -> float:
        objective_fields = {item.field_name for item in template.objective.terms}
        controllable_fields = {
            item.field_name for item in template.field_dictionary.fields if item.controllable
        }
        target = objective_fields.union(controllable_fields)
        if not target:
            return 1.0
        covered = {item.field_name for item in template.guardrail.rules}
        return round(len(target.intersection(covered)) / len(target), 4)

    def _regression_score(self, samples: list[SimulationSample], results: list) -> float:
        if not results:
            return 0.0

        total = len(results)
        violations = sum(1 for item in results if item.guardrail.violations)
        violation_rate = violations / total

        expected_pairs = [
            (sample.expected_approved, result.executed)
            for sample, result in zip(samples, results)
            if sample.expected_approved is not None
        ]

        if expected_pairs:
            matches = sum(1 for expected, actual in expected_pairs if expected == actual)
            match_rate = matches / len(expected_pairs)
        else:
            match_rate = 1.0 - violation_rate

        score = 0.7 * match_rate + 0.3 * (1.0 - violation_rate)
        return round(max(0.0, min(1.0, score)), 4)

    def _default_samples(self, template: ScenarioTemplate) -> list[SimulationSample]:
        nominal = {item.field_name: 1.0 for item in template.field_dictionary.fields}

        for constraint in template.constraints:
            field = constraint.field_name
            if constraint.operator.value == "ge" and constraint.lower_bound is not None:
                nominal[field] = constraint.lower_bound + max(1.0, abs(constraint.lower_bound) * 0.05)
            elif constraint.operator.value == "le" and constraint.upper_bound is not None:
                nominal[field] = constraint.upper_bound - max(1.0, abs(constraint.upper_bound) * 0.05)
            elif (
                constraint.operator.value == "between"
                and constraint.lower_bound is not None
                and constraint.upper_bound is not None
            ):
                nominal[field] = (constraint.lower_bound + constraint.upper_bound) / 2.0
            elif constraint.operator.value == "eq" and constraint.equals_value is not None:
                nominal[field] = constraint.equals_value

        for rule in template.guardrail.rules:
            field = rule.field_name
            if rule.min_value is not None and rule.max_value is not None:
                nominal[field] = (rule.min_value + rule.max_value) / 2.0
            elif rule.min_value is not None:
                nominal[field] = rule.min_value + max(0.1, abs(rule.min_value) * 0.05)
            elif rule.max_value is not None:
                nominal[field] = rule.max_value - max(0.1, abs(rule.max_value) * 0.05)

        stressed = dict(nominal)
        for field in template.field_dictionary.fields:
            if not field.controllable:
                continue
            base = stressed[field.field_name]
            max_delta = next(
                (
                    rule.max_delta
                    for rule in template.guardrail.rules
                    if rule.field_name == field.field_name and rule.max_delta is not None
                ),
                None,
            )
            if max_delta is not None:
                stressed[field.field_name] = base + (max_delta * 0.5)
            else:
                stressed[field.field_name] = base * 1.05

        return [
            SimulationSample(context=SceneContext(values=nominal, metadata={}), expected_approved=True),
            SimulationSample(context=SceneContext(values=stressed, metadata={}), expected_approved=True),
        ]

    def _append_threshold_issues(
        self,
        *,
        issues: list[TemplateQualityIssue],
        gate: TemplateQualityGate,
        structural_score: float,
        semantic_score: float,
        solvability_score: float,
        guardrail_coverage: float,
        regression_score: float,
        overall_score: float,
    ) -> None:
        checks = [
            ("STRUCTURAL_LOW", structural_score, gate.structural_min, "structural score below threshold"),
            ("SEMANTIC_LOW", semantic_score, gate.semantic_min, "semantic score below threshold"),
            ("SOLVABILITY_LOW", solvability_score, gate.solvability_min, "solvability score below threshold"),
            ("GUARDRAIL_LOW", guardrail_coverage, gate.guardrail_min, "guardrail coverage below threshold"),
            ("REGRESSION_LOW", regression_score, gate.regression_min, "regression score below threshold"),
            ("OVERALL_LOW", overall_score, gate.overall_min, "overall quality score below threshold"),
        ]
        for code, score, target, message in checks:
            if score < target:
                issues.append(
                    TemplateQualityIssue(
                        code=code,
                        message=f"{message}: {score:.4f} < {target:.4f}",
                        severity=IssueSeverity.ERROR,
                    )
                )
