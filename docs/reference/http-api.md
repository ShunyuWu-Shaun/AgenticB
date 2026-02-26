# HTTP API 参考

Base URL: `http://127.0.0.1:8000`

## 1. Agentic API
### `POST /v1/agentic/parse-points`
用途：将 legacy 点位映射到标准字段。

请求示例：
```json
{
  "field_dictionary": {
    "fields": [
      {"field_name": "boiler_temp", "semantic_label": "temperature", "unit": "C", "dimension": "dimensionless", "observable": true, "controllable": true, "missing_strategy": "required"}
    ],
    "alias_map": {"B_T_01": "boiler_temp"}
  },
  "legacy_points": ["B_T_01", "RAA10BQ101"]
}
```

响应：`ParserResult`

### `POST /v1/agentic/generate-draft`
用途：根据场景信息、字段字典和自然语言诉求生成草案。

请求关键字段：
1. `scene_metadata`
2. `field_dictionary`
3. `nl_requirements`
4. `parser_result` 可选

响应：`MigrationDraft`

### `POST /v1/agentic/review-draft`
用途：对失败草案进行审计并产出修正指令。

请求关键字段：
1. `failed_draft`
2. `validation_report`
3. `quality_report`

响应：`CriticFeedback`

### `POST /v1/agentic/run`
用途：运行完整自动修正流程。

请求关键字段：
1. `scene_metadata`
2. `field_dictionary`
3. `nl_requirements`
4. `legacy_points` 或 `raw_yaml_text` 可选
5. `max_iterations` 默认 3
6. `gate` 可选
7. `regression_samples` 可选
8. `publish_on_pass` 可选

响应：`AgenticRunReport`

## 2. Template API
### `POST /v1/templates/validate`
输入：`MigrationDraft`

输出：`MigrationValidationReport`

### `POST /v1/templates/quality-check`
输入：`draft` 或 `template`

输出：`TemplateQualityReport`

### `POST /v1/templates/publish`
输入：`draft` 与门禁参数

输出：`TemplatePublishResponse`

### `GET /v1/templates/{template_id}`
用途：按模板 ID 和可选版本查询。

## 3. Catalog API
### `POST /v1/catalogs/import`
输入：
1. `mode`: `standard` 或 `legacy`
2. `yaml_text` 或 `yaml_path`
3. `source_profiles` 可选

输出：`catalog_id`, `binding_count`, `warnings`, `pending_confirmations`

### `GET /v1/catalogs/{catalog_id}`
输出：`PointCatalog`

### `POST /v1/contexts/build`
输入：`catalog_id`, `missing_policy`, `scene_metadata` 可选

输出：`ContextBuildResult`

## 4. Pipeline API
### `POST /v1/pipeline/simulate`
输入：`scene_context` + (`template_id` 或 `inline_template`)

输出：`PipelineResult`

### `POST /v1/pipeline/evaluate`
输入：`samples` + (`template_id` 或 `inline_template`)

输出：`EvaluationReport`

## 5. Health API
### `GET /health`
返回版本、组件状态、模板数量、catalog 数量。

## 6. 错误码
- `400`: 业务校验失败，例如质量分数未达阈值。
- `404`: 资源不存在。
- `422`: 请求体格式错误。
