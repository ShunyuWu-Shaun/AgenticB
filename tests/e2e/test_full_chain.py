from fastapi.testclient import TestClient

from easyshift_maas.api.app import app


client = TestClient(app)


def _generation_request(scene_id: str) -> dict:
    return {
        "scene_metadata": {
            "scene_id": scene_id,
            "scenario_type": "generic",
            "tags": ["synthetic"],
            "granularity_sec": 60,
            "execution_window_sec": 300,
        },
        "field_dictionary": {
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
            "alias_map": {},
        },
        "nl_requirements": ["prefer safety and stable outputs"],
    }


def test_end_to_end_generate_validate_publish_simulate_evaluate() -> None:
    draft = client.post("/v1/templates/generate", json=_generation_request("e2e-scene")).json()
    report = client.post("/v1/templates/validate", json=draft).json()
    assert report["valid"] is True

    published = client.post(
        "/v1/templates/publish",
        json={"draft": draft, "validate_before_publish": True},
    )
    assert published.status_code == 200
    template_id = published.json()["template_id"]

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


def test_low_confidence_path_visible_in_draft() -> None:
    draft = client.post(
        "/v1/templates/generate",
        json={
            "scene_metadata": {
                "scene_id": "low-conf",
                "scenario_type": "generic",
                "tags": [],
                "granularity_sec": 60,
                "execution_window_sec": 300,
            },
            "field_dictionary": {
                "fields": [
                    {
                        "field_name": "x",
                        "semantic_label": "proxy",
                        "unit": "u",
                        "dimension": "dimensionless",
                        "observable": True,
                        "controllable": False,
                        "missing_strategy": "required",
                    }
                ],
                "alias_map": {},
            },
            "nl_requirements": [],
        },
    ).json()

    assert draft["generation_strategy"] == "rule_only_low_confidence"


def test_conflict_draft_is_blocked_from_publish() -> None:
    draft = client.post("/v1/templates/generate", json=_generation_request("conflict-scene")).json()
    draft["template"]["constraints"] = [
        {
            "name": "pressure_min",
            "field_name": "pressure",
            "operator": "ge",
            "lower_bound": 20,
            "upper_bound": None,
            "equals_value": None,
            "priority": 1,
            "severity": "hard",
        },
        {
            "name": "pressure_max",
            "field_name": "pressure",
            "operator": "le",
            "lower_bound": None,
            "upper_bound": 10,
            "equals_value": None,
            "priority": 1,
            "severity": "hard",
        }
    ]

    response = client.post(
        "/v1/templates/publish",
        json={"draft": draft, "validate_before_publish": True},
    )
    assert response.status_code == 400
