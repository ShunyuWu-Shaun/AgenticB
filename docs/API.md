# API Overview (v0.2)

Base URL: `http://<host>:8000`

## Catalog & Context
- `POST /v1/catalogs/import`
  - Input: `mode`, `yaml_text|yaml_path`, optional `source_profiles`
  - Output: `catalog_id`, `binding_count`, `warnings`, `pending_confirmations`
- `GET /v1/catalogs/{catalog_id}`
  - Output: `PointCatalog`
- `POST /v1/contexts/build`
  - Input: `catalog_id`, optional `fields`, `missing_policy`, optional `scene_metadata`
  - Output: `ContextBuildResult(scene_context + snapshot)`

## Template Migration
- `POST /v1/templates/generate`
  - Input: `scene_metadata`, `field_dictionary`, `nl_requirements`
  - Output: `MigrationDraft`
- `POST /v1/templates/validate`
  - Input: `MigrationDraft`
  - Output: `MigrationValidationReport`
- `POST /v1/templates/quality-check`
  - Input: `draft|template` (exactly one), optional `gate`, optional `regression_samples`
  - Output: `TemplateQualityReport`
- `POST /v1/templates/publish`
  - Input: `draft`, `validate_before_publish`, `enforce_quality_gate`, `quality_gate`, `regression_samples`
  - Output: `template_id`, `version`, `validation`, `quality`
- `GET /v1/templates/{template_id}`
  - Output: `ScenarioTemplate`
- `GET /v1/templates/base`
  - Output: `templates` (official baseline templates), `template_schema`

## Pipeline
- `POST /v1/pipeline/simulate`
  - Input: `scene_context` + (`template_id` xor `inline_template`)
  - Output: `PipelineResult`
- `POST /v1/pipeline/evaluate`
  - Input: `scenario_id`, `samples` + (`template_id` xor `inline_template`)
  - Output: `EvaluationReport`

## Health
- `GET /health`
  - Output: status + template/catalog/data source counts.

## Error Behavior
- Validation errors: `422` (request schema mismatch)
- Business validation block: `400`
- Not found: `404`

## Notes
- `/v1/contexts/build` with `missing_policy=error` blocks when any required field is missing.
- `/v1/templates/publish` applies both validation and quality gate by default.
- Catalog import supports `standard` and `legacy` YAML modes.
