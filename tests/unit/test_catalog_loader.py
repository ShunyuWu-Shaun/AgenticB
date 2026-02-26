from easyshift_maas.core.contracts import CatalogLoadMode
from easyshift_maas.ingestion.catalog_loader import YamlCatalogLoader


def test_standard_yaml_catalog_load() -> None:
    yaml_text = """
scene:
  scene_id: demo-line
  scenario_type: optimization
datasources:
  redis_main:
    kind: redis
    conn_ref: env:REFLEXFLOW_REDIS_CONN
    options:
      batch_size: 200
      timeout_ms: 300
      tls: false
point_catalog:
  catalog_id: demo-line-catalog
  version: v2
  refresh_sec: 10
  source_profile: redis_main
  bindings:
    - point_id: P_TEMP_01
      source_type: redis
      source_ref: redis:temp:01
      field_name: reactor_temp
      unit: C
    - point_id: P_FLOW_01
      source_type: redis
      source_ref: redis:flow:01
      field_name: steam_flow
      unit: t/h
"""
    result = YamlCatalogLoader().load(yaml_text=yaml_text, mode=CatalogLoadMode.STANDARD)

    assert result.catalog.catalog_id == "demo-line-catalog"
    assert len(result.catalog.bindings) == 2
    assert len(result.source_profiles) == 1
    assert result.source_profiles[0].name == "redis_main"
    assert result.field_dictionary.has_field("reactor_temp")


def test_legacy_yaml_catalog_load() -> None:
    yaml_text = """
redis_config:
  host: 127.0.0.1
  port: 6379
AB10PT101: AB10PT101
AB10FT201: AB10FT201
threshold: 0.8
"""
    result = YamlCatalogLoader().load(yaml_text=yaml_text, mode=CatalogLoadMode.LEGACY)

    assert result.catalog.version == "legacy-v1"
    assert len(result.catalog.bindings) == 2
    assert result.source_profiles[0].kind.value == "redis"
    assert result.pending_confirmations


def test_legacy_nested_sections_with_duplicate_tags() -> None:
    yaml_text = """
inputs:
  specific_heat_of_slag: AMICS_BALAR1500
  coal_net_calorific_value: AMICS_BALAR1503
real_time_inputs:
  air_preheater_outlet_oxygen_content_A1: RAA10BQ101
  air_preheater_outlet_oxygen_content_A2: RAA10BQ101
  airheater_outlet_temp_A1: RAA10BT301
"""
    result = YamlCatalogLoader().load(yaml_text=yaml_text, mode=CatalogLoadMode.LEGACY)

    assert len(result.catalog.bindings) >= 5
    assert len({item.point_id for item in result.catalog.bindings}) == len(result.catalog.bindings)
    assert len([item for item in result.catalog.bindings if item.source_ref == "RAA10BQ101"]) == 2
    assert result.field_dictionary.has_field("air_preheater_outlet_oxygen_content_a1")
