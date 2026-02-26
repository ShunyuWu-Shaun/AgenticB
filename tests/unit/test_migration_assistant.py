from easyshift_maas.agentic.generator_agent import GeneratorAgent
from easyshift_maas.agentic.parser_agent import ParserAgent
from easyshift_maas.core.contracts import FieldDefinition, FieldDictionary, SceneMetadata


def _fields() -> FieldDictionary:
    return FieldDictionary(
        fields=[
            FieldDefinition(field_name="quality_index", semantic_label="quality", unit="ratio"),
            FieldDefinition(field_name="energy_cost", semantic_label="cost", unit="$/h"),
            FieldDefinition(field_name="pressure", semantic_label="pressure", unit="bar", controllable=True),
        ],
        alias_map={"b_t_01": "pressure"},
    )


def test_parser_rule_mapping_outputs_confidence() -> None:
    parser = ParserAgent(llm_client=None)
    result = parser.parse(field_dictionary=_fields(), legacy_points=["b_t_01", "unknown_tag"])

    assert result.strategy == "rule_fallback"
    assert result.confidence >= 0.0
    assert any(item.legacy_name == "b_t_01" for item in result.mappings)


def test_generator_produces_structured_draft_without_llm() -> None:
    generator = GeneratorAgent(llm_client=None)
    metadata = SceneMetadata(scene_id="quality-scene")
    draft = generator.generate(
        scene_metadata=metadata,
        field_dictionary=_fields(),
        nl_requirements=["prioritize stability"],
    )

    assert draft.template.template_id == "quality-scene-template"
    assert len(draft.template.objective.terms) >= 1
    assert draft.generation_strategy == "rule_fallback"
