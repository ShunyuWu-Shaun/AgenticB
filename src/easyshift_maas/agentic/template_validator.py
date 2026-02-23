from __future__ import annotations

from collections import defaultdict
from typing import Protocol

from easyshift_maas.core.contracts import (
    ConstraintOperator,
    IssueSeverity,
    MigrationDraft,
    MigrationValidationIssue,
    MigrationValidationReport,
)


class TemplateValidatorProtocol(Protocol):
    def validate(self, draft: MigrationDraft) -> MigrationValidationReport: ...


class TemplateValidator:
    """Validator for migration drafts with correctness and conflict metrics."""

    def validate(self, draft: MigrationDraft) -> MigrationValidationReport:
        issues: list[MigrationValidationIssue] = []
        template = draft.template
        fields = set(template.field_dictionary.field_names())

        if not template.objective.terms:
            issues.append(
                MigrationValidationIssue(
                    code="OBJ_EMPTY",
                    path="objective.terms",
                    message="Objective terms cannot be empty.",
                    severity=IssueSeverity.ERROR,
                )
            )

        for idx, term in enumerate(template.objective.terms):
            if term.field_name not in fields:
                issues.append(
                    MigrationValidationIssue(
                        code="OBJ_FIELD_UNKNOWN",
                        path=f"objective.terms[{idx}].field_name",
                        message=f"Unknown field in objective: {term.field_name}",
                        severity=IssueSeverity.ERROR,
                    )
                )

        for idx, feature in enumerate(template.prediction.feature_fields):
            if feature not in fields:
                issues.append(
                    MigrationValidationIssue(
                        code="PRED_FEATURE_UNKNOWN",
                        path=f"prediction.feature_fields[{idx}]",
                        message=f"Unknown prediction feature: {feature}",
                        severity=IssueSeverity.ERROR,
                    )
                )

        for idx, constraint in enumerate(template.constraints):
            if constraint.field_name not in fields:
                issues.append(
                    MigrationValidationIssue(
                        code="CONSTRAINT_FIELD_UNKNOWN",
                        path=f"constraints[{idx}].field_name",
                        message=f"Unknown field in constraint: {constraint.field_name}",
                        severity=IssueSeverity.ERROR,
                    )
                )

        conflict_count = self._check_constraint_conflicts(template.constraints, issues)
        guardrail_coverage = self._guardrail_coverage(template)
        correctness_score = self._correctness_score(issues)
        conflict_rate = (
            conflict_count / len(template.constraints)
            if template.constraints
            else 0.0
        )

        valid = (
            all(issue.severity != IssueSeverity.ERROR for issue in issues)
            and correctness_score >= 0.95
            and conflict_rate <= 0.02
            and guardrail_coverage >= 0.95
        )

        return MigrationValidationReport(
            draft_id=draft.draft_id,
            valid=valid,
            correctness_score=correctness_score,
            conflict_rate=conflict_rate,
            guardrail_coverage=guardrail_coverage,
            issues=issues,
        )

    def _check_constraint_conflicts(
        self,
        constraints,
        issues: list[MigrationValidationIssue],
    ) -> int:
        grouped: dict[str, list] = defaultdict(list)
        for constraint in constraints:
            grouped[constraint.field_name].append(constraint)

        conflicts = 0
        for field_name, items in grouped.items():
            lowers = [item.lower_bound for item in items if item.lower_bound is not None]
            uppers = [item.upper_bound for item in items if item.upper_bound is not None]
            equals = [item.equals_value for item in items if item.equals_value is not None]

            lower = max(lowers) if lowers else None
            upper = min(uppers) if uppers else None

            if lower is not None and upper is not None and lower > upper:
                conflicts += 1
                issues.append(
                    MigrationValidationIssue(
                        code="CONSTRAINT_CONFLICT_RANGE",
                        path=f"constraints[{field_name}]",
                        message=f"Conflicting range for {field_name}: lower {lower} > upper {upper}",
                        severity=IssueSeverity.ERROR,
                    )
                )

            if equals:
                eq = equals[0]
                if lower is not None and eq < lower:
                    conflicts += 1
                    issues.append(
                        MigrationValidationIssue(
                            code="CONSTRAINT_CONFLICT_EQ_LOW",
                            path=f"constraints[{field_name}]",
                            message=f"Equality value {eq} < lower bound {lower} for {field_name}",
                            severity=IssueSeverity.ERROR,
                        )
                    )
                if upper is not None and eq > upper:
                    conflicts += 1
                    issues.append(
                        MigrationValidationIssue(
                            code="CONSTRAINT_CONFLICT_EQ_HIGH",
                            path=f"constraints[{field_name}]",
                            message=f"Equality value {eq} > upper bound {upper} for {field_name}",
                            severity=IssueSeverity.ERROR,
                        )
                    )

            if all(item.operator == ConstraintOperator.EQ for item in items) and len(set(equals)) > 1:
                conflicts += 1
                issues.append(
                    MigrationValidationIssue(
                        code="CONSTRAINT_CONFLICT_MULTIPLE_EQ",
                        path=f"constraints[{field_name}]",
                        message=f"Multiple equality constraints conflict on {field_name}",
                        severity=IssueSeverity.ERROR,
                    )
                )

        return conflicts

    def _guardrail_coverage(self, template) -> float:
        objective_fields = {item.field_name for item in template.objective.terms}
        if not objective_fields:
            return 1.0
        guarded_fields = {item.field_name for item in template.guardrail.rules}
        covered = len(objective_fields.intersection(guarded_fields))
        return covered / len(objective_fields)

    def _correctness_score(self, issues: list[MigrationValidationIssue]) -> float:
        score = 1.0
        for issue in issues:
            if issue.severity == IssueSeverity.ERROR:
                score -= 0.2
            elif issue.severity == IssueSeverity.WARN:
                score -= 0.05
            else:
                score -= 0.01
        return max(0.0, round(score, 4))
