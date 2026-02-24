from __future__ import annotations

from easyshift_maas.core.contracts import (
    ConstraintOperator,
    ConstraintSeverity,
    ConstraintSpec,
    FieldDefinition,
    FieldDictionary,
    GuardrailAction,
    GuardrailRule,
    GuardrailSpec,
    ObjectiveDirection,
    ObjectiveSpec,
    ObjectiveTerm,
    OptimizationSpec,
    PredictionSpec,
    ScenarioTemplate,
    SceneContext,
    SceneMetadata,
)


def build_energy_efficiency_template() -> ScenarioTemplate:
    metadata = SceneMetadata(scene_id="synthetic-energy", scenario_type="efficiency", tags=["synthetic"])
    fields = FieldDictionary(
        fields=[
            FieldDefinition(field_name="energy_cost", semantic_label="energy_cost", unit="$/h", observable=True),
            FieldDefinition(field_name="steam_flow", semantic_label="steam_flow", unit="t/h", observable=True, controllable=True),
            FieldDefinition(field_name="boiler_temp", semantic_label="temperature", unit="C", observable=True, controllable=True),
            FieldDefinition(field_name="efficiency", semantic_label="efficiency", unit="ratio", observable=True),
        ]
    )

    return ScenarioTemplate(
        template_id="synthetic-energy-template",
        version="v1",
        scene_metadata=metadata,
        field_dictionary=fields,
        objective=ObjectiveSpec(
            terms=[
                ObjectiveTerm(field_name="energy_cost", direction=ObjectiveDirection.MIN, weight=0.6),
                ObjectiveTerm(field_name="efficiency", direction=ObjectiveDirection.MAX, weight=0.4),
            ]
        ),
        constraints=[
            ConstraintSpec(
                name="steam_flow_nonnegative",
                field_name="steam_flow",
                operator=ConstraintOperator.GE,
                lower_bound=0.0,
                severity=ConstraintSeverity.HARD,
                priority=10,
            ),
            ConstraintSpec(
                name="boiler_temp_range",
                field_name="boiler_temp",
                operator=ConstraintOperator.BETWEEN,
                lower_bound=200.0,
                upper_bound=950.0,
                severity=ConstraintSeverity.HARD,
                priority=5,
            ),
        ],
        prediction=PredictionSpec(feature_fields=["energy_cost", "steam_flow", "boiler_temp", "efficiency"], horizon_steps=3),
        optimization=OptimizationSpec(solver_name="projected-heuristic", max_iterations=80, tolerance=1e-6, time_budget_ms=250),
        guardrail=GuardrailSpec(
            rules=[
                GuardrailRule(field_name="boiler_temp", min_value=250.0, max_value=900.0, max_delta=60.0, action=GuardrailAction.REJECT),
                GuardrailRule(field_name="steam_flow", min_value=0.0, max_delta=8.0, action=GuardrailAction.CLIP),
                GuardrailRule(field_name="energy_cost", min_value=0.0, max_delta=25.0, action=GuardrailAction.CLIP),
                GuardrailRule(field_name="efficiency", min_value=0.0, max_value=1.0, max_delta=0.08, action=GuardrailAction.CLIP),
            ]
        ),
        notes="Synthetic template for energy-efficiency tradeoff.",
    )


def build_quality_stability_template() -> ScenarioTemplate:
    metadata = SceneMetadata(scene_id="synthetic-quality", scenario_type="quality", tags=["synthetic"])
    fields = FieldDictionary(
        fields=[
            FieldDefinition(field_name="quality_index", semantic_label="quality", unit="ratio", observable=True),
            FieldDefinition(field_name="rework_rate", semantic_label="cost", unit="ratio", observable=True),
            FieldDefinition(field_name="line_speed", semantic_label="flow_rate", unit="u/min", observable=True, controllable=True),
            FieldDefinition(field_name="pressure", semantic_label="pressure", unit="bar", observable=True, controllable=True),
        ]
    )

    return ScenarioTemplate(
        template_id="synthetic-quality-template",
        version="v1",
        scene_metadata=metadata,
        field_dictionary=fields,
        objective=ObjectiveSpec(
            terms=[
                ObjectiveTerm(field_name="quality_index", direction=ObjectiveDirection.MAX, weight=0.7),
                ObjectiveTerm(field_name="rework_rate", direction=ObjectiveDirection.MIN, weight=0.3),
            ]
        ),
        constraints=[
            ConstraintSpec(
                name="line_speed_min",
                field_name="line_speed",
                operator=ConstraintOperator.GE,
                lower_bound=10.0,
                severity=ConstraintSeverity.SOFT,
                priority=20,
            ),
            ConstraintSpec(
                name="pressure_range",
                field_name="pressure",
                operator=ConstraintOperator.BETWEEN,
                lower_bound=1.0,
                upper_bound=20.0,
                severity=ConstraintSeverity.HARD,
                priority=10,
            ),
        ],
        prediction=PredictionSpec(feature_fields=["quality_index", "rework_rate", "line_speed", "pressure"], horizon_steps=2),
        optimization=OptimizationSpec(solver_name="projected-heuristic", max_iterations=50, tolerance=1e-6, time_budget_ms=180),
        guardrail=GuardrailSpec(
            rules=[
                GuardrailRule(field_name="pressure", min_value=2.0, max_value=18.0, max_delta=2.0, action=GuardrailAction.REJECT),
                GuardrailRule(field_name="line_speed", min_value=8.0, max_value=80.0, max_delta=10.0, action=GuardrailAction.CLIP),
                GuardrailRule(field_name="quality_index", min_value=0.0, max_value=1.0, max_delta=0.1, action=GuardrailAction.CLIP),
                GuardrailRule(field_name="rework_rate", min_value=0.0, max_value=1.0, max_delta=0.1, action=GuardrailAction.CLIP),
            ]
        ),
        notes="Synthetic template focused on quality-stability balance.",
    )


def sample_contexts() -> list[SceneContext]:
    return [
        SceneContext(values={"energy_cost": 100.0, "steam_flow": 35.0, "boiler_temp": 560.0, "efficiency": 0.82}),
        SceneContext(values={"quality_index": 0.88, "rework_rate": 0.04, "line_speed": 45.0, "pressure": 8.0}),
    ]
