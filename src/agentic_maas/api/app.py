from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from agentic_maas.approval.gateway import ApprovalGateway, ApprovalPolicy
from agentic_maas.deployment.manager import DeploymentManager
from agentic_maas.evaluation.gate import QualityGate
from agentic_maas.evaluation.replay import ReplayEvaluator
from agentic_maas.ingestion.modbus import ModbusAdapter
from agentic_maas.ingestion.mqtt import MqttAdapter
from agentic_maas.ingestion.opcua import OpcUaAdapter
from agentic_maas.ingestion.registry import IngestionRegistry
from agentic_maas.observability import instrument_fastapi
from agentic_maas.providers.registry import ProviderRegistry
from agentic_maas.store.memory import InMemoryStore
from agentic_maas.types import (
    ApprovalRequest,
    ApprovalTicket,
    CanaryDeployment,
    CanaryRequest,
    DecisionAction,
    EvalReport,
    MigrationSpec,
    MigrationTask,
    ReplayEvalRequest,
    RiskLevel,
    RollbackRequest,
)


class DiscoverRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    endpoint: str
    auth: dict[str, str] = Field(default_factory=dict)


class ErrorResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    detail: str


app = FastAPI(title="agentic-maas", version="0.1.0")
instrument_fastapi(app)

store = InMemoryStore()
quality_gate = QualityGate()
replay_evaluator = ReplayEvaluator()
approval_gateway = ApprovalGateway(
    policy=ApprovalPolicy(
        allowed_action_types={
            "set_setpoint",
            "raise_alarm",
            "create_workorder",
        },
        allowed_targets={"line-1", "line-2"},
        reason_required_at_or_above=RiskLevel.HIGH,
    )
)
deployment_manager = DeploymentManager(store)
provider_registry = ProviderRegistry()
ingestion_registry = IngestionRegistry()
for adapter in (OpcUaAdapter(), ModbusAdapter(), MqttAdapter()):
    ingestion_registry.register(adapter)


@app.post("/v1/migrations", response_model=MigrationTask, status_code=201)
def create_migration(spec: MigrationSpec) -> MigrationTask:
    task = MigrationTask(
        spec=spec,
        logs=[f"created at {datetime.now(tz=timezone.utc).isoformat()}", "waiting_for_execution"],
    )
    store.save_migration(task)
    return task


@app.get(
    "/v1/migrations/{migration_id}",
    response_model=MigrationTask,
    responses={404: {"model": ErrorResponse}},
)
def get_migration(migration_id: str) -> MigrationTask:
    task = store.get_migration(migration_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"migration not found: {migration_id}")
    return task


@app.post("/v1/evals/replay", response_model=EvalReport)
def replay_eval(request: ReplayEvalRequest) -> EvalReport:
    report = replay_evaluator.evaluate(request.scenario_id, request.outcomes)
    store.save_eval_report(report)
    return report


@app.post("/v1/deployments/canary", response_model=CanaryDeployment, status_code=201)
def create_canary(request: CanaryRequest) -> CanaryDeployment:
    task = store.get_migration(request.migration_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"migration not found: {request.migration_id}")

    deployment = deployment_manager.create_canary(request, quality_gate)
    return deployment


@app.post("/v1/approvals", response_model=ApprovalTicket, status_code=201)
def create_approval_ticket(action: DecisionAction) -> ApprovalTicket:
    try:
        ticket = approval_gateway.create_ticket(action)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    store.audit("approval_ticket_created", {"ticket_id": ticket.ticket_id, "action_id": action.action_id})
    return ticket


@app.post(
    "/v1/approvals/{ticket_id}/approve",
    response_model=ApprovalTicket,
    responses={404: {"model": ErrorResponse}, 400: {"model": ErrorResponse}},
)
def approve_ticket(ticket_id: str, request: ApprovalRequest) -> ApprovalTicket:
    try:
        ticket = approval_gateway.approve(ticket_id, request.approver, request.reason)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    store.audit("approval_ticket_approved", {"ticket_id": ticket_id, "approver": request.approver})
    return ticket


@app.post(
    "/v1/deployments/{deployment_id}/rollback",
    response_model=CanaryDeployment,
    responses={404: {"model": ErrorResponse}},
)
def rollback(deployment_id: str, request: RollbackRequest) -> CanaryDeployment:
    try:
        deployment = deployment_manager.rollback(deployment_id, request.reason)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    store.audit("deployment_rolled_back", {"deployment_id": deployment_id, "reason": request.reason})
    return deployment


@app.post(
    "/v1/ingestion/{protocol}/discover",
    responses={404: {"model": ErrorResponse}},
)
def discover_points(protocol: str, request: DiscoverRequest) -> list[dict[str, Any]]:
    try:
        adapter = ingestion_registry.get(protocol)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    points = adapter.discover_points(request.endpoint, request.auth)
    return [point.model_dump() for point in points]


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "providers": provider_registry.health(),
        "protocols": ingestion_registry.protocols(),
        "audit_events": len(store.list_audit_events()),
    }


def run() -> None:
    uvicorn.run("agentic_maas.api.app:app", host="0.0.0.0", port=8000, reload=False)
