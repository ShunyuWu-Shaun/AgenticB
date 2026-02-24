# EasyShift-MaaS Architecture (v0.2)

## Runtime Layers
1. Core Layer
   - `contracts.py`
   - `predictor.py`
   - `optimizer.py`
   - `guardrail.py`
   - `pipeline.py`
2. Ingestion Layer
   - YAML loader (`standard|legacy`)
   - Catalog repository
   - Redis/MySQL snapshot providers
   - context builder (`PointCatalog -> SceneContext`)
3. Agentic + Quality Layer
   - migration assistant
   - template validator
   - template quality evaluator
   - regression planner
4. Service Layer
   - FastAPI endpoints
   - template/catalog repos
   - health and observability

## Key Contracts
- `PointBinding`, `PointCatalog`, `DataSourceProfile`
- `SnapshotRequest`, `SnapshotResult`
- `ScenarioTemplate`, `MigrationDraft`, `MigrationValidationReport`
- `TemplateQualityGate`, `TemplateQualityReport`

## Why Template-Centric
- Template is a versioned migration contract.
- Agentic output becomes auditable and replayable.
- Objective/constraint/guardrail logic is no longer scattered in scripts.

## Correctness & Gate
Quality gate dimensions:
1. structural
2. semantic
3. solvability
4. guardrail coverage
5. regression score

Default publish policy: validation pass + quality pass.

## Deployment Model
- Local/dev: Docker Compose (`easyshift-api + redis + mysql + secrets`)
- Production baseline: Helm chart + secretKeyRef
- Binary distribution: Nuitka (`scripts/build_nuitka.sh`)
