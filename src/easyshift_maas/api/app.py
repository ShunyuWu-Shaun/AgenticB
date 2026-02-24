from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict, Field, model_validator

from easyshift_maas.agentic.migration_assistant import HybridMigrationAssistant
from easyshift_maas.agentic.template_validator import TemplateValidator
from easyshift_maas.core.contracts import (
    CatalogLoadMode,
    ContextBuildResult,
    DataSourceProfile,
    EvaluationReport,
    FieldDictionary,
    MigrationDraft,
    MigrationValidationReport,
    PipelineResult,
    ScenarioTemplate,
    SceneContext,
    SceneMetadata,
    SimulationSample,
    SnapshotMissingPolicy,
    SnapshotRequest,
    TemplateQualityGate,
    TemplateQualityReport,
)
from easyshift_maas.core.pipeline import PredictionOptimizationPipeline
from easyshift_maas.ingestion.catalog_loader import YamlCatalogLoader
from easyshift_maas.ingestion.providers.mysql_provider import MySQLSnapshotProvider
from easyshift_maas.ingestion.providers.redis_provider import RedisSnapshotProvider
from easyshift_maas.ingestion.repository import InMemoryCatalogRepository, InMemoryDataSourceRegistry
from easyshift_maas.ingestion.snapshot_provider import CompositeSnapshotProvider
from easyshift_maas.observability import instrument_fastapi
from easyshift_maas.quality.template_quality import TemplateQualityEvaluator
from easyshift_maas.security.secrets import ChainedSecretResolver
from easyshift_maas.templates.base import BaseTemplateInfo, list_base_templates
from easyshift_maas.templates.repository import InMemoryTemplateRepository
from easyshift_maas.templates.schema import scenario_template_schema


class ErrorResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    detail: Any


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
    enforce_quality_gate: bool = True
    quality_gate: TemplateQualityGate = Field(default_factory=TemplateQualityGate)
    regression_samples: list[SimulationSample] = Field(default_factory=list)


class TemplatePublishResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    template_id: str
    version: str
    validation: MigrationValidationReport
    quality: TemplateQualityReport


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


class CatalogImportRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mode: CatalogLoadMode = CatalogLoadMode.STANDARD
    yaml_text: Optional[str] = None
    yaml_path: Optional[str] = None
    source_profiles: list[DataSourceProfile] = Field(default_factory=list)

    @model_validator(mode="after")
    def _check_yaml_input(self) -> "CatalogImportRequest":
        has_text = self.yaml_text is not None
        has_path = self.yaml_path is not None
        if has_text == has_path:
            raise ValueError("exactly one of yaml_text or yaml_path must be provided")
        return self


class CatalogImportResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    catalog_id: str
    binding_count: int
    warnings: list[str] = Field(default_factory=list)
    pending_confirmations: list[str] = Field(default_factory=list)


class ContextBuildRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    catalog_id: str
    fields: Optional[list[str]] = None
    at: Optional[datetime] = None
    missing_policy: SnapshotMissingPolicy = SnapshotMissingPolicy.ERROR
    scene_metadata: Optional[SceneMetadata] = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class QualityCheckRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    draft: Optional[MigrationDraft] = None
    template: Optional[ScenarioTemplate] = None
    gate: TemplateQualityGate = Field(default_factory=TemplateQualityGate)
    regression_samples: list[SimulationSample] = Field(default_factory=list)

    @model_validator(mode="after")
    def _check_source(self) -> "QualityCheckRequest":
        has_draft = self.draft is not None
        has_template = self.template is not None
        if has_draft == has_template:
            raise ValueError("exactly one of draft or template must be provided")
        return self


class BaseTemplatesResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    templates: list[BaseTemplateInfo]
    template_schema: dict[str, Any]


app = FastAPI(title="EasyShift-MaaS", version="0.2.0")
instrument_fastapi(app)

assistant = HybridMigrationAssistant()
validator = TemplateValidator()
template_repository = InMemoryTemplateRepository()
catalog_repository = InMemoryCatalogRepository()
datasource_registry = InMemoryDataSourceRegistry()
loader = YamlCatalogLoader()
secret_resolver = ChainedSecretResolver()
snapshot_provider = CompositeSnapshotProvider(
    providers=[RedisSnapshotProvider(), MySQLSnapshotProvider()]
)
pipeline = PredictionOptimizationPipeline()
quality_evaluator = TemplateQualityEvaluator(pipeline=pipeline, validator=validator)


