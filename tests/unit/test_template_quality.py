from easyshift_maas.core.contracts import GuardrailSpec, TemplateQualityGate
from easyshift_maas.examples.synthetic_templates import build_energy_efficiency_template
from easyshift_maas.quality.template_quality import TemplateQualityEvaluator


def test_template_quality_passes_for_base_template() -> None:
    template = build_energy_efficiency_template()
    report = TemplateQualityEvaluator().evaluate(template)

    assert report.passed is True
    assert report.overall_score >= 0.95


def test_template_quality_blocks_when_guardrail_coverage_low() -> None:
    template = build_energy_efficiency_template()
    template = template.model_copy(update={"guardrail": GuardrailSpec(rules=[])})

    gate = TemplateQualityGate(guardrail_min=0.95, overall_min=0.95)
    report = TemplateQualityEvaluator().evaluate(template, gate=gate)

    assert report.passed is False
    assert any(item.code == "GUARDRAIL_LOW" for item in report.issues)
