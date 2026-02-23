from __future__ import annotations

from collections.abc import Callable
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict

from agentic_maas.approval.gateway import ApprovalGateway
from agentic_maas.types import ApprovalTicket, DecisionAction


class RuntimeState(str, Enum):
    PERCEIVE = "perceive"
    ANALYZE = "analyze"
    DECIDE = "decide"
    APPROVAL_PENDING = "approval_pending"
    EXECUTE = "execute"
    FALLBACK = "fallback"
    DONE = "done"


class RuntimeResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    state: RuntimeState
    observation: dict[str, Any]
    features: dict[str, Any]
    action: DecisionAction
    approval_ticket: ApprovalTicket
    execution_result: dict[str, Any] | None = None


class AgentRuntime:
    """State-machine runtime: perceive -> analyze -> decide -> approve -> execute."""

    def __init__(self, approval_gateway: ApprovalGateway) -> None:
        self.approval_gateway = approval_gateway

    def run_cycle(
        self,
        payload: dict[str, Any],
        analyze_fn: Callable[[dict[str, Any]], dict[str, Any]],
        decide_fn: Callable[[dict[str, Any]], DecisionAction],
    ) -> RuntimeResult:
        observation = payload
        features = analyze_fn(observation)
        action = decide_fn(features)
        ticket = self.approval_gateway.create_ticket(action)

        return RuntimeResult(
            state=RuntimeState.APPROVAL_PENDING,
            observation=observation,
            features=features,
            action=action,
            approval_ticket=ticket,
            execution_result=None,
        )

    def execute_approved(
        self,
        ticket_id: str,
        execute_fn: Callable[[DecisionAction], dict[str, Any]],
    ) -> dict[str, Any]:
        if not self.approval_gateway.is_approved(ticket_id):
            raise PermissionError("action execution is blocked until approval")
        ticket = self.approval_gateway.get_ticket(ticket_id)
        return execute_fn(ticket.decision_action)
