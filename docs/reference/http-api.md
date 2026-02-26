# HTTP API 参考

Base URL: `http://127.0.0.1:8000`

## Agentic API
### `POST /v1/agentic/parse-points`
作用：legacy 点位语义映射。

请求关键字段：
- `field_dictionary`
- `legacy_points` 或 `raw_yaml_text`

响应：`ParserResult`

### `POST /v1/agentic/generate-draft`
作用：生成迁移草案。

请求关键字段：
- `scene_metadata`
- `field_dictionary`
- `nl_requirements`
- `parser_result` 可选

响应：`MigrationDraft`

### `POST /v1/agentic/review-draft`
作用：对失败草案给出修正指令。

请求关键字段：
- `failed_draft`
- `validation_report`
- `quality_report`

响应：`CriticFeedback`

### `POST /v1/agentic/run`
作用：运行完整自动修正流程。

请求关键字段：
- `scene_metadata`
- `field_dictionary`
- `nl_requirements`
- `max_iterations`
- `gate` 可选
- `regression_samples` 可选

响应：`AgenticRunReport`

## Template API
### `POST /v1/templates/validate`
输入：`MigrationDraft`
输出：`MigrationValidationReport`

### `POST /v1/templates/quality-check`
输入：`draft` 或 `template`
输出：`TemplateQualityReport`

### `POST /v1/templates/publish`
输入：`draft` + 发布门禁参数
输出：`TemplatePublishResponse`

### `GET /v1/templates/{template_id}`
作用：按 `template_id` 和可选 `version` 查询模板。

## Pipeline API
### `POST /v1/pipeline/simulate`
输入：`scene_context` + (`template_id` 或 `inline_template`)
输出：`PipelineResult`

### `POST /v1/pipeline/evaluate`
输入：`samples` + (`template_id` 或 `inline_template`)
输出：`EvaluationReport`

## Catalog API
### `POST /v1/catalogs/import`
输入：`mode`, `yaml_text` 或 `yaml_path`
输出：`catalog_id`, `binding_count`, `warnings`

### `GET /v1/catalogs/{catalog_id}`
输出：`PointCatalog`

### `POST /v1/contexts/build`
输入：`catalog_id`, `missing_policy`
输出：`ContextBuildResult`

## Health
### `GET /health`
返回版本、组件状态、模板数量、catalog 数量。

## 错误码
- `400`: 业务校验失败，例如质量门禁未通过。
- `404`: 资源不存在。
- `422`: 请求体格式错误。
