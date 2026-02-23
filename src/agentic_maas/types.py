from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


def now_utc() -> datetime:
    return datetime.now(tz=timezone.utc)


class ProtocolType(str, Enum):
    OPC_UA = "opcua"
    MODBUS = "modbus"
    MQTT = "mqtt"


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ApprovalStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class MigrationStatus(str, Enum):
    CREATED = "created"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class DeploymentStatus(str, Enum):
    CREATED = "created"
    ACTIVE = "active"
    BLOCKED = "blocked"
    ROLLED_BACK = "rolled_back"


class SensorPoint(BaseModel):
    model_config = ConfigDict(extra="forbid")

    point_id: str
    protocol: ProtocolType
    address: str
    unit: str
    sampling_hz: float = Field(gt=0)
    quality_flags: list[str] = Field(default_factory=list)
    tags: dict[str, str] = Field(default_factory=dict)


class PointMappingRule(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_expr: str
    target_field: str
    unit_transform: dict[str, float] = Field(default_factory=dict)
    validation_rule: dict[str, float] = Field(default_factory=dict)


class MigrationSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_system: str
    point_rules: list[PointMappingRule] = Field(default_factory=list)
    algo_template: str
    eval_plan: dict[str, Any] = Field(default_factory=dict)
    rollout_plan: dict[str, Any] = Field(default_factory=dict)


class AlgorithmProfile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    baseline_algo: str
    agent_template: str
    feature_set: list[str] = Field(default_factory=list)
    constraints: dict[str, Any] = Field(default_factory=dict)


class DecisionAction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action_id: str = Field(default_factory=lambda: f"act-{uuid4().hex}")
    action_type: str
    target: str
    value: float
    confidence: float = Field(ge=0.0, le=1.0)
    risk_level: RiskLevel = RiskLevel.MEDIUM


class ApprovalTicket(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ticket_id: str = Field(default_factory=lambda: f"apr-{uuid4().hex}")
    decision_action: DecisionAction
    approver: str | None = None
    status: ApprovalStatus = ApprovalStatus.PENDING
    reason: str | None = None
    created_at: datetime = Field(default_factory=now_utc)
    updated_at: datetime = Field(default_factory=now_utc)


class EvalReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scenario_id: str
    pass_rate: float = Field(ge=0.0, le=1.0)
    latency_p95: float = Field(ge=0.0)
    safety_violations: int = Field(ge=0)
    false_positive_rate: float = Field(default=0.0, ge=0.0, le=1.0)
    false_negative_rate: float = Field(default=0.0, ge=0.0, le=1.0)


class MigrationTask(BaseModel):
    model_config = ConfigDict(extra="forbid")

    migration_id: str = Field(default_factory=lambda: f"mig-{uuid4().hex}")
    spec: MigrationSpec
    status: MigrationStatus = MigrationStatus.CREATED
    logs: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=now_utc)
    updated_at: datetime = Field(default_factory=now_utc)


class ReplayOutcome(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expected: bool
    predicted: bool
    latency_ms: float = Field(default=0.0, ge=0.0)
    safety_violation: bool = False


class ReplayEvalRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scenario_id: str
    outcomes: list[ReplayOutcome] = Field(default_factory=list)


class CanaryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    migration_id: str
    traffic_percent: int = Field(ge=1, le=100)
    eval_report: EvalReport


class CanaryDeployment(BaseModel):
    model_config = ConfigDict(extra="forbid")

    deployment_id: str = Field(default_factory=lambda: f"dep-{uuid4().hex}")
    migration_id: str
    traffic_percent: int = Field(ge=1, le=100)
    status: DeploymentStatus = DeploymentStatus.CREATED
    reason: str | None = None
    created_at: datetime = Field(default_factory=now_utc)
    updated_at: datetime = Field(default_factory=now_utc)


class ApprovalRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    approver: str
    reason: str | None = None


class RollbackRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: str = "manual rollback"
