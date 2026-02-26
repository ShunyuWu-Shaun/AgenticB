from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class ParserMappingOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    legacy_name: str
    standard_name: str
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str


class ParserAgentOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mappings: list[ParserMappingOutput] = Field(default_factory=list)
    unmapped_points: list[str] = Field(default_factory=list)


class GeneratorObjectiveTermOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    field_name: str
    direction: Literal["min", "max"]
    weight: float = Field(gt=0)


class GeneratorObjectiveOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    terms: list[GeneratorObjectiveTermOutput] = Field(min_length=1)


class GeneratorConstraintOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    field_name: str
    operator: Literal[">=", "<=", "==", "between"]
    value: Optional[float] = None
    lower: Optional[float] = None
    upper: Optional[float] = None


class GeneratorGuardrailRuleOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    field_name: str
    max_delta: Optional[float] = Field(default=None, ge=0)
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    action: Literal["clip", "warn", "reject"] = "clip"


class GeneratorGuardrailOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rules: list[GeneratorGuardrailRuleOutput] = Field(default_factory=list)


class GeneratorPredictionOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    feature_fields: list[str] = Field(default_factory=list)
    horizon_steps: int = Field(default=1, ge=1)


class GeneratorAgentOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    objective: GeneratorObjectiveOutput
    constraints: list[GeneratorConstraintOutput] = Field(default_factory=list)
    guardrail: GeneratorGuardrailOutput
    prediction: Optional[GeneratorPredictionOutput] = None
    notes: Optional[str] = None


class CriticAgentOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    is_fatal_error: bool
    analysis: str
    correction_instruction: str


def parser_output_schema() -> dict:
    return ParserAgentOutput.model_json_schema()


def generator_output_schema() -> dict:
    return GeneratorAgentOutput.model_json_schema()


def critic_output_schema() -> dict:
    return CriticAgentOutput.model_json_schema()
