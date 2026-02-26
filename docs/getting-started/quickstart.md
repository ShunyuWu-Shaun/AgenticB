# 10分钟上手

目标：跑通 `parse -> run -> publish -> simulate`。

## 1. 启动服务
```bash
uvicorn easyshift_maas.api.app:app --reload --port 8000
```

## 2. 解析 legacy 点位
```bash
curl -X POST http://127.0.0.1:8000/v1/agentic/parse-points \
  -H 'Content-Type: application/json' \
  -d '{
    "field_dictionary": {
      "fields": [
        {"field_name":"energy_cost","semantic_label":"cost","unit":"$/h","dimension":"dimensionless","observable":true,"controllable":false,"missing_strategy":"required"},
        {"field_name":"boiler_temp","semantic_label":"temperature","unit":"C","dimension":"dimensionless","observable":true,"controllable":true,"missing_strategy":"required"}
      ],
      "alias_map": {"B_T_01": "boiler_temp"}
    },
    "legacy_points": ["B_T_01", "E_COST_01"]
  }'
```

## 3. 运行完整自动修正流程
```bash
curl -X POST http://127.0.0.1:8000/v1/agentic/run \
  -H 'Content-Type: application/json' \
  -d '{
    "scene_metadata": {"scene_id":"demo-line","scenario_type":"optimization","tags":["synthetic"],"granularity_sec":60,"execution_window_sec":300},
    "field_dictionary": {
      "fields": [
        {"field_name":"energy_cost","semantic_label":"cost","unit":"$/h","dimension":"dimensionless","observable":true,"controllable":false,"missing_strategy":"required"},
        {"field_name":"boiler_temp","semantic_label":"temperature","unit":"C","dimension":"dimensionless","observable":true,"controllable":true,"missing_strategy":"required"}
      ],
      "alias_map": {"B_T_01": "boiler_temp"}
    },
    "nl_requirements": ["minimize energy cost and keep temperature above 180"],
    "legacy_points": ["B_T_01", "E_COST_01"],
    "max_iterations": 3
  }'
```

预期响应包含：
- `status`: `approved` 或 `blocked`
- `reflections`: 每轮失败原因和修正建议
- `final_draft`: 当前最优草案

## 4. 发布模板
```bash
curl -X POST http://127.0.0.1:8000/v1/templates/publish \
  -H 'Content-Type: application/json' \
  -d '{"draft": {...}, "validate_before_publish": true, "enforce_quality_gate": true}'
```

## 5. 仿真
```bash
curl -X POST http://127.0.0.1:8000/v1/pipeline/simulate \
  -H 'Content-Type: application/json' \
  -d '{
    "template_id": "demo-line-template",
    "scene_context": {"values": {"energy_cost": 120, "boiler_temp": 520}, "metadata": {}}
  }'
```

## 6. 排查
1. `status=blocked`：查看 `reflections[].critic_feedback.correction_instruction`。
2. `quality-check` 不通过：优先修约束冲突和安全规则覆盖。
3. 点位映射错误：补 `alias_map` 或输入更多 legacy 点位样例。
