from easyshift_maas.core.pipeline import PredictionOptimizationPipeline
from easyshift_maas.examples.synthetic_templates import build_energy_efficiency_template
from easyshift_maas.core.contracts import SceneContext


def test_pipeline_simulate_success() -> None:
    template = build_energy_efficiency_template()
    context = SceneContext(values={"energy_cost": 100.0, "steam_flow": 30.0, "boiler_temp": 560.0, "efficiency": 0.8})

    result = PredictionOptimizationPipeline().run(context, template)

    assert result.template_id == template.template_id
    assert result.plan.solver_status in {"solved", "infeasible"}
    assert "energy_cost" in result.final_setpoints


def test_pipeline_guardrail_rejects_high_risk_value() -> None:
    template = build_energy_efficiency_template()
    context = SceneContext(values={"energy_cost": 100.0, "steam_flow": 30.0, "boiler_temp": 2000.0, "efficiency": 0.8})

    result = PredictionOptimizationPipeline().run(context, template)

    assert result.executed is False
    assert result.guardrail.action.value == "reject"
