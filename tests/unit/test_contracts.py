import pytest

from easyshift_maas.core.contracts import (
    AgenticRunStatus,
    ConstraintOperator,
    ConstraintSpec,
    MigrationDraft,
    ObjectiveDirection,
    ObjectiveSpec,
    ObjectiveTerm,
)
from easyshift_maas.examples.synthetic_templates import build_energy_efficiency_template


def test_objective_weights_are_normalized() -> None:
    objective = ObjectiveSpec(
        terms=[
            ObjectiveTerm(field_name="a", direction=ObjectiveDirection.MIN, weight=2.0),
            ObjectiveTerm(field_name="b", direction=ObjectiveDirection.MAX, weight=1.0),
        ]
    )

    weights = [item.weight for item in objective.terms]
    assert round(sum(weights), 6) == 1.0
    assert weights[0] > weights[1]


def test_invalid_between_constraint_raises() -> None:
    with pytest.raises(ValueError):
        ConstraintSpec(
            name="bad",
            field_name="x",
            operator=ConstraintOperator.BETWEEN,
            lower_bound=10,
            upper_bound=1,
        )


def test_migration_draft_has_agentic_trace_fields() -> None:
    template = build_energy_efficiency_template()
    draft = MigrationDraft(template=template, confidence=0.8)

    assert draft.trace == []
    assert draft.source_mappings == []
    assert isinstance(draft.llm_metadata, dict)


def test_agentic_status_enum_values() -> None:
    assert AgenticRunStatus.APPROVED.value == "approved"
    assert AgenticRunStatus.BLOCKED.value == "blocked"
