from __future__ import annotations

from pathlib import Path

from easyshift_maas.agentic.prompts.output_schemas import GeneratorAgentOutput
from easyshift_maas.core.contracts import (
    ConstraintOperator,
    ConstraintSeverity,
    ConstraintSpec,
    FieldDictionary,
    GuardrailAction,
    GuardrailRule,
    GuardrailSpec,
    MigrationDraft,
    MigrationRisk,
    ObjectiveDirection,
    ObjectiveSpec,
    ObjectiveTerm,
    OptimizationSpec,
    ParserResult,
    PredictionSpec,
    ScenarioTemplate,
    SceneMetadata,
)
from easyshift_maas.llm.client import LLMClientProtocol


class GeneratorAgent:
    """Generate migration draft from semantic fields and natural language requirements."""

    def __init__(self, llm_client: LLMClientProtocol | None = None, prompt_path: str | None = None) -> None:
        self.llm_client = llm_client
        default_path = Path(__file__).with_name("prompts") / "generator_system.md"
        self.prompt = Path(prompt_path).read_text(encoding="utf-8") if prompt_path else default_path.read_text(encoding="utf-8")

    def generate(
        self,
        *,
        scene_metadata: SceneMetadata,
        field_dictionary: FieldDictionary,
        nl_requirements: list[str],
        parser_result: ParserResult | None = None,
        correction_instruction: str | None = None,
        iteration: int = 1,
    ) -> MigrationDraft:
        if self.llm_client is not None:
            try:
                return self._generate_with_llm(
                    scene_metadata=scene_metadata,
                    field_dictionary=field_dictionary,
                    nl_requirements=nl_requirements,
                    parser_result=parser_result,
                    correction_instruction=correction_instruction,
                    iteration=iteration,
                )
            except Exception as exc:  # noqa: BLE001
                draft = self._generate_with_rules(
                    scene_metadata=scene_metadata,
                    field_dictionary=field_dictionary,
                    nl_requirements=nl_requirements,
                    parser_result=parser_result,
                    iteration=iteration,
                )
                draft.risks.append(
                    MigrationRisk(
                        code="LLM_GENERATOR_UNAVAILABLE",
                        message=f"llm generator unavailable, fallback to rule generator: {exc}",
                    )
                )
                draft.generation_strategy = "rule_fallback"
                return draft

        return self._generate_with_rules(
            scene_metadata=scene_metadata,
            field_dictionary=field_dictionary,
            nl_requirements=nl_requirements,
            parser_result=parser_result,
            iteration=iteration,
        )

    def _generate_with_llm(
        self,
        *,
        scene_metadata: SceneMetadata,
        field_dictionary: FieldDictionary,
        nl_requirements: list[str],
        parser_result: ParserResult | None,
        correction_instruction: str | None,
        iteration: int,
    ) -> MigrationDraft:
        last_error: Exception | None = None
        output: GeneratorAgentOutput | None = None
        meta: dict[str, str] = {}
        for _ in range(2):
            try:
                payload, meta_payload = self.llm_client.complete_json(
                    role="generator",
                    system_prompt=self.prompt,
                    user_payload={
                        "scene_metadata": scene_metadata.model_dump(mode="json"),
                        "field_dictionary": field_dictionary.model_dump(mode="json"),
                        "nl_requirements": nl_requirements,
                        "parser_result": parser_result.model_dump(mode="json") if parser_result else None,
                        "correction_instruction": correction_instruction,
                    },
                    temperature=0.1,
                )
                output = GeneratorAgentOutput.model_validate(payload)
                meta = {key: str(value) for key, value in meta_payload.items()}
                break
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                continue

        if output is None:
            raise RuntimeError(f"generator llm output validation failed after retries: {last_error}")

        objective_terms = [
            ObjectiveTerm(
                field_name=item.field_name,
                direction=ObjectiveDirection(item.direction),
                weight=item.weight,
            )
            for item in output.objective.terms
            if field_dictionary.has_field(item.field_name)
        ]
        if not objective_terms:
            objective_terms = self._fallback_objective(field_dictionary)

        constraints: list[ConstraintSpec] = []
        for idx, item in enumerate(output.constraints):
            if not field_dictionary.has_field(item.field_name):
                continue
            operator = self._to_constraint_operator(item.operator)
            constraint = self._build_constraint(idx=idx, field_name=item.field_name, operator=operator, raw=item)
            if constraint is not None:
                constraints.append(constraint)

        rules: list[GuardrailRule] = []
        for item in output.guardrail.rules:
            if not field_dictionary.has_field(item.field_name):
                continue
            rules.append(
                GuardrailRule(
                    field_name=item.field_name,
                    min_value=item.min_value,
                    max_value=item.max_value,
                    max_delta=item.max_delta,
                    action=GuardrailAction(item.action),
                )
            )

        rules = self._ensure_objective_guardrail(rules=rules, objective_fields=[x.field_name for x in objective_terms])

        prediction_fields = output.prediction.feature_fields if output.prediction else []
        prediction_fields = [item for item in prediction_fields if field_dictionary.has_field(item)]
        if not prediction_fields:
            prediction_fields = self._default_prediction_fields(field_dictionary)

        horizon = output.prediction.horizon_steps if output.prediction else 3
        template = ScenarioTemplate(
            template_id=f"{scene_metadata.scene_id}-template",
            version=f"draft-{iteration}",
            scene_metadata=scene_metadata,
            field_dictionary=field_dictionary,
            objective=ObjectiveSpec(terms=objective_terms),
            constraints=constraints,
            prediction=PredictionSpec(
                feature_fields=prediction_fields,
                horizon_steps=max(1, horizon),
                model_signature="llm-draft:v1",
            ),
            optimization=OptimizationSpec(
                solver_name="projected-heuristic",
                max_iterations=80,
                tolerance=1e-6,
                time_budget_ms=400,
            ),
            guardrail=GuardrailSpec(rules=rules),
            notes=output.notes or "Generated by LLM generator agent.",
        )

        pending = []
        if correction_instruction:
            pending.append("Review whether correction instruction has been fully applied")
        if parser_result and parser_result.unmapped_points:
            pending.append("Confirm unmapped points before production rollout")

        base_conf = 0.84
        if parser_result:
            base_conf = min(0.95, 0.6 + parser_result.confidence * 0.4)
        confidence = round(base_conf - (0.04 if correction_instruction else 0.0), 4)

        return MigrationDraft(
            template=template,
            confidence=max(0.0, min(1.0, confidence)),
            pending_confirmations=pending,
            risks=[],
            generation_strategy="llm_primary",
            source_mappings=parser_result.mappings if parser_result else [],
            llm_metadata=meta,
        )

    def _generate_with_rules(
        self,
        *,
        scene_metadata: SceneMetadata,
        field_dictionary: FieldDictionary,
        nl_requirements: list[str],
        parser_result: ParserResult | None,
        iteration: int,
    ) -> MigrationDraft:
        objective_terms = self._fallback_objective(field_dictionary)
        prediction_fields = self._default_prediction_fields(field_dictionary)
        constraints = self._fallback_constraints(field_dictionary)

        guardrail_rules = [
            GuardrailRule(field_name=item.field_name, max_delta=0.2, action=GuardrailAction.CLIP)
            for item in objective_terms
        ]

        template = ScenarioTemplate(
            template_id=f"{scene_metadata.scene_id}-template",
            version=f"draft-{iteration}",
            scene_metadata=scene_metadata,
            field_dictionary=field_dictionary,
            objective=ObjectiveSpec(terms=objective_terms),
            constraints=constraints,
            prediction=PredictionSpec(
                feature_fields=prediction_fields,
                horizon_steps=max(1, min(12, scene_metadata.execution_window_sec // scene_metadata.granularity_sec)),
                model_signature="rule-bootstrap:v2",
            ),
            optimization=OptimizationSpec(
                solver_name="projected-heuristic",
                max_iterations=60,
                tolerance=1e-6,
                time_budget_ms=300,
            ),
            guardrail=GuardrailSpec(rules=guardrail_rules),
            notes="Generated by rule fallback generator.",
        )

        confidence = 0.52 if nl_requirements else 0.45
        pending = [
            "Confirm objective weights",
            "Confirm constraint ranges",
            "Confirm safety rule thresholds",
        ]
        if parser_result and parser_result.unmapped_points:
            pending.append("Resolve unmapped legacy points")

        return MigrationDraft(
            template=template,
            confidence=confidence,
            pending_confirmations=pending,
            risks=[],
            generation_strategy="rule_fallback",
            source_mappings=parser_result.mappings if parser_result else [],
            llm_metadata={"mode": "disabled"},
        )

    def _fallback_objective(self, field_dictionary: FieldDictionary) -> list[ObjectiveTerm]:
        terms: list[ObjectiveTerm] = []
        for field in field_dictionary.fields:
            token = f"{field.field_name} {field.semantic_label}".lower()
            if any(item in token for item in ["cost", "energy", "consumption", "emission"]):
                terms.append(ObjectiveTerm(field_name=field.field_name, direction=ObjectiveDirection.MIN, weight=1.0))
            elif any(item in token for item in ["yield", "quality", "efficiency"]):
                terms.append(ObjectiveTerm(field_name=field.field_name, direction=ObjectiveDirection.MAX, weight=1.0))

        if not terms and field_dictionary.fields:
            terms.append(
                ObjectiveTerm(
                    field_name=field_dictionary.fields[0].field_name,
                    direction=ObjectiveDirection.MIN,
                    weight=1.0,
                )
            )
        return terms[:3]

    def _fallback_constraints(self, field_dictionary: FieldDictionary) -> list[ConstraintSpec]:
        constraints: list[ConstraintSpec] = []
        for idx, field in enumerate(field_dictionary.fields):
            token = f"{field.field_name} {field.semantic_label}".lower()
            if "temperature" in token:
                constraints.append(
                    ConstraintSpec(
                        name=f"{field.field_name}_range",
                        field_name=field.field_name,
                        operator=ConstraintOperator.BETWEEN,
                        lower_bound=0.0,
                        upper_bound=1200.0,
                        severity=ConstraintSeverity.HARD,
                        priority=10 + idx,
                    )
                )
            elif "pressure" in token:
                constraints.append(
                    ConstraintSpec(
                        name=f"{field.field_name}_range",
                        field_name=field.field_name,
                        operator=ConstraintOperator.BETWEEN,
                        lower_bound=0.0,
                        upper_bound=500.0,
                        severity=ConstraintSeverity.HARD,
                        priority=10 + idx,
                    )
                )
        return constraints

    def _default_prediction_fields(self, field_dictionary: FieldDictionary) -> list[str]:
        names = field_dictionary.field_names()
        return names[: min(8, len(names))] if names else ["proxy_metric"]

    def _to_constraint_operator(self, value: str) -> ConstraintOperator:
        mapping = {
            ">=": ConstraintOperator.GE,
            "<=": ConstraintOperator.LE,
            "==": ConstraintOperator.EQ,
            "between": ConstraintOperator.BETWEEN,
        }
        return mapping[value]

    def _build_constraint(self, *, idx: int, field_name: str, operator: ConstraintOperator, raw) -> ConstraintSpec | None:
        if operator == ConstraintOperator.GE:
            if raw.value is None:
                return None
            return ConstraintSpec(
                name=f"{field_name}_ge_{idx}",
                field_name=field_name,
                operator=operator,
                lower_bound=raw.value,
                severity=ConstraintSeverity.HARD,
                priority=50 + idx,
            )
        if operator == ConstraintOperator.LE:
            if raw.value is None:
                return None
            return ConstraintSpec(
                name=f"{field_name}_le_{idx}",
                field_name=field_name,
                operator=operator,
                upper_bound=raw.value,
                severity=ConstraintSeverity.HARD,
                priority=50 + idx,
            )
        if operator == ConstraintOperator.EQ:
            if raw.value is None:
                return None
            return ConstraintSpec(
                name=f"{field_name}_eq_{idx}",
                field_name=field_name,
                operator=operator,
                equals_value=raw.value,
                severity=ConstraintSeverity.HARD,
                priority=50 + idx,
            )
        if operator == ConstraintOperator.BETWEEN:
            if raw.lower is None or raw.upper is None:
                return None
            return ConstraintSpec(
                name=f"{field_name}_between_{idx}",
                field_name=field_name,
                operator=operator,
                lower_bound=raw.lower,
                upper_bound=raw.upper,
                severity=ConstraintSeverity.HARD,
                priority=50 + idx,
            )
        return None

    def _ensure_objective_guardrail(self, *, rules: list[GuardrailRule], objective_fields: list[str]) -> list[GuardrailRule]:
        covered = {item.field_name for item in rules}
        for field_name in objective_fields:
            if field_name in covered:
                continue
            rules.append(GuardrailRule(field_name=field_name, max_delta=0.2, action=GuardrailAction.CLIP))
        return rules
