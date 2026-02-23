from fastapi.testclient import TestClient

from agentic_maas.api.app import app


client = TestClient(app)


def test_api_main_flow() -> None:
    create_resp = client.post(
        "/v1/migrations",
        json={
            "source_system": "plant-A",
            "point_rules": [
                {
                    "source_expr": "point_id:opcua-temp-001",
                    "target_field": "boiler_temp",
                    "unit_transform": {"scale": 1.0, "offset": 0.0},
                    "validation_rule": {"min": 0, "max": 1000},
                }
            ],
            "algo_template": "boiler-guardian-v1",
            "eval_plan": {"min_pass_rate": 0.95},
            "rollout_plan": {"step": [5, 20, 50]},
        },
    )
    assert create_resp.status_code == 201
    migration = create_resp.json()

    get_resp = client.get(f"/v1/migrations/{migration['migration_id']}")
    assert get_resp.status_code == 200

    eval_resp = client.post(
        "/v1/evals/replay",
        json={
            "scenario_id": "scenario-1",
            "outcomes": [
                {"expected": True, "predicted": True, "latency_ms": 100, "safety_violation": False},
                {"expected": False, "predicted": False, "latency_ms": 120, "safety_violation": False},
                {"expected": True, "predicted": True, "latency_ms": 110, "safety_violation": False},
            ],
        },
    )
    assert eval_resp.status_code == 200
    report = eval_resp.json()

    canary_resp = client.post(
        "/v1/deployments/canary",
        json={
            "migration_id": migration["migration_id"],
            "traffic_percent": 10,
            "eval_report": report,
        },
    )
    assert canary_resp.status_code == 201
    deployment = canary_resp.json()
    assert deployment["status"] == "active"

    ticket_resp = client.post(
        "/v1/approvals",
        json={
            "action_type": "set_setpoint",
            "target": "boiler-1",
            "value": 88,
            "confidence": 0.92,
            "risk_level": "high",
        },
    )
    # boiler-1 target is not in whitelist in API policy, expect rejection.
    assert ticket_resp.status_code == 400

    safe_ticket = client.post(
        "/v1/approvals",
        json={
            "action_type": "raise_alarm",
            "target": "line-1",
            "value": 1,
            "confidence": 0.90,
            "risk_level": "medium",
        },
    )
    assert safe_ticket.status_code == 201
    ticket = safe_ticket.json()

    approve_resp = client.post(
        f"/v1/approvals/{ticket['ticket_id']}/approve",
        json={"approver": "operator-1", "reason": "confirmed"},
    )
    assert approve_resp.status_code == 200
    assert approve_resp.json()["status"] == "approved"

    rollback_resp = client.post(
        f"/v1/deployments/{deployment['deployment_id']}/rollback",
        json={"reason": "manual safety rollback"},
    )
    assert rollback_resp.status_code == 200
    assert rollback_resp.json()["status"] == "rolled_back"
