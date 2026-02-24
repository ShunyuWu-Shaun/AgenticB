from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict

from easyshift_maas.core.contracts import ScenarioTemplate
from easyshift_maas.examples.synthetic_templates import (
    build_energy_efficiency_template,
    build_quality_stability_template,
)


class BaseTemplateInfo(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    template_id: str
    version: str
    description: str


def list_base_templates() -> list[BaseTemplateInfo]:
    energy = build_energy_efficiency_template()
    quality = build_quality_stability_template()
    return [
        BaseTemplateInfo(
            name="energy_efficiency",
            template_id=energy.template_id,
            version=energy.version,
            description="Baseline template for energy-cost minimization with efficiency tradeoff.",
        ),
        BaseTemplateInfo(
            name="quality_stability",
            template_id=quality.template_id,
            version=quality.version,
            description="Baseline template for quality/rework optimization with stability guardrails.",
        ),
    ]


def get_base_template(name: str) -> ScenarioTemplate:
    if name == "energy_efficiency":
        return build_energy_efficiency_template()
    if name == "quality_stability":
        return build_quality_stability_template()
    raise KeyError(f"unknown base template: {name}")


def apply_template_override(template: ScenarioTemplate, override: dict[str, Any]) -> ScenarioTemplate:
    if not override:
        return template
    merged = template.model_dump(mode="json")
    merged.update(override)
    return ScenarioTemplate.model_validate(merged)
