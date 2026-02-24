from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator


def now_utc() -> datetime:
    return datetime.now(tz=timezone.utc)


class ObjectiveDirection(str, Enum):
    MIN = "min"
    MAX = "max"


class ConstraintSeverity(str, Enum):
    HARD = "hard"
    SOFT = "soft"


class ConstraintOperator(str, Enum):
    LE = "le"
    GE = "ge"
    EQ = "eq"
    BETWEEN = "between"


class GuardrailAction(str, Enum):
    REJECT = "reject"
    WARN = "warn"
    CLIP = "clip"


class MissingValueStrategy(str, Enum):
    REQUIRED = "required"
    DROP = "drop"
    ZERO = "zero"
    FORWARD_FILL = "forward_fill"
    MEAN = "mean"


class IssueSeverity(str, Enum):
    ERROR = "error"
    WARN = "warn"
    INFO = "info"


class DataSourceKind(str, Enum):
    REDIS = "redis"
    MYSQL = "mysql"


class CatalogLoadMode(str, Enum):
    STANDARD = "standard"
    LEGACY = "legacy"


class SnapshotMissingPolicy(str, Enum):
    ERROR = "error"
    DROP = "drop"
    ZERO = "zero"


class SceneMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scene_id: str
    scenario_type: str = "generic"
    tags: list[str] = Field(default_factory=list)
    granularity_sec: int = Field(default=60, gt=0)
    execution_window_sec: int = Field(default=300, gt=0)


class DataSourceOptions(BaseModel):
    model_config = ConfigDict(extra="forbid")

    batch_size: int = Field(default=500, ge=1, le=5000)
    timeout_ms: int = Field(default=500, ge=1)
    tls: bool = False
    retries: int = Field(default=1, ge=0, le=10)
    mysql_table: str = "point_snapshot"
    mysql_point_column: str = "point_id"
    mysql_value_column: str = "value"
    mysql_ts_column: Optional[str] = None


class DataSourceProfile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    kind: DataSourceKind
    conn_ref: str
    options: DataSourceOptions = Field(default_factory=DataSourceOptions)


class PointBinding(BaseModel):
    model_config = ConfigDict(extra="forbid")

    point_id: str
    source_type: DataSourceKind
    source_ref: str
    field_name: str
    unit: str = "dimensionless"
    transform: Optional[str] = None
    enabled: bool = True
    tags: list[str] = Field(default_factory=list)


class PointCatalog(BaseModel):
    model_config = ConfigDict(extra="forbid")

    catalog_id: str
    version: str = "v1"
    bindings: list[PointBinding] = Field(default_factory=list)
    refresh_sec: int = Field(default=30, ge=1)
    source_profile: str = "default"
    created_at: datetime = Field(default_factory=now_utc)

    @model_validator(mode="after")
    def _ensure_unique_points(self) -> "PointCatalog":
        ids = [item.point_id for item in self.bindings]
        if len(ids) != len(set(ids)):
            raise ValueError("point_id must be unique in point catalog")
        return self


class SnapshotRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    catalog_id: str
    fields: Optional[list[str]] = None
    at: Optional[datetime] = None
    missing_policy: SnapshotMissingPolicy = SnapshotMissingPolicy.ERROR


class SnapshotResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    values: dict[str, float] = Field(default_factory=dict)
    quality_flags: dict[str, str] = Field(default_factory=dict)
    missing_fields: list[str] = Field(default_factory=list)
    source_latency_ms: dict[str, int] = Field(default_factory=dict)
    collected_at: datetime = Field(default_factory=now_utc)


class FieldDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    field_name: str
    semantic_label: str
    unit: str
    dimension: str = "dimensionless"
    observable: bool = True
    controllable: bool = False
    missing_strategy: MissingValueStrategy = MissingValueStrategy.REQUIRED


class FieldDictionary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    fields: list[FieldDefinition] = Field(default_factory=list)
    alias_map: dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _ensure_unique_fields(self) -> "FieldDictionary":
        names = [item.field_name for item in self.fields]
        if len(names) != len(set(names)):
            raise ValueError("field_name must be unique in field dictionary")
        return self

    def has_field(self, field_name: str) -> bool:
        return field_name in {item.field_name for item in self.fields}

    def field_names(self) -> list[str]:
        return [item.field_name for item in self.fields]


class ObjectiveTerm(BaseModel):
    model_config = ConfigDict(extra="forbid")

    field_name: str
    direction: ObjectiveDirection
    weight: float = Field(gt=0)


class ObjectiveSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    terms: list[ObjectiveTerm] = Field(min_length=1)
    normalize_weights: bool = True

    @model_validator(mode="after")
    def _normalize(self) -> "ObjectiveSpec":
        if not self.normalize_weights:
            return self
        total = sum(term.weight for term in self.terms)
        if total <= 0:
            raise ValueError("sum of objective weights must be positive")
        for term in self.terms:
            term.weight = term.weight / total
        self.normalize_weights = False
        return self


class ConstraintSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    field_name: str
    operator: ConstraintOperator
    lower_bound: Optional[float] = None
    upper_bound: Optional[float] = None
    equals_value: Optional[float] = None
    priority: int = Field(default=100, ge=0)
    severity: ConstraintSeverity = ConstraintSeverity.HARD

    @model_validator(mode="after")
    def _validate_bounds(self) -> "ConstraintSpec":
        if self.operator == ConstraintOperator.LE and self.upper_bound is None:
            raise ValueError("upper_bound is required for operator=le")
        if self.operator == ConstraintOperator.GE and self.lower_bound is None:
            raise ValueError("lower_bound is required for operator=ge")
        if self.operator == ConstraintOperator.EQ and self.equals_value is None:
            raise ValueError("equals_value is required for operator=eq")
        if self.operator == ConstraintOperator.BETWEEN:
            if self.lower_bound is None or self.upper_bound is None:
                raise ValueError("both lower_bound and upper_bound are required for operator=between")
            if self.lower_bound > self.upper_bound:
                raise ValueError("lower_bound must be <= upper_bound for operator=between")
        return self


class PredictionSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    feature_fields: list[str] = Field(min_length=1)
    horizon_steps: int = Field(default=1, ge=1)
    model_signature: str = "heuristic:v1"


class OptimizationSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    solver_name: str = "projected-heuristic"
    max_iterations: int = Field(default=50, ge=1)
    tolerance: float = Field(default=1e-6, gt=0)
    time_budget_ms: int = Field(default=200, ge=1)


class GuardrailRule(BaseModel):
    model_config = ConfigDict(extra="forbid")

    field_name: str
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    max_delta: Optional[float] = None
    action: GuardrailAction = GuardrailAction.REJECT


class GuardrailSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rules: list[GuardrailRule] = Field(default_factory=list)
    fallback_policy: str = "keep_previous"


class ScenarioTemplate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    template_id: str
    version: str
    scene_metadata: SceneMetadata
    field_dictionary: FieldDictionary
    objective: ObjectiveSpec
    constraints: list[ConstraintSpec] = Field(default_factory=list)
    prediction: PredictionSpec
    optimization: OptimizationSpec
    guardrail: GuardrailSpec = Field(default_factory=GuardrailSpec)
    notes: Optional[str] = None
    created_at: datetime = Field(default_factory=now_utc)


class MigrationRisk(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str
    message: str
    severity: IssueSeverity = IssueSeverity.WARN


class MigrationDraft(BaseModel):
    model_config = ConfigDict(extra="forbid")

    draft_id: str = Field(default_factory=lambda: f"draft-{uuid4().hex}")
    template: ScenarioTemplate
    confidence: float = Field(ge=0.0, le=1.0)
    pending_confirmations: list[str] = Field(default_factory=list)
    risks: list[MigrationRisk] = Field(default_factory=list)
    generation_strategy: str = "rule_only"


class MigrationValidationIssue(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str
    path: str
    message: str
    severity: IssueSeverity


class MigrationValidationReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    draft_id: str
    valid: bool
    correctness_score: float = Field(ge=0.0, le=1.0)
    conflict_rate: float = Field(ge=0.0, le=1.0)
    guardrail_coverage: float = Field(ge=0.0, le=1.0)
    issues: list[MigrationValidationIssue] = Field(default_factory=list)


class TemplateQualityGate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    structural_min: float = Field(default=0.98, ge=0.0, le=1.0)
    semantic_min: float = Field(default=0.98, ge=0.0, le=1.0)
    solvability_min: float = Field(default=0.95, ge=0.0, le=1.0)
    guardrail_min: float = Field(default=0.95, ge=0.0, le=1.0)
    regression_min: float = Field(default=0.90, ge=0.0, le=1.0)
    overall_min: float = Field(default=0.95, ge=0.0, le=1.0)


class TemplateQualityIssue(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str
    message: str
    severity: IssueSeverity


class TemplateQualityReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    overall_score: float = Field(ge=0.0, le=1.0)
    structural_score: float = Field(ge=0.0, le=1.0)
    semantic_score: float = Field(ge=0.0, le=1.0)
    solvability_score: float = Field(ge=0.0, le=1.0)
    guardrail_coverage: float = Field(ge=0.0, le=1.0)
    regression_score: float = Field(ge=0.0, le=1.0)
    passed: bool
    issues: list[TemplateQualityIssue] = Field(default_factory=list)


class SceneContext(BaseModel):
    model_config = ConfigDict(extra="forbid")

    values: dict[str, float] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=now_utc)


class ContextBuildResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scene_context: SceneContext
    snapshot: SnapshotResult


class PredictionResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    predictions: dict[str, float] = Field(default_factory=dict)
    model_signature: str
    diagnostics: dict[str, Any] = Field(default_factory=dict)


class OptimizationPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    recommended_setpoints: dict[str, float] = Field(default_factory=dict)
    objective_value: float
    solver_status: str
    diagnostics: dict[str, Any] = Field(default_factory=dict)


class GuardrailDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    approved: bool
    violations: list[str] = Field(default_factory=list)
    action: GuardrailAction
    adjusted_setpoints: dict[str, float] = Field(default_factory=dict)


class PipelineResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    template_id: str
    prediction: PredictionResult
    plan: OptimizationPlan
    guardrail: GuardrailDecision
    final_setpoints: dict[str, float] = Field(default_factory=dict)
    executed: bool


class SimulationSample(BaseModel):
    model_config = ConfigDict(extra="forbid")

    context: SceneContext
    expected_approved: Optional[bool] = None


class EvaluationReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scenario_id: str
    total_runs: int = Field(ge=0)
    approval_rate: float = Field(ge=0.0, le=1.0)
    mean_objective: float
    violation_rate: float = Field(ge=0.0, le=1.0)
    expectation_match_rate: Optional[float] = Field(default=None, ge=0.0, le=1.0)
