from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from easyshift_maas.core.contracts import ScenarioTemplate, SceneContext


class RegressionCase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    case_id: str
    description: str
    context: SceneContext
    expected_approved: bool


class RegressionPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    template_id: str
    cases: list[RegressionCase] = Field(default_factory=list)
    coverage: dict[str, float] = Field(default_factory=dict)


class RegressionPlanner:
    """Builds synthetic regression suites to verify migration correctness."""

    def build(self, template: ScenarioTemplate) -> RegressionPlan:
        cases: list[RegressionCase] = []
        nominal_values = {field.field_name: 1.0 for field in template.field_dictionary.fields}

        cases.append(
            RegressionCase(
                case_id="nominal",
                description="Nominal operating point",
                context=SceneContext(values=nominal_values),
                expected_approved=True,
            )
        )

        for idx, constraint in enumerate(template.constraints):
            if constraint.lower_bound is not None:
                values = dict(nominal_values)
                values[constraint.field_name] = constraint.lower_bound
                cases.append(
                    RegressionCase(
                        case_id=f"constraint-lower-{idx}",
                        description=f"Constraint lower boundary for {constraint.field_name}",
                        context=SceneContext(values=values),
                        expected_approved=True,
                    )
                )
            if constraint.upper_bound is not None:
                values = dict(nominal_values)
                values[constraint.field_name] = constraint.upper_bound
                cases.append(
                    RegressionCase(
                        case_id=f"constraint-upper-{idx}",
                        description=f"Constraint upper boundary for {constraint.field_name}",
                        context=SceneContext(values=values),
                        expected_approved=True,
                    )
                )

        for idx, rule in enumerate(template.guardrail.rules):
            if rule.max_value is not None:
                values = dict(nominal_values)
                values[rule.field_name] = rule.max_value + 1.0
                cases.append(
                    RegressionCase(
                        case_id=f"guardrail-breach-{idx}",
                        description=f"Guardrail breach case for {rule.field_name}",
                        context=SceneContext(values=values),
                        expected_approved=False,
                    )
                )

        coverage = {
            "constraint_case_ratio": round((len(template.constraints) / max(1, len(cases))), 4),
            "guardrail_case_ratio": round((len(template.guardrail.rules) / max(1, len(cases))), 4),
        }

        return RegressionPlan(template_id=template.template_id, cases=cases, coverage=coverage)
