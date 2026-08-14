from uuid import UUID

import pytest
import yaml
from deckhand.adapters import CancellationDisposition
from deckhand.models import ActionRequest, RequestContext, Target
from deckhand.plugin_api import PluginContext

from dh_example.plugin import OBSERVE_ACTION, create_plugin


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
    assert list(contribution.adapters) == ["dh-example.read"]
    assert contribution.actions == (OBSERVE_ACTION,)


@pytest.mark.asyncio
async def test_reference_adapter_implements_complete_lifecycle() -> None:
    contribution = create_plugin().build(
        PluginContext(config={"domains": {"example": {"state": "healthy"}}})
    )
    adapter = contribution.adapters["dh-example.read"]
    request = ActionRequest(
        action_id=OBSERVE_ACTION.id,
        action_version=1,
        target=Target(type="example_domain", id="example"),
        parameters={},
        context=RequestContext(client="test"),
        idempotency_key=UUID("00000000-0000-4000-8000-000000000001"),
    )

    health = await adapter.health()
    plan = await adapter.plan(OBSERVE_ACTION, request)
    execution = await adapter.execute(OBSERVE_ACTION, request)
    observation = await adapter.observe(OBSERVE_ACTION, request)
    verification = await adapter.verify(OBSERVE_ACTION, request, execution, observation)
    cancellation = await adapter.cancel(OBSERVE_ACTION, request, execution)

    assert health.state == "healthy"
    assert len(plan.steps) == 3
    assert execution.reference == "observe:example"
    assert observation.state == "healthy"
    assert verification.satisfied is True
    assert cancellation.disposition == CancellationDisposition.ALREADY_TERMINAL
