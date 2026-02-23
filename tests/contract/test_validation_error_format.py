from fastapi.testclient import TestClient

from easyshift_maas.api.app import app


client = TestClient(app)


def test_publish_error_contains_structured_report() -> None:
    draft_resp = client.post(
        "/v1/templates/generate",
        json={
            "scene_metadata": {
                "scene_id": "err-scene",
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
    )
    draft = draft_resp.json()

    # Deliberately create objective/guardrail mismatch to fail strict validator.
    draft["template"]["guardrail"]["rules"] = []

    publish_resp = client.post(
        "/v1/templates/publish",
        json={"draft": draft, "validate_before_publish": True},
    )
    assert publish_resp.status_code == 400
    body = publish_resp.json()
    assert "detail" in body
