from __future__ import annotations

from typing import Protocol

from easyshift_maas.agentic.generator_agent import GeneratorAgent
from easyshift_maas.core.contracts import FieldDictionary, MigrationDraft, SceneMetadata


class MigrationAssistantProtocol(Protocol):
    def generate(
        self,
        scene_metadata: SceneMetadata,
        field_dictionary: FieldDictionary,
        nl_requirements: list[str],
    ) -> MigrationDraft: ...


class HybridMigrationAssistant:
    """Compatibility wrapper around v0.3 GeneratorAgent."""

    def __init__(self) -> None:
        self._generator = GeneratorAgent(llm_client=None)

    def generate(
        self,
        scene_metadata: SceneMetadata,
        field_dictionary: FieldDictionary,
        nl_requirements: list[str],
    ) -> MigrationDraft:
        return self._generator.generate(
            scene_metadata=scene_metadata,
            field_dictionary=field_dictionary,
            nl_requirements=nl_requirements,
        )
