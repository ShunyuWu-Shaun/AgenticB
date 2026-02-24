from __future__ import annotations

from easyshift_maas.core.contracts import (
    MigrationDraft,
    MigrationValidationReport,
    PointCatalog,
    ScenarioTemplate,
    TemplateQualityReport,
)


def scenario_template_schema() -> dict:
    return ScenarioTemplate.model_json_schema()


def migration_draft_schema() -> dict:
    return MigrationDraft.model_json_schema()


def migration_validation_report_schema() -> dict:
    return MigrationValidationReport.model_json_schema()


def point_catalog_schema() -> dict:
    return PointCatalog.model_json_schema()


def template_quality_report_schema() -> dict:
    return TemplateQualityReport.model_json_schema()
