from easyshift_maas.agentic.critic_agent import CriticAgent
from easyshift_maas.agentic.generator_agent import GeneratorAgent
from easyshift_maas.agentic.langgraph_workflow import LangGraphMigrationWorkflow
from easyshift_maas.agentic.parser_agent import ParserAgent
from easyshift_maas.agentic.template_validator import TemplateValidator
from easyshift_maas.core.contracts import FieldDefinition, FieldDictionary, SceneMetadata
from easyshift_maas.quality.template_quality import TemplateQualityEvaluator


def _fields() -> FieldDictionary:
    return FieldDictionary(
        fields=[
            FieldDefinition(field_name="energy_cost", semantic_label="cost", unit="$/h"),
            FieldDefinition(field_name="boiler_temp", semantic_label="temperature", unit="C", controllable=True),
            FieldDefinition(field_name="efficiency", semantic_label="efficiency", unit="ratio"),
        ]
    )


def test_reflection_loop_returns_report() -> None:
    workflow = LangGraphMigrationWorkflow(
        parser_agent=ParserAgent(llm_client=None),
        generator_agent=GeneratorAgent(llm_client=None),
        critic_agent=CriticAgent(llm_client=None),
        validator=TemplateValidator(),
        quality_evaluator=TemplateQualityEvaluator(),
    )

    report = workflow.run(
        scene_metadata=SceneMetadata(scene_id="wf-scene"),
        field_dictionary=_fields(),
        nl_requirements=["minimize energy while keeping efficiency high"],
        legacy_points=["B_TEMP_01", "ENERGY_COST"],
        max_iterations=3,
    )

    assert report.status.value in {"approved", "blocked"}
    assert report.iterations_used >= 1
    assert report.parser_result is not None


def test_critic_produces_instruction_on_failure() -> None:
    generator = GeneratorAgent(llm_client=None)
    metadata = SceneMetadata(scene_id="critic-scene")
    fields = _fields()
    draft = generator.generate(scene_metadata=metadata, field_dictionary=fields, nl_requirements=[])

    # Make draft invalid by removing guardrail rules from objective coverage.
    draft.template.guardrail.rules = []

    validator = TemplateValidator()
    quality = TemplateQualityEvaluator(validator=validator).evaluate(draft.template)
    report = validator.validate(draft)

    critic = CriticAgent(llm_client=None)
    feedback = critic.review(failed_draft=draft, validation_report=report, quality_report=quality)

    assert feedback.correction_instruction
    assert feedback.confidence >= 0.0
