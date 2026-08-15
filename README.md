# dh-plugin-template

This repository is the reference starter for an independently releasable Deckhand plugin. It ships as a working, read-only `dh-example` adapter and status provider so contract, discovery, configuration, and tests are demonstrable before integration-specific behavior is added.

## Create a plugin

1. Create a repository from this template named `dh-<integration>`.
2. Replace `dh-example`, `dh_example`, and the human-readable metadata everywhere.
3. Keep runtime components under the plugin namespace: `dh-<integration>.<component>`.
4. Declare every adapter, action, permission, credential slot, and egress binding in `deckhand-plugin.yaml` and the runtime manifest.
5. Implement all six adapter lifecycle methods: `health`, `plan`, `execute`, `observe`, `verify`, and `cancel`.
6. Replace the static provider and adapter with the smallest integration boundary that can be tested without a real site.
7. Convert upstream failures into typed, sanitized `AdapterError` values. Use `UnknownOutcome` when a mutation may have happened but cannot yet be proven.
8. Pin the supported Deckhand core release or immutable commit and run the full conformance suite.

Public examples use logical names and `.invalid` addresses only. Real endpoints, resource IDs, certificate names, and secrets belong in a private site overlay.

## Local verification

```bash
uv sync --locked --all-groups
uv run ruff check .
uv run ruff format --check .
uv run mypy src
uv run python scripts/check_public_surface.py
uv run pytest
```

The template is MIT licensed.
