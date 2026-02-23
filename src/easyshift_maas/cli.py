from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from easyshift_maas.agentic.migration_assistant import HybridMigrationAssistant
from easyshift_maas.agentic.template_validator import TemplateValidator
from easyshift_maas.core.contracts import FieldDictionary, MigrationDraft, ScenarioTemplate, SceneContext, SceneMetadata
from easyshift_maas.core.pipeline import PredictionOptimizationPipeline
from easyshift_maas.examples.synthetic_templates import (
    build_energy_efficiency_template,
    build_quality_stability_template,
)


def _load_json(path: str) -> Any:
    return json.loads(Path(path).read_text())


def _print_json(payload: Any) -> None:
    print(json.dumps(payload, indent=2, ensure_ascii=False))


def cmd_sample_template(variant: str) -> None:
    if variant == "energy":
        template = build_energy_efficiency_template()
    else:
        template = build_quality_stability_template()
    _print_json(template.model_dump(mode="json"))


def cmd_generate_draft(metadata_path: str, fields_path: str, requirements: list[str]) -> None:
    metadata = SceneMetadata.model_validate(_load_json(metadata_path))
    field_dictionary = FieldDictionary.model_validate(_load_json(fields_path))

    assistant = HybridMigrationAssistant()
    draft = assistant.generate(metadata, field_dictionary, requirements)
    _print_json(draft.model_dump(mode="json"))


def cmd_validate_draft(draft_path: str) -> None:
    draft = MigrationDraft.model_validate(_load_json(draft_path))
    report = TemplateValidator().validate(draft)
    _print_json(report.model_dump(mode="json"))


def cmd_simulate(template_path: str, context_path: str) -> None:
    template = ScenarioTemplate.model_validate(_load_json(template_path))
    context = SceneContext.model_validate(_load_json(context_path))
    result = PredictionOptimizationPipeline().run(context, template)
    _print_json(result.model_dump(mode="json"))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="EasyShift-MaaS CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    sample = sub.add_parser("sample-template", help="Print a synthetic template")
    sample.add_argument("--variant", choices=["energy", "quality"], default="energy")

    gen = sub.add_parser("generate-draft", help="Generate migration draft from metadata and field dictionary")
    gen.add_argument("--metadata", required=True)
    gen.add_argument("--fields", required=True)
    gen.add_argument("--requirement", action="append", default=[])

    validate = sub.add_parser("validate-draft", help="Validate migration draft JSON")
    validate.add_argument("--draft", required=True)

    simulate = sub.add_parser("simulate", help="Run one prediction-optimization simulation")
    simulate.add_argument("--template", required=True)
    simulate.add_argument("--context", required=True)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "sample-template":
        cmd_sample_template(args.variant)
        return

    if args.command == "generate-draft":
        cmd_generate_draft(args.metadata, args.fields, args.requirement)
        return

    if args.command == "validate-draft":
        cmd_validate_draft(args.draft)
        return

    if args.command == "simulate":
        cmd_simulate(args.template, args.context)
        return

    parser.error(f"unknown command: {args.command}")
