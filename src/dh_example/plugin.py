from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

from deckhand.adapters import (
    AdapterCancellation,
    AdapterError,
    AdapterErrorKind,
    AdapterExecution,
    AdapterHealth,
    AdapterHealthState,
    AdapterObservation,
    AdapterPlan,
    AdapterVerification,
    CancellationDisposition,
)
from deckhand.models import (
    ActionDefinition,
    ActionRequest,
    ConfirmationMode,
    RiskClass,
    StatusValue,
    StrictModel,
)
from deckhand.plugin_api import (
    DeckhandPlugin,
    PluginContext,
    PluginContribution,
    PluginManifest,
    PluginPermissions,
    StaticStatusProvider,
)
from pydantic import Field, field_validator


class ExampleDomain(StrictModel):
    state: str = Field(min_length=1, max_length=64)
    stale_after_seconds: int = Field(default=30, ge=1, le=3600)
    details: dict[str, Any] = Field(default_factory=dict)


class ExampleConfig(StrictModel):
    domains: dict[str, ExampleDomain] = Field(default_factory=dict)

    @field_validator("domains")
    @classmethod
    def validate_domain_names(cls, value: dict[str, ExampleDomain]) -> dict[str, ExampleDomain]:
        invalid = [name for name in value if re.fullmatch(r"[a-z][a-z0-9_]{0,63}", name) is None]
        if invalid:
            raise ValueError("domain names must contain only letters, numbers, and underscores")
        return value


CONFIG_SCHEMA: dict[str, Any] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "additionalProperties": False,
    "required": ["domains"],
    "properties": {
        "domains": {
            "type": "object",
            "propertyNames": {"pattern": "^[a-z][a-z0-9_]{0,63}$"},
            "additionalProperties": {
                "type": "object",
                "additionalProperties": False,
                "required": ["state"],
                "properties": {
                    "state": {"type": "string", "minLength": 1, "maxLength": 64},
                    "stale_after_seconds": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 3600,
                    },
                    "details": {"type": "object"},
                },
            },
        }
    },
}


OBSERVE_ACTION = ActionDefinition(
    id="example.domain.observe",
    version=1,
    title="Observe example domain",
    description="Read the configured state for a logical example domain.",
    risk_class=RiskClass.READ,
    plugin="dh-example",
    adapter="dh-example.read",
    target_types=["example_domain"],
    parameter_schema={
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "additionalProperties": False,
        "properties": {},
    },
    policy_action="example.domain.observe",
    confirmation=ConfirmationMode.NONE,
    timeout_seconds=10,
    idempotency="read-only",
    mutation=False,
)


class ExampleReadAdapter:
    """Complete, deterministic reference implementation of Deckhand's adapter contract."""

    def __init__(self, domains: Mapping[str, ExampleDomain]) -> None:
        self.domains = dict(domains)

    def _domain(self, request: ActionRequest) -> ExampleDomain:
        try:
            return self.domains[request.target.id]
        except KeyError as error:
            raise AdapterError(
                "example domain is not configured",
                kind=AdapterErrorKind.NOT_FOUND,
            ) from error

    async def health(self) -> AdapterHealth:
        return AdapterHealth(
            state=AdapterHealthState.HEALTHY,
            details={"configured_domain_count": len(self.domains)},
        )

    async def plan(self, action: ActionDefinition, request: ActionRequest) -> AdapterPlan:
        self._domain(request)
        return AdapterPlan(steps=["resolve logical domain", "observe state", "verify observation"])

    async def execute(self, action: ActionDefinition, request: ActionRequest) -> AdapterExecution:
        self._domain(request)
        return AdapterExecution(reference=f"observe:{request.target.id}")

    async def observe(self, action: ActionDefinition, request: ActionRequest) -> AdapterObservation:
        domain = self._domain(request)
        return AdapterObservation(state=domain.state, details=domain.details)

    async def verify(
        self,
        action: ActionDefinition,
        request: ActionRequest,
        execution: AdapterExecution,
        observation: AdapterObservation,
    ) -> AdapterVerification:
        return AdapterVerification(
            satisfied=observation.state != "unknown",
            details={"execution_reference": execution.reference},
        )

    async def cancel(
        self,
        action: ActionDefinition,
        request: ActionRequest,
        execution: AdapterExecution | None,
    ) -> AdapterCancellation:
        return AdapterCancellation(disposition=CancellationDisposition.ALREADY_TERMINAL)


class ExamplePlugin:
    @property
    def manifest(self) -> PluginManifest:
        return PluginManifest(
            id="dh-example",
            name="Example",
            version="0.2.0",
            description=(
                "Reference read-only adapter and status provider for Deckhand plugin authors."
            ),
            adapters=["dh-example.read"],
            status_provider_types=["static-example"],
            actions=[OBSERVE_ACTION.id],
            permissions=PluginPermissions(mutation=False),
            config_schema=CONFIG_SCHEMA,
        )

    def build(self, context: PluginContext) -> PluginContribution:
        config = ExampleConfig.model_validate(dict(context.config))
        providers: Mapping[str, StaticStatusProvider] = {
            name: StaticStatusProvider(
                StatusValue(
                    state=domain.state,
                    stale_after_seconds=domain.stale_after_seconds,
                    details=domain.details,
                )
            )
            for name, domain in config.domains.items()
        }
        return PluginContribution(
            adapters={"dh-example.read": ExampleReadAdapter(config.domains)},
            status_providers=providers,
            actions=(OBSERVE_ACTION,),
        )


def create_plugin() -> DeckhandPlugin:
    return ExamplePlugin()
