from fastapi.testclient import TestClient

from easyshift_maas.api.app import app


client = TestClient(app)


def _generate_payload() -> dict:
    return {
        "scene_metadata": {
            "scene_id": "api-scene",
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
        "nl_requirements": ["prioritize safe stability"],
    }


def test_generate_validate_contract_shape() -> None:
    draft_resp = client.post("/v1/templates/generate", json=_generate_payload())
    assert draft_resp.status_code == 200
    draft = draft_resp.json()

    assert "draft_id" in draft
    assert "template" in draft
    assert "confidence" in draft

    report_resp = client.post("/v1/templates/validate", json=draft)
    assert report_resp.status_code == 200
    report = report_resp.json()

    assert set(["valid", "correctness_score", "conflict_rate", "guardrail_coverage"]).issubset(report.keys())
