# CODEX.md

## Mission

Build and maintain the Geopolitical State Engine as a real-time, evidence-traceable geopolitical sensing and scenario platform.

## Operating Rules

1. Preserve domain purity.
2. Keep adapters separate from reasoning logic.
3. Be contract-first.
4. Preserve provenance for every derived fact.
5. Prefer explainability over opaque models.
6. Support analyst override as a first-class workflow.
7. Keep changes small and reversible.

## Repository Boundaries

- `apps/web` for the frontend
- `apps/api` for the public API
- `apps/worker` for background processing
- `packages/contracts` for schemas and shared types
- `packages/domain` for pure business logic
- `packages/adapters` for external source integrations
- `packages/scenarios` for scenario probability logic
- `packages/explanations` for explanation generation
- `packages/ui` for reusable UI primitives

## Required Workflow

For every meaningful change:

1. Read the relevant docs and contracts.
2. Update or add contracts before behavior.
3. Implement the smallest useful slice.
4. Add or update tests.
5. Update docs.
6. Prepare a concise summary with risk notes.

## Modeling Guidance

- Treat state as dynamic and revisable.
- Never present certainty where evidence is ambiguous.
- Preserve contradictory evidence.
- Separate observed facts from inferred dynamics.
- Keep scenario updates auditable.

## Testing Minimum

- Unit tests for pure domain logic
- Integration tests for ingestion and extraction
- Scenario math tests
- At least one end-to-end happy path

## Documentation Minimum

- README
- architecture overview
- event ontology
- scenario engine spec
- operations runbook
- ADRs

## Anti-Patterns

- Do not bury business logic inside UI or adapters.
- Do not ship black-box scenario updates without explanation.
- Do not mix raw source truth with inference without labels.
- Do not make silent schema changes.

