from __future__ import annotations

from pathlib import Path

from easyshift_maas.agentic.prompts.output_schemas import CriticAgentOutput
from easyshift_maas.core.contracts import CriticFeedback, MigrationDraft, MigrationValidationReport, TemplateQualityReport
from easyshift_maas.llm.client import LLMClientProtocol


class CriticAgent:
    """Review failed drafts and produce concrete correction instructions."""

    def __init__(self, llm_client: LLMClientProtocol | None = None, prompt_path: str | None = None) -> None:
        self.llm_client = llm_client
        default_path = Path(__file__).with_name("prompts") / "critic_system.md"
        self.prompt = Path(prompt_path).read_text(encoding="utf-8") if prompt_path else default_path.read_text(encoding="utf-8")

    def review(
        self,
        *,
        failed_draft: MigrationDraft,
        validation_report: MigrationValidationReport,
        quality_report: TemplateQualityReport,
    ) -> CriticFeedback:
        if self.llm_client is not None:
            try:
                return self._review_with_llm(
                    failed_draft=failed_draft,
                    validation_report=validation_report,
                    quality_report=quality_report,
                )
            except Exception as exc:  # noqa: BLE001
                feedback = self._review_with_rules(
                    failed_draft=failed_draft,
                    validation_report=validation_report,
                    quality_report=quality_report,
                )
                feedback.analysis = f"{feedback.analysis}; llm critic unavailable: {exc}"
                return feedback

        return self._review_with_rules(
            failed_draft=failed_draft,
            validation_report=validation_report,
            quality_report=quality_report,
        )

    def _review_with_llm(
        self,
        *,
        failed_draft: MigrationDraft,
        validation_report: MigrationValidationReport,
        quality_report: TemplateQualityReport,
    ) -> CriticFeedback:
        result: CriticAgentOutput | None = None
        last_error: Exception | None = None
        for _ in range(2):
            try:
                payload, _meta = self.llm_client.complete_json(
                    role="critic",
                    system_prompt=self.prompt,
                    user_payload={
                        "failed_draft": failed_draft.model_dump(mode="json"),
                        "validation_report": validation_report.model_dump(mode="json"),
                        "quality_report": quality_report.model_dump(mode="json"),
                    },
                    temperature=0.0,
                )
                result = CriticAgentOutput.model_validate(payload)
                break
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                continue

        if result is None:
            raise RuntimeError(f"critic llm output validation failed after retries: {last_error}")
        return CriticFeedback(
            is_fatal_error=result.is_fatal_error,
            analysis=result.analysis,
            correction_instruction=result.correction_instruction,
            confidence=0.85,
        )

    def _review_with_rules(
        self,
        *,
        failed_draft: MigrationDraft,
        validation_report: MigrationValidationReport,
        quality_report: TemplateQualityReport,
    ) -> CriticFeedback:
        errors = [f"{item.code}: {item.message}" for item in validation_report.issues]
        quality_errors = [f"{item.code}: {item.message}" for item in quality_report.issues]

        analysis_parts = []
        if errors:
            analysis_parts.append("Validation issues detected")
        if quality_errors:
            analysis_parts.append("Quality threshold issues detected")

        analysis = "; ".join(analysis_parts) if analysis_parts else "Draft failed without explicit issue list"

        instruction = "Ensure objective fields exist in field_dictionary and add guardrail coverage for objective fields"
        if any("CONSTRAINT_CONFLICT" in item.code for item in validation_report.issues):
            instruction = "Resolve conflicting constraint bounds so every field has feasible range"
        elif any(item.code == "GUARDRAIL_LOW" for item in quality_report.issues):
            instruction = "Add or widen guardrail rules to cover all objective and controllable fields"
        elif any("UNKNOWN" in item.code for item in validation_report.issues):
            instruction = "Replace unknown fields with valid field_dictionary entries and regenerate constraints"

        fatal = quality_report.structural_score < 0.5
        if not failed_draft.template.field_dictionary.fields:
            fatal = True
            instruction = "Provide a non-empty field_dictionary before generating draft"

        return CriticFeedback(
            is_fatal_error=fatal,
            analysis=analysis,
            correction_instruction=instruction,
            confidence=0.62,
        )
