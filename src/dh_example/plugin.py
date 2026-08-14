import re
from collections.abc import Mapping
from typing import Any

from deckhand.models import StatusValue, StrictModel
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


class ExamplePlugin:
    @property
    def manifest(self) -> PluginManifest:
        return PluginManifest(
            id="dh-example",
            name="Example",
            version="0.1.0",
            description="Reference read-only status provider for Deckhand plugin authors.",
            status_provider_types=["static-example"],
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
        return PluginContribution(status_providers=providers)


def create_plugin() -> DeckhandPlugin:
    return ExamplePlugin()
