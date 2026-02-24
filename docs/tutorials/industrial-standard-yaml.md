# 教程：标准 YAML 工业流程

目标：从标准 YAML 走完整链路：
`import -> context build -> draft -> validate -> quality -> publish -> simulate`

## 步骤 1：准备 YAML
使用示例：`src/easyshift_maas/examples/data/catalog_standard.yaml`

关键块：
- `datasources`: Redis/MySQL 连接引用。
- `point_catalog.bindings`: 点位到字段映射。
- `field_dictionary`: 字段语义。

## 步骤 2：导入 catalog
```bash
curl -X POST http://127.0.0.1:8000/v1/catalogs/import \
  -H 'Content-Type: application/json' \
  -d '{"mode":"standard","yaml_path":"./src/easyshift_maas/examples/data/catalog_standard.yaml"}'
```

## 步骤 3：构建上下文
```bash
curl -X POST http://127.0.0.1:8000/v1/contexts/build \
  -H 'Content-Type: application/json' \
  -d '{"catalog_id":"demo-line-catalog","missing_policy":"error"}'
```

如果现场偶发缺失值，可先用 `missing_policy=zero` 观察链路。

## 步骤 4：生成草案
调用 `POST /v1/templates/generate`，输入：
- `scene_metadata`
- `field_dictionary`
- `nl_requirements`

## 步骤 5：校验与质量评估
- `POST /v1/templates/validate`
- `POST /v1/templates/quality-check`

若 `passed=false`，优先处理 `issues` 里的 ERROR。

## 步骤 6：发布
```bash
curl -X POST http://127.0.0.1:8000/v1/templates/publish \
  -H 'Content-Type: application/json' \
  -d '{"draft": {"...": "..."}, "validate_before_publish": true, "enforce_quality_gate": true}'
```

## 步骤 7：仿真
`POST /v1/pipeline/simulate`

关注四块输出：
- `prediction`
- `plan.recommended_setpoints`
- `guardrail`（安全规则判定结果）
- `final_setpoints`

## 常见问题
- 发布失败：通常是字段不一致或质量评分低。
- 仿真被拦截：通常是安全规则阈值过严或约束设置冲突。
