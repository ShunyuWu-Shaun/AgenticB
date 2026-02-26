from fastapi.testclient import TestClient

from easyshift_maas.api.app import app


client = TestClient(app)


def test_catalog_import_get_and_context_build_contract() -> None:
    yaml_text = """
scene:
  scene_id: api-line
datasources:
  redis_main:
    kind: redis
    conn_ref: env:EASYSHIFT_REDIS_CONN
point_catalog:
  catalog_id: api-line-catalog
  source_profile: redis_main
  bindings:
    - point_id: P_TEMP_01
      source_type: redis
      source_ref: plant:temp:01
      field_name: reactor_temp
      unit: C
    - point_id: P_FLOW_01
      source_type: redis
      source_ref: plant:flow:01
      field_name: steam_flow
      unit: t/h
"""
    import_resp = client.post(
        "/v1/catalogs/import",
        json={"mode": "standard", "yaml_text": yaml_text},
    )
    assert import_resp.status_code == 200
    payload = import_resp.json()
    assert payload["catalog_id"] == "api-line-catalog"
    assert payload["binding_count"] == 2

    get_resp = client.get("/v1/catalogs/api-line-catalog")
    assert get_resp.status_code == 200

    context_resp = client.post(
        "/v1/contexts/build",
        json={
            "catalog_id": "api-line-catalog",
            "missing_policy": "zero",
            "scene_metadata": {
                "scene_id": "api-line",
                "scenario_type": "generic",
                "tags": ["synthetic"],
                "granularity_sec": 60,
                "execution_window_sec": 300,
            },
        },
    )
    assert context_resp.status_code == 200
    context_payload = context_resp.json()
    assert "scene_context" in context_payload
    assert "snapshot" in context_payload


def test_quality_check_contract() -> None:
    draft = client.post(
        "/v1/agentic/generate-draft",
        json={
            "scene_metadata": {
                "scene_id": "quality-api",
                "scenario_type": "generic",
                "tags": ["synthetic"],
                "granularity_sec": 60,
                "execution_window_sec": 300,
            },
            "field_dictionary": {
                "fields": [
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
            "nl_requirements": ["prefer safety"],
        },
    ).json()

    quality_resp = client.post(
        "/v1/templates/quality-check",
        json={"draft": draft},
    )
    assert quality_resp.status_code == 200
    quality = quality_resp.json()
    assert set(["overall_score", "passed", "semantic_score", "solvability_score"]).issubset(quality.keys())
