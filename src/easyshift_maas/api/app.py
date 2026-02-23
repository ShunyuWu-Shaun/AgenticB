from __future__ import annotations

from typing import Any, Optional

import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict, Field, model_validator

from easyshift_maas.agentic.migration_assistant import HybridMigrationAssistant
from easyshift_maas.agentic.template_validator import TemplateValidator
from easyshift_maas.core.contracts import (
    EvaluationReport,
    FieldDictionary,
    MigrationDraft,
    MigrationValidationReport,
    PipelineResult,
    ScenarioTemplate,
    SceneContext,
    SceneMetadata,
    SimulationSample,
)
from easyshift_maas.core.pipeline import PredictionOptimizationPipeline
from easyshift_maas.observability import instrument_fastapi
from easyshift_maas.templates.repository import InMemoryTemplateRepository


class ErrorResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    detail: str


class TemplateGenerateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scene_metadata: SceneMetadata = Field(
        examples=[
            {
                "scene_id": "synthetic-energy",
                "scenario_type": "efficiency",
                "tags": ["synthetic"],
                "granularity_sec": 60,
                "execution_window_sec": 300,
            }
        ]
    )
    field_dictionary: FieldDictionary = Field(
        examples=[
            {
                "fields": [
                    {
                        "field_name": "energy_cost",
                        "semantic_label": "cost",
                        "unit": "$/h",
                        "dimension": "dimensionless",
                        "observable": True,
                        "controllable": False,
                        "missing_strategy": "required",
                    }
                ],
                "alias_map": {},
            }
        ]
    )
    nl_requirements: list[str] = Field(default_factory=list, examples=[["prioritize stable operation"]])


class TemplatePublishRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    draft: MigrationDraft
    validate_before_publish: bool = True


class TemplatePublishResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    template_id: str
    version: str
    validation: MigrationValidationReport


class SimulateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scene_context: SceneContext = Field(
        examples=[{"values": {"energy_cost": 100.0, "boiler_temp": 560.0}, "metadata": {}}]
    )
    template_id: Optional[str] = None
    version: Optional[str] = None
    inline_template: Optional[ScenarioTemplate] = None

    @model_validator(mode="after")
    def _check_template_source(self) -> "SimulateRequest":
        has_id = self.template_id is not None
        has_inline = self.inline_template is not None
        if has_id == has_inline:
            raise ValueError("exactly one of template_id or inline_template must be provided")
        return self


class EvaluateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scenario_id: str
    samples: list[SimulationSample] = Field(
        default_factory=list,
        examples=[
            [
                {
                    "context": {"values": {"energy_cost": 100.0, "boiler_temp": 560.0}, "metadata": {}},
                    "expected_approved": True,
                }
            ]
        ],
    )
    template_id: Optional[str] = None
    version: Optional[str] = None
    inline_template: Optional[ScenarioTemplate] = None

    @model_validator(mode="after")
    def _check_template_source(self) -> "EvaluateRequest":
        has_id = self.template_id is not None
        has_inline = self.inline_template is not None
        if has_id == has_inline:
            raise ValueError("exactly one of template_id or inline_template must be provided")
        return self


app = FastAPI(title="EasyShift-MaaS", version="0.1.0")
instrument_fastapi(app)

assistant = HybridMigrationAssistant()
validator = TemplateValidator()
repository = InMemoryTemplateRepository()
pipeline = PredictionOptimizationPipeline()


@app.post("/v1/templates/generate", response_model=MigrationDraft)
def generate_template(request: TemplateGenerateRequest) -> MigrationDraft:
    return assistant.generate(
        scene_metadata=request.scene_metadata,
        field_dictionary=request.field_dictionary,
        nl_requirements=request.nl_requirements,
    )


@app.post("/v1/templates/validate", response_model=MigrationValidationReport)
def validate_template(draft: MigrationDraft) -> MigrationValidationReport:
    return validator.validate(draft)


@app.post(
    "/v1/templates/publish",
    response_model=TemplatePublishResponse,
    responses={400: {"model": ErrorResponse}},
)
def publish_template(request: TemplatePublishRequest) -> TemplatePublishResponse:
    report = validator.validate(request.draft)
    if request.validate_before_publish and not report.valid:
        raise HTTPException(
            status_code=400,
            detail={
                "message": "migration draft failed validation",
                "report": report.model_dump(mode="json"),
            },
        )

    published = repository.publish(request.draft.template)
    return TemplatePublishResponse(
        template_id=published.template_id,
        version=published.version,
        validation=report,
    )


@app.get(
    "/v1/templates/{template_id}",
    response_model=ScenarioTemplate,
    responses={404: {"model": ErrorResponse}},
)
def get_template(template_id: str, version: str | None = None) -> ScenarioTemplate:
    try:
        return repository.get(template_id, version)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post(
    "/v1/pipeline/simulate",
    response_model=PipelineResult,
    responses={404: {"model": ErrorResponse}},
)
def simulate(request: SimulateRequest) -> PipelineResult:
    template = _resolve_template(
        template_id=request.template_id,
        version=request.version,
        inline_template=request.inline_template,
    )
    return pipeline.run(request.scene_context, template)


@app.post(
    "/v1/pipeline/evaluate",
    response_model=EvaluationReport,
    responses={404: {"model": ErrorResponse}},
)
def evaluate(request: EvaluateRequest) -> EvaluationReport:
    if not request.samples:
        return EvaluationReport(
            scenario_id=request.scenario_id,
            total_runs=0,
            approval_rate=0.0,
            mean_objective=0.0,
            violation_rate=0.0,
            expectation_match_rate=None,
        )

    template = _resolve_template(
        template_id=request.template_id,
        version=request.version,
        inline_template=request.inline_template,
    )

    results = [pipeline.run(item.context, template) for item in request.samples]
    total = len(results)
    approvals = sum(1 for item in results if item.executed)
    mean_objective = sum(item.plan.objective_value for item in results) / total
    violations = sum(1 for item in results if item.guardrail.violations)

    expected_pairs = [
        (sample.expected_approved, result.executed)
        for sample, result in zip(request.samples, results)
        if sample.expected_approved is not None
    ]
    match_rate = None
    if expected_pairs:
        matches = sum(1 for expected, actual in expected_pairs if expected == actual)
        match_rate = matches / len(expected_pairs)

    return EvaluationReport(
        scenario_id=request.scenario_id,
        total_runs=total,
        approval_rate=approvals / total,
        mean_objective=mean_objective,
        violation_rate=violations / total,
        expectation_match_rate=match_rate,
    )


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "templates": len(repository.list_template_ids()),
        "components": {
            "migration_assistant": "ready",
            "template_validator": "ready",
            "pipeline": "ready",
        },
    }


def _resolve_template(
    template_id: Optional[str],
    version: Optional[str],
    inline_template: Optional[ScenarioTemplate],
) -> ScenarioTemplate:
    if inline_template is not None:
        return inline_template
    if template_id is None:
        raise HTTPException(status_code=400, detail="template_id is required")
    try:
        return repository.get(template_id, version)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


def run() -> None:
    uvicorn.run("easyshift_maas.api.app:app", host="0.0.0.0", port=8000, reload=False)
