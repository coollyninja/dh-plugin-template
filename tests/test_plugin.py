import yaml
from deckhand.plugin_api import PluginContext

from dh_example.plugin import create_plugin


def test_manifest_matches_repository_document() -> None:
    with open("deckhand-plugin.yaml", encoding="utf-8") as manifest_file:
        document = yaml.safe_load(manifest_file)
    assert document == create_plugin().manifest.model_dump(mode="json")


def test_build_contributes_only_configured_logical_domains() -> None:
    contribution = create_plugin().build(
        PluginContext(
            config={
                "domains": {
                    "example": {
                        "state": "healthy",
                        "details": {"source": "template"},
                    }
                }
            }
        )
    )
    assert list(contribution.status_providers) == ["example"]
