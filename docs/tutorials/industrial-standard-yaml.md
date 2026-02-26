# 标准 YAML 工业流程

本教程展示从 YAML 到迁移草案发布的完整链路。

## 1. 准备标准 YAML
示例：

```yaml
scene:
  scene_id: line-a
  scenario_type: optimization
  tags: [synthetic]
  granularity_sec: 60
  execution_window_sec: 300

datasources:
  redis_main:
    kind: redis
    conn_ref: env:EASYSHIFT_REDIS_CONN
    options:
      batch_size: 500
      timeout_ms: 500
      tls: false

point_catalog:
  catalog_id: line-a-catalog
  version: v1
  source_profile: redis_main
  bindings:
    - point_id: P_TEMP_01
      source_type: redis
      source_ref: line:a:temp:01
      field_name: boiler_temp
      unit: C
    - point_id: P_COST_01
      source_type: redis
      source_ref: line:a:cost:01
      field_name: energy_cost
      unit: $/h

field_dictionary:
  fields:
    - field_name: boiler_temp
      semantic_label: temperature
      unit: C
      controllable: true
      observable: true
      missing_strategy: required
    - field_name: energy_cost
      semantic_label: cost
      unit: $/h
      controllable: false
      observable: true
      missing_strategy: required
  alias_map:
    B_T_01: boiler_temp
```

## 2. 导入 catalog
```bash
curl -X POST http://127.0.0.1:8000/v1/catalogs/import \
  -H 'content-type: application/json' \
  -d '{"mode":"standard", "yaml_path":"/path/to/catalog.yaml"}'
```

## 3. 构建场景上下文
```bash
curl -X POST http://127.0.0.1:8000/v1/contexts/build \
  -H 'content-type: application/json' \
  -d '{"catalog_id":"line-a-catalog", "missing_policy":"zero"}'
```

## 4. 运行多 Agent 迁移链路
```bash
curl -X POST http://127.0.0.1:8000/v1/agentic/run \
  -H 'content-type: application/json' \
  -d '{
    "scene_metadata": {"scene_id":"line-a", "scenario_type":"optimization", "tags":["synthetic"], "granularity_sec":60, "execution_window_sec":300},
    "field_dictionary": {
      "fields": [
        {"field_name":"boiler_temp", "semantic_label":"temperature", "unit":"C", "controllable":true, "observable":true, "missing_strategy":"required"},
        {"field_name":"energy_cost", "semantic_label":"cost", "unit":"$/h", "controllable":false, "observable":true, "missing_strategy":"required"}
      ],
      "alias_map": {"B_T_01": "boiler_temp"}
    },
    "nl_requirements": ["minimize energy cost and keep temperature above 180"],
    "legacy_points": ["B_T_01", "P_COST_01"],
    "max_iterations": 3
  }'
```

## 5. 发布通过门禁的草案
```bash
curl -X POST http://127.0.0.1:8000/v1/templates/publish \
  -H 'content-type: application/json' \
  -d '{"draft": {...}, "validate_before_publish": true, "enforce_quality_gate": true}'
```

## 6. 仿真评估
```bash
curl -X POST http://127.0.0.1:8000/v1/pipeline/simulate \
  -H 'content-type: application/json' \
  -d '{"template_id":"line-a-template", "scene_context":{"values":{"boiler_temp":520,"energy_cost":120},"metadata":{}}}'
```

## 7. 失败时怎么调
1. 先看 `AgenticRunReport.reflections`。
2. 按 `correction_instruction` 修改字段字典或约束描述。
3. 如果映射置信度低，补充 `alias_map` 再运行。
4. 如果质量分低，先修约束冲突和安全规则覆盖。
