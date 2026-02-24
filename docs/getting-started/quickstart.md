# 10分钟上手

本节给出一条最短可跑通链路：
`导入点位 -> 构建上下文 -> 生成草案 -> 校验/质量检查 -> 发布 -> 仿真`

## 1. 启动服务
```bash
uvicorn easyshift_maas.api.app:app --reload --port 8000
```

## 2. 导入标准 YAML 点位配置
```bash
curl -X POST http://127.0.0.1:8000/v1/catalogs/import \
  -H 'Content-Type: application/json' \
  -d '{
    "mode": "standard",
    "yaml_path": "./src/easyshift_maas/examples/data/catalog_standard.yaml"
  }'
```

预期响应（示例）：
```json
{
  "catalog_id": "demo-line-catalog",
  "binding_count": 3,
  "warnings": [],
  "pending_confirmations": []
}
```

## 3. 基于 catalog 构建运行上下文
```bash
curl -X POST http://127.0.0.1:8000/v1/contexts/build \
  -H 'Content-Type: application/json' \
  -d '{
    "catalog_id": "demo-line-catalog",
    "missing_policy": "zero"
  }'
```

预期输出：
- `scene_context.values` 有字段值。
- `snapshot.quality_flags` 标识每个字段读取状态。

## 4. 生成迁移草案
```bash
curl -X POST http://127.0.0.1:8000/v1/templates/generate \
  -H 'Content-Type: application/json' \
  -d @- <<'JSON'
{
  "scene_metadata": {
    "scene_id": "demo-line",
    "scenario_type": "optimization",
    "tags": ["synthetic"],
    "granularity_sec": 60,
    "execution_window_sec": 300
  },
  "field_dictionary": {
    "fields": [
      {"field_name":"energy_cost","semantic_label":"cost","unit":"$/h","dimension":"dimensionless","observable":true,"controllable":false,"missing_strategy":"required"},
      {"field_name":"reactor_temp","semantic_label":"temperature","unit":"C","dimension":"dimensionless","observable":true,"controllable":true,"missing_strategy":"required"},
      {"field_name":"reactor_pressure","semantic_label":"pressure","unit":"bar","dimension":"dimensionless","observable":true,"controllable":true,"missing_strategy":"required"}
    ],
    "alias_map": {}
  },
  "nl_requirements": ["prioritize safety and stability"]
}
JSON
```

## 5. 校验与质量检查
- `POST /v1/templates/validate`
- `POST /v1/templates/quality-check`

质量检查通过标准可在请求里调节（`TemplateQualityGate`）。

## 6. 发布模板
调用 `POST /v1/templates/publish`，默认会同时检查：
- 草案校验（validator）
- 质量门禁（quality gate）

## 7. 仿真
调用 `POST /v1/pipeline/simulate`，你会得到：
- 预测结果
- 优化建议值
- 安全规则判定结果（通过/拦截/裁剪）
- 最终输出建议值

如果你只想快速感受执行链，可先用 `inline_template` 直接仿真。
