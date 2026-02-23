import pytest

from easyshift_maas.examples.synthetic_templates import build_quality_stability_template
from easyshift_maas.templates.repository import InMemoryTemplateRepository


def test_template_export_import_roundtrip_json_yaml() -> None:
    pytest.importorskip("yaml")

    repo = InMemoryTemplateRepository()
    template = build_quality_stability_template()
    repo.publish(template)

    raw_json = repo.export_template(template.template_id, template.version, fmt="json")
    restored = repo.import_template(raw_json, fmt="json")
    assert restored.template_id == template.template_id

    raw_yaml = repo.export_template(template.template_id, template.version, fmt="yaml")
    restored_yaml = repo.import_template(raw_yaml, fmt="yaml")
    assert restored_yaml.version == template.version
