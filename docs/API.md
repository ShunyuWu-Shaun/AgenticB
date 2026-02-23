# API Overview

## Endpoints
- POST `/v1/templates/generate`
- POST `/v1/templates/validate`
- POST `/v1/templates/publish`
- GET `/v1/templates/{template_id}`
- POST `/v1/pipeline/simulate`
- POST `/v1/pipeline/evaluate`
- GET `/health`

## Notes
- Simulation/evaluation requests accept either `template_id` or `inline_template`.
- Publishing with `validate_before_publish=true` will reject invalid drafts.
