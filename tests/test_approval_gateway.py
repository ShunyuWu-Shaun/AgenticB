import pytest

from agentic_maas.approval.gateway import ApprovalGateway, ApprovalPolicy
from agentic_maas.types import DecisionAction, RiskLevel


def test_high_risk_approval_requires_reason() -> None:
    gateway = ApprovalGateway(
        ApprovalPolicy(
            allowed_action_types={"set_setpoint"},
            allowed_targets={"boiler-1"},
            reason_required_at_or_above=RiskLevel.HIGH,
        )
    )

    ticket = gateway.create_ticket(
        DecisionAction(
            action_type="set_setpoint",
            target="boiler-1",
            value=123.0,
            confidence=0.96,
            risk_level=RiskLevel.HIGH,
        )
    )

    with pytest.raises(ValueError):
        gateway.approve(ticket.ticket_id, approver="alice")

    approved = gateway.approve(ticket.ticket_id, approver="alice", reason="maintenance window")
    assert approved.status.value == "approved"
    assert gateway.is_approved(ticket.ticket_id) is True
