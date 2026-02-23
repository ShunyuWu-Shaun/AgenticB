from easyshift_maas.agentic.migration_assistant import HybridMigrationAssistant
from easyshift_maas.core.contracts import FieldDefinition, FieldDictionary, SceneMetadata


def test_low_confidence_fallback_path() -> None:
    assistant = HybridMigrationAssistant(llm_suggester=lambda _: {"objective_terms": []})

    metadata = SceneMetadata(scene_id="tiny-scene")
    fields = FieldDictionary(
        fields=[
            FieldDefinition(field_name="x", semantic_label="proxy", unit="u"),
        ]
    )

    draft = assistant.generate(metadata, fields, nl_requirements=[])

    assert draft.confidence < 0.78
    assert draft.generation_strategy == "rule_only_low_confidence"


def test_generate_structured_draft() -> None:
    assistant = HybridMigrationAssistant()
    metadata = SceneMetadata(scene_id="quality-scene")
    fields = FieldDictionary(
        fields=[
            FieldDefinition(field_name="quality_index", semantic_label="quality", unit="ratio"),
            FieldDefinition(field_name="energy_cost", semantic_label="cost", unit="$/h"),
            FieldDefinition(field_name="pressure", semantic_label="pressure", unit="bar", controllable=True),
        ]
    )

    draft = assistant.generate(metadata, fields, nl_requirements=["prioritize stability"])

    assert draft.template.template_id == "quality-scene-template"
    assert len(draft.template.objective.terms) >= 1
