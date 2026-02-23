# EasyShift-MaaS Architecture

## Four-Layer Runtime
1. Core Layer: contracts, predictor, optimizer, guardrail, pipeline.
2. Template Layer: schema + versioned template repository.
3. Agentic Layer: migration assistant, validator, regression planner.
4. Service Layer: FastAPI endpoints for generation, validation, publish, simulation, evaluation.

## Migration-Centric Agentic Design
- Agentic module does not directly execute closed-loop control.
- Agentic module focuses on portability tasks:
  - semantic field mapping hints
  - constraint/objective draft generation
  - migration risk and pending confirmations
  - regression case planning

## Safety And Correctness
- Drafts are validated before publish.
- Validation outputs correctness score, conflict rate, guardrail coverage.
- Publish can be blocked when validation fails.
