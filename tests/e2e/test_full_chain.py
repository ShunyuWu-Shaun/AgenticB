from fastapi.testclient import TestClient

from easyshift_maas.api.app import app


client = TestClient(app)


def _field_dictionary() -> dict:
    return {
        "fields": [
            {
                "field_name": "quality_index",
                "semantic_label": "quality",
                "unit": "ratio",
                "dimension": "dimensionless",
                "observable": True,
                "controllable": False,
                "missing_strategy": "required",
            },
            {
                "field_name": "energy_cost",
                "semantic_label": "cost",
                "unit": "$/h",
                "dimension": "dimensionless",
                "observable": True,
                "controllable": False,
                "missing_strategy": "required",
            },
            {
                "field_name": "pressure",
                "semantic_label": "pressure",
                "unit": "bar",
                "dimension": "dimensionless",
                "observable": True,
                "controllable": True,
                "missing_strategy": "required",
            },
        ],
        "alias_map": {"p01": "pressure"},
    }


def test_end_to_end_parse_generate_review_publish_simulate_evaluate() -> None:
    parse_resp = client.post(
        "/v1/agentic/parse-points",
        json={"field_dictionary": _field_dictionary(), "legacy_points": ["p01", "unknown_tag"]},
    )
    assert parse_resp.status_code == 200
    parser_result = parse_resp.json()

    draft_resp = client.post(
        "/v1/agentic/generate-draft",
        json={
            "scene_metadata": {
                "scene_id": "e2e-scene",
                "scenario_type": "generic",
                "tags": ["synthetic"],
                "granularity_sec": 60,
                "execution_window_sec": 300,
            },
            "field_dictionary": _field_dictionary(),
            "nl_requirements": ["prefer safety and stable outputs"],
            "parser_result": parser_result,
        },
    )
    assert draft_resp.status_code == 200
    draft = draft_resp.json()

    validate = client.post("/v1/templates/validate", json=draft)
    assert validate.status_code == 200

    quality = client.post("/v1/templates/quality-check", json={"draft": draft})
    assert quality.status_code == 200

    review = client.post(
        "/v1/agentic/review-draft",
        json={
            "failed_draft": draft,
            "validation_report": validate.json(),
            "quality_report": quality.json(),
        },
    )
    assert review.status_code == 200

    run = client.post(
        "/v1/agentic/run",
        json={
            "scene_metadata": {
                "scene_id": "e2e-run",
                "scenario_type": "generic",
                "tags": ["synthetic"],
                "granularity_sec": 60,
                "execution_window_sec": 300,
            },
            "field_dictionary": _field_dictionary(),
            "nl_requirements": ["reduce energy with safety constraints"],
            "legacy_points": ["p01", "temp_a"],
            "max_iterations": 3,
        },
    )
    assert run.status_code == 200
    run_payload = run.json()

    final_draft = run_payload.get("final_draft") or draft

    publish = client.post(
        "/v1/templates/publish",
        json={"draft": final_draft, "validate_before_publish": True, "enforce_quality_gate": False},
    )
    assert publish.status_code == 200
    template_id = publish.json()["template_id"]

    sim = client.post(
        "/v1/pipeline/simulate",
        json={
            "template_id": template_id,
            "scene_context": {
                "values": {"quality_index": 0.8, "energy_cost": 120.0, "pressure": 12.0},
                "metadata": {},
            },
        },
    )
    assert sim.status_code == 200

    eval_resp = client.post(
        "/v1/pipeline/evaluate",
        json={
            "scenario_id": "eval-e2e",
            "template_id": template_id,
            "samples": [
                {
                    "context": {"values": {"quality_index": 0.8, "energy_cost": 120.0, "pressure": 12.0}, "metadata": {}},
                    "expected_approved": True,
                },
                {
                    "context": {"values": {"quality_index": 0.7, "energy_cost": 130.0, "pressure": 14.0}, "metadata": {}},
                    "expected_approved": True,
                },
            ],
        },
    )
    assert eval_resp.status_code == 200
    assert eval_resp.json()["total_runs"] == 2
