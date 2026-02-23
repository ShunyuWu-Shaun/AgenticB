# Migration Guide: agentic-maas -> EasyShift-MaaS

This release uses a destructive switch in API and package naming.

## Breaking Changes
- Package import path changed from `agentic_maas` to `easyshift_maas`.
- API surface moved from migration/deployment oriented endpoints to template/pipeline endpoints.
- Core contracts were redesigned for reusable prediction-optimization patterns.

## New Entry Points
- API: `easyshift_maas.api.app:app`
- CLI: `easyshift-maas`

## Data Model Shift
Legacy task-centric models were replaced with:
- `SceneMetadata`
- `FieldDictionary`
- `ScenarioTemplate`
- `MigrationDraft`
- `MigrationValidationReport`
