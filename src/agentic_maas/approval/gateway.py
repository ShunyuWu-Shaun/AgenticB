from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import RLock

from agentic_maas.types import ApprovalStatus, ApprovalTicket, DecisionAction, RiskLevel


RISK_ORDER = {
    RiskLevel.LOW: 0,
    RiskLevel.MEDIUM: 1,
    RiskLevel.HIGH: 2,
    RiskLevel.CRITICAL: 3,
}


@dataclass
class ApprovalPolicy:
    allowed_action_types: set[str] = field(default_factory=set)
    allowed_targets: set[str] = field(default_factory=set)
    reason_required_at_or_above: RiskLevel = RiskLevel.HIGH

    def validate_action(self, action: DecisionAction) -> None:
        if self.allowed_action_types and action.action_type not in self.allowed_action_types:
            raise ValueError(f"action_type not in whitelist: {action.action_type}")
        if self.allowed_targets and action.target not in self.allowed_targets:
            raise ValueError(f"target not in whitelist: {action.target}")


class ApprovalGateway:
    def __init__(self, policy: ApprovalPolicy | None = None) -> None:
        self.policy = policy or ApprovalPolicy()
        self._tickets: dict[str, ApprovalTicket] = {}
        self._signatures: dict[str, str] = {}
        self._lock = RLock()

    def create_ticket(self, action: DecisionAction) -> ApprovalTicket:
        self.policy.validate_action(action)
        ticket = ApprovalTicket(decision_action=action)
        with self._lock:
            self._tickets[ticket.ticket_id] = ticket
            self._signatures[ticket.ticket_id] = self._sign_action(action)
        return ticket

    def get_ticket(self, ticket_id: str) -> ApprovalTicket:
        with self._lock:
            ticket = self._tickets.get(ticket_id)
            if not ticket:
                raise KeyError(f"ticket not found: {ticket_id}")
            return ticket

    def approve(self, ticket_id: str, approver: str, reason: str | None = None) -> ApprovalTicket:
        with self._lock:
            ticket = self.get_ticket(ticket_id)
            if ticket.status != ApprovalStatus.PENDING:
                raise ValueError(f"ticket is not pending: {ticket.status}")

            if self._requires_reason(ticket.decision_action.risk_level) and not reason:
                raise ValueError("reason is required for high-risk approvals")

            updated = ticket.model_copy(
                update={
                    "status": ApprovalStatus.APPROVED,
                    "approver": approver,
                    "reason": reason,
                    "updated_at": datetime.now(tz=timezone.utc),
                }
            )
            self._tickets[ticket_id] = updated
            return updated

    def reject(self, ticket_id: str, approver: str, reason: str) -> ApprovalTicket:
        if not reason:
            raise ValueError("reason is required for rejection")
        with self._lock:
            ticket = self.get_ticket(ticket_id)
            if ticket.status != ApprovalStatus.PENDING:
                raise ValueError(f"ticket is not pending: {ticket.status}")
            updated = ticket.model_copy(
                update={
                    "status": ApprovalStatus.REJECTED,
                    "approver": approver,
                    "reason": reason,
                    "updated_at": datetime.now(tz=timezone.utc),
                }
            )
            self._tickets[ticket_id] = updated
            return updated

    def is_approved(self, ticket_id: str) -> bool:
        return self.get_ticket(ticket_id).status == ApprovalStatus.APPROVED

    def signature(self, ticket_id: str) -> str:
        with self._lock:
            if ticket_id not in self._signatures:
                raise KeyError(f"signature not found for ticket: {ticket_id}")
            return self._signatures[ticket_id]

    def _requires_reason(self, risk_level: RiskLevel) -> bool:
        return RISK_ORDER[risk_level] >= RISK_ORDER[self.policy.reason_required_at_or_above]

    def _sign_action(self, action: DecisionAction) -> str:
        payload = json.dumps(action.model_dump(mode="json"), sort_keys=True)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()
