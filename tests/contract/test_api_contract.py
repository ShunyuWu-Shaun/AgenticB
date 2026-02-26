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
        "alias_map": {"p_01": "pressure"},
    }


def test_agentic_parse_generate_validate_contract_shape() -> None:
    parse_resp = client.post(
        "/v1/agentic/parse-points",
        json={
            "field_dictionary": _field_dictionary(),
            "legacy_points": ["p_01", "unknown_tag"],
        },
    )
    assert parse_resp.status_code == 200
    parse_payload = parse_resp.json()
    assert "mappings" in parse_payload
    assert "confidence" in parse_payload

    draft_resp = client.post(
        "/v1/agentic/generate-draft",
        json={
            "scene_metadata": {
                "scene_id": "api-scene",
                "scenario_type": "generic",
                "tags": ["synthetic"],
                "granularity_sec": 60,
                "execution_window_sec": 300,
            },
            "field_dictionary": _field_dictionary(),
            "nl_requirements": ["prioritize safe stability"],
            "parser_result": parse_payload,
        },
    )
    assert draft_resp.status_code == 200
    draft = draft_resp.json()

    assert "draft_id" in draft
    assert "template" in draft
    assert "trace" in draft

    report_resp = client.post("/v1/templates/validate", json=draft)
    assert report_resp.status_code == 200
    report = report_resp.json()

    assert set(["valid", "correctness_score", "conflict_rate", "guardrail_coverage"]).issubset(report.keys())


def test_agentic_run_contract_shape() -> None:
    run_resp = client.post(
        "/v1/agentic/run",
        json={
            "scene_metadata": {
                "scene_id": "run-scene",
                "scenario_type": "generic",
                "tags": [],
                "granularity_sec": 60,
                "execution_window_sec": 300,
            },
            "field_dictionary": _field_dictionary(),
            "nl_requirements": ["reduce energy usage"],
            "legacy_points": ["pressure_sensor_1"],
            "max_iterations": 2,
        },
    )
    assert run_resp.status_code == 200
    payload = run_resp.json()
    assert set(["run_id", "status", "iterations_used", "reflections"]).issubset(payload.keys())
