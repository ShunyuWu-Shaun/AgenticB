from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from easyshift_maas.agentic.migration_assistant import HybridMigrationAssistant
from easyshift_maas.agentic.template_validator import TemplateValidator
from easyshift_maas.core.contracts import (
    CatalogLoadMode,
    DataSourceProfile,
    FieldDictionary,
    PointCatalog,
    MigrationDraft,
    ScenarioTemplate,
    SceneContext,
    SceneMetadata,
    SimulationSample,
    SnapshotMissingPolicy,
    SnapshotRequest,
    TemplateQualityGate,
)
from easyshift_maas.core.pipeline import PredictionOptimizationPipeline
from easyshift_maas.examples.synthetic_templates import (
    build_energy_efficiency_template,
    build_quality_stability_template,
)
from easyshift_maas.ingestion.catalog_loader import YamlCatalogLoader
from easyshift_maas.ingestion.providers.mysql_provider import MySQLSnapshotProvider
from easyshift_maas.ingestion.providers.redis_provider import RedisSnapshotProvider
from easyshift_maas.ingestion.snapshot_provider import CompositeSnapshotProvider
from easyshift_maas.quality.template_quality import TemplateQualityEvaluator
from easyshift_maas.security.secrets import ChainedSecretResolver
from easyshift_maas.templates.base import list_base_templates


def _load_json(path: str) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _print_json(payload: Any) -> None:
    print(json.dumps(payload, indent=2, ensure_ascii=False))


def cmd_sample_template(variant: str) -> None:
    if variant == "energy":
        template = build_energy_efficiency_template()
    else:
        template = build_quality_stability_template()
    _print_json(template.model_dump(mode="json"))


def cmd_list_base_templates() -> None:
    items = [item.model_dump(mode="json") for item in list_base_templates()]
    _print_json(items)


def cmd_generate_draft(metadata_path: str, fields_path: str, requirements: list[str]) -> None:
    metadata = SceneMetadata.model_validate(_load_json(metadata_path))
    field_dictionary = FieldDictionary.model_validate(_load_json(fields_path))

    assistant = HybridMigrationAssistant()
    draft = assistant.generate(metadata, field_dictionary=field_dictionary, nl_requirements=requirements)
    _print_json(draft.model_dump(mode="json"))


def cmd_validate_draft(draft_path: str) -> None:
    draft = MigrationDraft.model_validate(_load_json(draft_path))
    report = TemplateValidator().validate(draft)
    _print_json(report.model_dump(mode="json"))


def cmd_quality_check(
    *,
    template_path: str | None,
    draft_path: str | None,
    samples_path: str | None,
) -> None:
    evaluator = TemplateQualityEvaluator()
    samples: list[SimulationSample] = []
    if samples_path:
        samples = [SimulationSample.model_validate(item) for item in _load_json(samples_path)]

    if template_path:
        template = ScenarioTemplate.model_validate(_load_json(template_path))
    else:
        draft = MigrationDraft.model_validate(_load_json(str(draft_path)))
        template = draft.template

    report = evaluator.evaluate(
        template=template,
        regression_samples=samples,
        gate=TemplateQualityGate(),
    )
    _print_json(report.model_dump(mode="json"))


def cmd_load_catalog(yaml_path: str, mode: str) -> None:
    loader = YamlCatalogLoader()
    result = loader.load(yaml_path=yaml_path, mode=CatalogLoadMode(mode))
    _print_json(result.model_dump(mode="json"))


def cmd_build_context(
    catalog_path: str,
    profiles_path: str,
    fields: list[str],
    missing_policy: str,
) -> None:
    catalog = PointCatalog.model_validate(_load_json(catalog_path))
    profiles = [DataSourceProfile.model_validate(item) for item in _load_json(profiles_path)]

    snapshot_provider = CompositeSnapshotProvider(
        providers=[RedisSnapshotProvider(), MySQLSnapshotProvider()]
    )
    secret_resolver = ChainedSecretResolver()

    request = SnapshotRequest(
        catalog_id=catalog.catalog_id,
        fields=fields or None,
        missing_policy=SnapshotMissingPolicy(missing_policy),
    )
    snapshot = snapshot_provider.fetch(
        request=request,
        catalog=catalog,
        profiles=profiles,
        secret_resolver=secret_resolver,
    )

    context = SceneContext(values=snapshot.values, metadata={"source": "snapshot"})
    _print_json({"scene_context": context.model_dump(mode="json"), "snapshot": snapshot.model_dump(mode="json")})


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

    sub.add_parser("list-base-templates", help="List official base templates")

    gen = sub.add_parser("generate-draft", help="Generate migration draft from metadata and field dictionary")
    gen.add_argument("--metadata", required=True)
    gen.add_argument("--fields", required=True)
    gen.add_argument("--requirement", action="append", default=[])

    validate = sub.add_parser("validate-draft", help="Validate migration draft JSON")
    validate.add_argument("--draft", required=True)

    quality = sub.add_parser("quality-check", help="Run template quality gate check")
    quality_group = quality.add_mutually_exclusive_group(required=True)
    quality_group.add_argument("--template")
    quality_group.add_argument("--draft")
    quality.add_argument("--samples")

    load_catalog = sub.add_parser("load-catalog", help="Load point catalog from YAML")
    load_catalog.add_argument("--yaml", required=True)
    load_catalog.add_argument("--mode", choices=["standard", "legacy"], default="standard")

    build_context = sub.add_parser("build-context", help="Build context from catalog + datasource profiles")
    build_context.add_argument("--catalog", required=True)
    build_context.add_argument("--profiles", required=True)
    build_context.add_argument("--field", action="append", default=[])
    build_context.add_argument("--missing-policy", choices=["error", "drop", "zero"], default="error")

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

    if args.command == "list-base-templates":
        cmd_list_base_templates()
        return

    if args.command == "generate-draft":
        cmd_generate_draft(args.metadata, args.fields, args.requirement)
        return

    if args.command == "validate-draft":
        cmd_validate_draft(args.draft)
        return

    if args.command == "quality-check":
        cmd_quality_check(template_path=args.template, draft_path=args.draft, samples_path=args.samples)
        return

    if args.command == "load-catalog":
        cmd_load_catalog(args.yaml, args.mode)
        return

    if args.command == "build-context":
        cmd_build_context(
            catalog_path=args.catalog,
            profiles_path=args.profiles,
            fields=args.field,
            missing_policy=args.missing_policy,
        )
        return

    if args.command == "simulate":
        cmd_simulate(args.template, args.context)
        return

    parser.error(f"unknown command: {args.command}")
