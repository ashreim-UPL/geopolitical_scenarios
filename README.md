# Geopolitical State Engine

Real-time geopolitical sensing platform for evidence-traceable state detection, scenario modeling, and analyst workflow.

This repository starts as a documentation-first scaffold derived from the build pack and blueprint in the repo root:

- `geopolitical_platform_build_pack.md`
- `realtime_geopolitical_sensing_platform_blueprint.md`

## What This Repo Contains

- Product requirements and scope
- Architecture and data model guidance
- Event ontology and scenario engine notes
- Git workflow and repository management rules
- Production and operations guidance
- Codex operating instructions
- GitHub templates for PRs and issues

## Repo Layout

```text
/apps
  /web
  /api
  /worker
/packages
  /contracts
  /domain
  /adapters
  /graph
  /scenarios
  /explanations
  /ui
/docs
  /architecture
  /adr
  /engineering
  /operations
  /product
/.github
/scripts
CODEX.md
README.md
```

## Working Model

1. Read the product and architecture docs before implementing anything.
2. Define or update contracts first.
3. Keep domain logic pure and isolated from adapters.
4. Keep evidence provenance on every derived output.
5. Update documentation whenever behavior changes.

## Current State

This repo now includes executable starter applications:

1. `apps/api` FastAPI service with health, issue catalog, scenario analysis, and SSE streaming
2. `apps/web` Next.js dashboard with issue filters, scenario board, trend/force panels, explanation drawer, and generated visual image
3. `packages/contracts` taxonomy and event schema contracts
4. GitHub CI workflow for web and API checks

Live-data behavior:

- API attempts live issue-based RSS ingestion (`use_live=true`)
- If live feed parsing fails, it falls back to deterministic demo signals
- Scenario calculations in this version are heuristic and explainable, not production-grade probabilistic intelligence

## Quick Start

Web:

```bash
cd apps/web
npm install
npm run dev
```

API:

```bash
cd apps/api
pip install -e .[dev]
uvicorn geostate_api.main:app --reload --host 0.0.0.0 --port 8000
```

## Useful Docs

- [Codex guidance](./CODEX.md)
- [Contributing](./CONTRIBUTING.md)
- [Docs index](./docs/README.md)
- [Git workflow](./docs/engineering/git-workflow.md)
- [Git management](./docs/engineering/git-management.md)
- [Production details](./docs/operations/production-details.md)