@app.post("/v1/catalogs/import", response_model=CatalogImportResponse)
def import_catalog(request: CatalogImportRequest) -> CatalogImportResponse:
    result = loader.load(yaml_text=request.yaml_text, yaml_path=request.yaml_path, mode=request.mode)

    merged_profiles = list(result.source_profiles)
    merged_profiles.extend(request.source_profiles)
    if merged_profiles:
        datasource_registry.upsert_many(merged_profiles)

    catalog_repository.put(result.catalog)

    return CatalogImportResponse(
        catalog_id=result.catalog.catalog_id,
        binding_count=len(result.catalog.bindings),
        warnings=result.warnings,
        pending_confirmations=result.pending_confirmations,
    )


@app.get(
    "/v1/catalogs/{catalog_id}",
    responses={404: {"model": ErrorResponse}},
)
def get_catalog(catalog_id: str):
    try:
        return catalog_repository.get(catalog_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post(
    "/v1/contexts/build",
    response_model=ContextBuildResult,
    responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)
def build_context(request: ContextBuildRequest) -> ContextBuildResult:
    try:
        catalog = catalog_repository.get(request.catalog_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    snapshot_request = SnapshotRequest(
        catalog_id=request.catalog_id,
        fields=request.fields,
        at=request.at,
        missing_policy=request.missing_policy,
    )
    profiles = datasource_registry.list_profiles()
    snapshot = snapshot_provider.fetch(
        request=snapshot_request,
        catalog=catalog,
        profiles=profiles,
        secret_resolver=secret_resolver,
    )

    if request.missing_policy == SnapshotMissingPolicy.ERROR and snapshot.missing_fields:
        raise HTTPException(
            status_code=400,
            detail={
                "message": "missing fields in snapshot",
                "missing_fields": snapshot.missing_fields,
                "quality_flags": snapshot.quality_flags,
            },
        )

    context_meta = dict(request.metadata)
    if request.scene_metadata is not None:
        context_meta["scene_id"] = request.scene_metadata.scene_id
        context_meta["scenario_type"] = request.scene_metadata.scenario_type

    context = SceneContext(values=snapshot.values, metadata=context_meta)
    return ContextBuildResult(scene_context=context, snapshot=snapshot)


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


@app.post("/v1/templates/quality-check", response_model=TemplateQualityReport)
def quality_check_template(request: QualityCheckRequest) -> TemplateQualityReport:
    template = request.template if request.template is not None else request.draft.template  # type: ignore[union-attr]
    return quality_evaluator.evaluate(
        template=template,
        regression_samples=request.regression_samples,
        gate=request.gate,
    )


@app.get("/v1/templates/base", response_model=BaseTemplatesResponse)
def list_templates_base() -> BaseTemplatesResponse:
    return BaseTemplatesResponse(
        templates=list_base_templates(),
        template_schema=scenario_template_schema(),
    )


@app.post(
    "/v1/templates/publish",
    response_model=TemplatePublishResponse,
    responses={400: {"model": ErrorResponse}},
)
def publish_template(request: TemplatePublishRequest) -> TemplatePublishResponse:
    validation = validator.validate(request.draft)
    if request.validate_before_publish and not validation.valid:
        raise HTTPException(
            status_code=400,
            detail={
                "message": "migration draft failed validation",
                "report": validation.model_dump(mode="json"),
            },
        )

    quality = quality_evaluator.evaluate(
        template=request.draft.template,
        regression_samples=request.regression_samples,
        gate=request.quality_gate,
    )
    if request.enforce_quality_gate and not quality.passed:
        raise HTTPException(
            status_code=400,
            detail={
                "message": "template failed quality gate",
                "validation": validation.model_dump(mode="json"),
                "quality": quality.model_dump(mode="json"),
            },
        )

    published = template_repository.publish(request.draft.template)
    return TemplatePublishResponse(
        template_id=published.template_id,
        version=published.version,
        validation=validation,
        quality=quality,
    )


@app.get(
    "/v1/templates/{template_id}",
    response_model=ScenarioTemplate,
    responses={404: {"model": ErrorResponse}},
)
def get_template(template_id: str, version: Optional[str] = None) -> ScenarioTemplate:
    try:
        return template_repository.get(template_id, version)
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
        "templates": len(template_repository.list_template_ids()),
        "catalogs": len(catalog_repository.list_catalog_ids()),
        "data_sources": len(datasource_registry.list_profiles()),
        "components": {
            "migration_assistant": "ready",
            "template_validator": "ready",
            "template_quality": "ready",
            "snapshot_provider": "ready",
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
        return template_repository.get(template_id, version)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


def run() -> None:
    uvicorn.run("easyshift_maas.api.app:app", host="0.0.0.0", port=8000, reload=False)
