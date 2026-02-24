# Migration Guide: v0.1 -> v0.2

## Summary
v0.2 introduces industrial YAML indexing, data source adapters, and quality gate enforcement.

## Breaking/Behavior Changes
1. `POST /v1/templates/publish` now enforces quality gate by default (`enforce_quality_gate=true`).
2. `TemplatePublishResponse` now contains `quality` section.
3. New catalog/context APIs are the recommended way to build `SceneContext` from point configuration.

## New APIs
- `POST /v1/catalogs/import`
- `GET /v1/catalogs/{catalog_id}`
- `POST /v1/contexts/build`
- `POST /v1/templates/quality-check`
- `GET /v1/templates/base`

## Data Model Additions
- `PointBinding`, `PointCatalog`, `DataSourceProfile`
- `SnapshotRequest`, `SnapshotResult`
- `TemplateQualityGate`, `TemplateQualityReport`

## YAML Modes
- `standard`: explicit scene + datasources + point_catalog + field_dictionary
- `legacy`: point-heavy legacy map with heuristic conversion and pending confirmations

## Security/Deployment Additions
- Docker multi-stage image and compose stack with secrets
- Helm values for secretKeyRef mapping
- Nuitka build script for CLI/API binaries

## Recommended Upgrade Steps
1. Move existing point map into `standard` YAML where possible.
2. Define `conn_ref` via `env:` or `file:` secrets.
3. Add regression sample set and validate `quality-check` before publish.
4. Keep `legacy` mode only for transition period.
