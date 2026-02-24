# HTTP API 参考

Base URL: `http://127.0.0.1:8000`

## Catalog 与 Context
### `POST /v1/catalogs/import`
- 作用：导入点位 YAML。
- 入参：
  - `mode`: `standard|legacy`
  - `yaml_text` 或 `yaml_path`（二选一）
  - `source_profiles`（可选）
- 出参：`catalog_id`, `binding_count`, `warnings`, `pending_confirmations`

### `GET /v1/catalogs/{catalog_id}`
- 作用：查询 catalog 详情。
- 出参：`PointCatalog`

### `POST /v1/contexts/build`
- 作用：从数据源读取快照并构建 `SceneContext`。
- 入参：`catalog_id`, `fields?`, `at?`, `missing_policy`, `scene_metadata?`
- 出参：`ContextBuildResult`

## 模板迁移与发布
### `POST /v1/templates/generate`
- 作用：生成迁移草案。
- 入参：`scene_metadata`, `field_dictionary`, `nl_requirements`
- 出参：`MigrationDraft`

### `POST /v1/templates/validate`
- 作用：校验草案一致性。
- 入参：`MigrationDraft`
- 出参：`MigrationValidationReport`

### `POST /v1/templates/quality-check`
- 作用：质量门禁评估。
- 入参：`draft` 或 `template`（二选一）, `gate?`, `regression_samples?`
- 出参：`TemplateQualityReport`

### `POST /v1/templates/publish`
- 作用：发布模板版本。
- 入参：
  - `draft`
  - `validate_before_publish`
  - `enforce_quality_gate`
  - `quality_gate`
  - `regression_samples`
- 出参：`template_id`, `version`, `validation`, `quality`

### `GET /v1/templates/{template_id}`
- 作用：按模板 ID/版本查询。
- 出参：`ScenarioTemplate`

### `GET /v1/templates/base`
- 作用：获取官方基线模板列表与 schema。

## 仿真与评估
### `POST /v1/pipeline/simulate`
- 入参：`scene_context` + (`template_id` xor `inline_template`)
- 出参：`PipelineResult`

### `POST /v1/pipeline/evaluate`
- 入参：`scenario_id`, `samples` + (`template_id` xor `inline_template`)
- 出参：`EvaluationReport`

## 健康检查
### `GET /health`
- 返回组件状态和计数。

## 错误语义
- `400`: 业务校验失败（例如质量门禁不通过、快照缺失）。
- `404`: catalog/template 不存在。
- `422`: 请求体字段或类型错误。
