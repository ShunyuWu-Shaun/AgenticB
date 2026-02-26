from __future__ import annotations

from typing import Optional

from easyshift_maas.agentic.critic_agent import CriticAgent
from easyshift_maas.agentic.generator_agent import GeneratorAgent
from easyshift_maas.agentic.parser_agent import ParserAgent
from easyshift_maas.agentic.template_validator import TemplateValidator
from easyshift_maas.core.contracts import (
    AgenticRunReport,
    AgenticRunState,
    AgenticRunStatus,
    FieldDictionary,
    IssueSeverity,
    MigrationDraft,
    ReflectionStep,
    SceneMetadata,
    SimulationSample,
    TemplateQualityGate,
)
from easyshift_maas.quality.template_quality import TemplateQualityEvaluator


class LangGraphMigrationWorkflow:
    """Reflection loop for Parser -> Generator -> Deterministic Gate -> Critic.

    This class keeps a LangGraph-friendly state structure. The runtime loop is
    deterministic and can be replaced by a compiled LangGraph graph in future versions.
    """

    def __init__(
        self,
        *,
        parser_agent: ParserAgent,
        generator_agent: GeneratorAgent,
        critic_agent: CriticAgent,
        validator: TemplateValidator | None = None,
        quality_evaluator: TemplateQualityEvaluator | None = None,
    ) -> None:
        self.parser_agent = parser_agent
        self.generator_agent = generator_agent
        self.critic_agent = critic_agent
        self.validator = validator or TemplateValidator()
        self.quality_evaluator = quality_evaluator or TemplateQualityEvaluator(validator=self.validator)

    def run(
        self,
        *,
        scene_metadata: SceneMetadata,
        field_dictionary: FieldDictionary,
        nl_requirements: list[str],
        legacy_points: list[str] | None = None,
        raw_yaml_text: str | None = None,
        regression_samples: list[SimulationSample] | None = None,
        gate: TemplateQualityGate | None = None,
        max_iterations: int = 3,
    ) -> AgenticRunReport:
        state = AgenticRunState(
            scene_metadata=scene_metadata,
            field_dictionary=field_dictionary,
            nl_requirements=nl_requirements,
        )

        parser_result = self.parser_agent.parse(
            field_dictionary=field_dictionary,
            legacy_points=legacy_points,
            raw_yaml_text=raw_yaml_text,
        )
        state.parser_result = parser_result

        correction_instruction: Optional[str] = None
        last_validation = None
        last_quality = None

        for iteration in range(1, max(1, max_iterations) + 1):
            state.iteration = iteration
            draft = self.generator_agent.generate(
                scene_metadata=scene_metadata,
                field_dictionary=field_dictionary,
                nl_requirements=nl_requirements,
                parser_result=parser_result,
                correction_instruction=correction_instruction,
                iteration=iteration,
            )

            validation = self.validator.validate(draft)
            quality = self.quality_evaluator.evaluate(
                template=draft.template,
                regression_samples=regression_samples,
                gate=gate,
            )

            validation_errors = [
                f"{item.code}: {item.message}"
                for item in validation.issues
                if item.severity == IssueSeverity.ERROR
            ]
            quality_errors = [
                f"{item.code}: {item.message}"
                for item in quality.issues
                if item.severity == IssueSeverity.ERROR
            ]

            if validation.valid and quality.passed:
                pass_step = ReflectionStep(
                    iteration=iteration,
                    draft_id=draft.draft_id,
                    validation_passed=True,
                    quality_passed=True,
                    validation_errors=[],
                    quality_errors=[],
                    critic_feedback=None,
                )
                state.reflections.append(pass_step)
                draft.trace = list(state.reflections)
                state.current_draft = draft
                return AgenticRunReport(
                    run_id=state.run_id,
                    status=AgenticRunStatus.APPROVED,
                    parser_result=parser_result,
                    final_draft=draft,
                    validation=validation,
                    quality=quality,
                    reflections=list(state.reflections),
                    iterations_used=iteration,
                    published=False,
                )

            critic = self.critic_agent.review(
                failed_draft=draft,
                validation_report=validation,
                quality_report=quality,
            )
            step = ReflectionStep(
                iteration=iteration,
                draft_id=draft.draft_id,
                validation_passed=validation.valid,
                quality_passed=quality.passed,
                validation_errors=validation_errors,
                quality_errors=quality_errors,
                critic_feedback=critic,
            )
            state.reflections.append(step)
            correction_instruction = critic.correction_instruction

            draft.trace = list(state.reflections)
            state.current_draft = draft
            last_validation = validation
            last_quality = quality

            if critic.is_fatal_error:
                return AgenticRunReport(
                    run_id=state.run_id,
                    status=AgenticRunStatus.BLOCKED,
                    parser_result=parser_result,
                    final_draft=draft,
                    validation=validation,
                    quality=quality,
                    reflections=list(state.reflections),
                    blocked_reason="critic_marked_fatal_error",
                    iterations_used=iteration,
                    published=False,
                )

        final_draft: MigrationDraft | None = state.current_draft
        return AgenticRunReport(
            run_id=state.run_id,
            status=AgenticRunStatus.BLOCKED,
            parser_result=parser_result,
            final_draft=final_draft,
            validation=last_validation,
            quality=last_quality,
            reflections=list(state.reflections),
            blocked_reason="max_iterations_reached",
            iterations_used=max_iterations,
            published=False,
        )
