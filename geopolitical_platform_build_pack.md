# Geopolitical State Engine Build Pack

## Contents
1. Product Requirements Document
2. Technical Architecture
3. Event Ontology and Scenario Engine Spec
4. Delivery Plan and Sprint Pack
5. Engineering Workflow, Git Management, QA, and Documentation Rules
6. CODEX.md
7. Prompt Instruction Pack for Building the Product

---

# 1. Product Requirements Document

## 1.1 Product Name
Geopolitical State Engine

## 1.2 Product Vision
Build a real-time web platform that senses geopolitical pressure, detects state transitions, models scenario probabilities, and explains actor-level and system-level impacts before conventional narratives stabilize.

This is not a news reader, a sentiment dashboard, or a static map.
It is a live geopolitical sensing and scenario engine.

## 1.3 Problem Statement
Decision-makers currently rely on delayed narratives, fragmented intelligence, and human interpretation that cannot continuously integrate shipping, market, military, diplomatic, and narrative signals at machine speed.

The result:
- phase transitions are detected late
- weak signals are ignored
- scenario probabilities are static or intuition-driven
- explanations are disconnected from real-time evidence

## 1.4 Product Goals
The platform must answer, continuously:
- What state is the system in now?
- What changed in the last hour, day, and week?
- Which scenarios are strengthening or weakening?
- What thresholds could trigger a phase transition?
- What is the impact on each actor, region, market, and infrastructure layer?

## 1.5 Target Users
Primary:
- geopolitical analysts
- sovereign risk teams
- commodities and shipping intelligence teams
- macro and strategic decision-makers

Secondary:
- think tanks
- journalists
- academic researchers
- policy teams

## 1.6 User Stories
### Analyst
- As an analyst, I want to see the current geopolitical state with confidence and dominant drivers so I can brief leadership quickly.
- As an analyst, I want to inspect why a scenario probability changed so I can trust the model.
- As an analyst, I want to annotate events and override weak machine extraction so the system improves.

### Executive
- As an executive, I want a concise impact summary by actor and market so I can make decisions fast.
- As an executive, I want alerts when trigger thresholds are near breach so I can prepare mitigation.

### Researcher
- As a researcher, I want to replay prior periods and compare predicted vs actual state shifts so I can validate models.

## 1.7 Core Features
### MVP
- Live signal ingestion
- Event extraction
- Current state detection
- Top scenario probabilities
- Trigger threshold board
- Actor impact summaries
- Incident map
- Evidence-based explanation panel
- Analyst annotation and approval workflow
- Daily snapshots and replay

### Post-MVP
- Narrative drift analysis
- Social clustering and anomaly detection
- Counterfactual simulation
- Sector exposure modeling
- API for downstream systems
- Portfolio impact module

## 1.8 Non-Goals
- fully autonomous policy recommendations without review
- black-box prediction without evidence traceability
- direct classified-intelligence dependency
- hard claims of certainty in contested events

## 1.9 Product Success Metrics
### Accuracy and usefulness
- analyst acceptance rate of extracted events
- state classification precision against reviewed benchmark set
- scenario movement interpretability score
- alert usefulness rating

### Usage
- daily active analyst sessions
- repeat session duration
- scenario drill-down usage
- replay mode usage

### Operational
- ingestion freshness latency
- extraction pipeline success rate
- data coverage by source type
- model update time

---

# 2. Technical Architecture

## 2.1 System Overview
The product has six layers:
1. Ingestion layer
2. Normalization and extraction layer
3. Knowledge graph and storage layer
4. State and scenario engine
5. Explanation and impact layer
6. Web application and analyst workflow layer

## 2.2 Recommended Stack
### Frontend
- Next.js
- TypeScript
- Tailwind CSS
- React Query
- Mapbox GL or deck.gl
- ECharts or Recharts

### Backend
- Python FastAPI
- Celery or Temporal for background jobs
- Postgres
- TimescaleDB extension for time series
- Neo4j or Memgraph for graph relationships
- Redis for queues and cache

### AI and Analytics
- spaCy for NER base pipeline
- transformer models for extraction and semantic similarity
- sentence embeddings for clustering and narrative drift
- Bayesian update layer for scenario probabilities
- rules engine for hard constraints

### Infrastructure
- Docker
- Docker Compose for local and initial deployment
- Kubernetes later if scale requires
- S3-compatible object storage for raw documents
- OpenTelemetry for observability

## 2.3 High-Level Service Layout
- ingestion-service
- extraction-service
- graph-service
- state-engine-service
- scenario-engine-service
- explanation-service
- api-gateway
- frontend-app
- worker-service
- scheduler-service

## 2.4 Data Flow
1. Pull live data from approved feeds
2. Store raw payload
3. Deduplicate and classify source
4. Extract entities, events, claims, time, location, confidence
5. Update graph and time-series tables
6. Recompute current state and scenario shifts
7. Recompute impact summaries
8. Publish to API and UI
9. Trigger alerts if thresholds are crossed

## 2.5 Security and Trust
- store provenance for every fact
- preserve raw source references
- every derived insight must reference evidence chain
- analyst override must be versioned and auditable

---

# 3. Event Ontology and Scenario Engine Spec

## 3.1 Event Ontology
### Event categories
- military strike
- drone attack
- missile launch
- infrastructure damage
- maritime disruption
- shipping reroute
- sanctions action
- diplomatic meeting
- official threat
- official de-escalation signal
- militia activity
- border incursion
- mobilization
- force deployment
- market shock
- refinery outage
- LNG disruption
- peacekeeping casualty

### Common event fields
- event_id
- title
- event_type
- timestamp_utc
- location_name
- latitude
- longitude
- actors_involved
- target_type
- source_ids
- extraction_confidence
- severity_score
- novelty_score
- attribution_status
- narrative_tags
- linked_scenarios

## 3.2 Actor Model
Each actor has:
- declared objectives
- inferred objectives
- constraints
- red lines
- current posture
- risk tolerance
- escalation style
- dependence profile
- alliance profile

## 3.3 State Taxonomy
- Stable
- Managed tension
- Controlled instability
- Distributed coercion
- Maritime pressure
- Hybrid escalation
- Pre-war transition
- Regional war
- Negotiated partial stabilization
- Post-shock recovery

## 3.4 Scenario Set
- Managed confrontation
- Hybrid pressure equilibrium
- Maritime or infrastructure shock
- Controlled partial reopening or corridor deal
- Regional war escalation
- Internal fragmentation or political rupture
- Negotiated stabilization

## 3.5 Probability Engine V1
Use a hybrid model.

### Prior
Maintain prior probability per scenario.

### Update
Apply weighted evidence likelihood ratios:
- signal supports scenario
- signal contradicts scenario
- source reliability modifies weight
- novelty modifies weight
- severity modifies weight

### Constraints
Apply rule-based caps and floors:
- if shipping throughput below threshold, stabilization probability cannot exceed cap
- if direct naval clash confirmed, regional war floor rises
- if repeated de-escalation signals with actual throughput recovery, confrontation scenario declines

### Output per scenario
- probability
- delta versus prior window
- top supporting evidence
- top contradicting evidence
- trigger thresholds to next state

## 3.6 Trigger Threshold Engine
Support:
- hard threshold
- soft threshold
- composite threshold
- actor-specific red lines

Example thresholds:
- merchant vessel strikes in rolling 7 days
- throughput percentage versus baseline
- Brent threshold persistence
- repeated cross-border drone attacks
- rhetoric escalation score
- diplomatic contact freeze duration
- peacekeeper casualty events

---

# 4. Delivery Plan and Sprint Pack

## 4.1 Phase Plan
### Phase 0: Definition
- finalize state taxonomy
- finalize scenario taxonomy
- finalize event ontology
- finalize actor profiles
- select initial sources

### Phase 1: MVP foundation
- scaffold frontend and backend
- implement source ingestion
- implement raw storage
- implement event extraction pipeline
- implement current state panel
- implement basic scenario cards

### Phase 2: Scenario engine
- implement Bayesian update layer
- implement rule-based threshold logic
- implement explanation engine
- implement actor impact cards

### Phase 3: Map and replay
- incident map
- chokepoint overlays
- historical timeline
- replay mode
- alerts

### Phase 4: Advanced analytics
- narrative drift
- anomaly detection
- counterfactuals
- sector impact and portfolio overlays

## 4.2 Sprint Plan
### Sprint 1
- repo setup
- architecture baseline
- schema v1
- ingestion service skeleton
- frontend shell

### Sprint 2
- raw document ingestion
- entity extraction
- event extraction v1
- source scoring baseline

### Sprint 3
- state engine v1
- scenario engine v1
- scenario card UI
- explanation panel v1

### Sprint 4
- map and chokepoint layer
- actor pages
- threshold board
- alert system

### Sprint 5
- replay mode
- annotation workflow
- model evaluation dashboard
- initial hardening

## 4.3 Acceptance Criteria for MVP
- current state visible and explainable
- top scenarios visible with probabilities
- each scenario update traceable to evidence
- at least one live source category integrated per domain:
  - news
  - official statements
  - markets
  - shipping
- analysts can approve or reject extracted events

---

# 5. Engineering Workflow, Git Management, QA, and Documentation Rules

## 5.1 Engineering Principles
- domain logic must remain pure and testable
- source ingestion and adapters must be isolated from reasoning logic
- all outputs must be reproducible from stored evidence
- every important decision must be documented in repo

## 5.2 Repo Structure
```text
/geostate-engine
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
  /data
    /fixtures
    /benchmarks
  /docs
    /architecture
    /adr
    /api
    /product
    /operations
  /.github
    /workflows
  /scripts
  CODEX.md
  README.md
```

## 5.3 Branching Strategy
Use trunk-based with controlled short-lived branches.

Branch naming:
- feat/<short-name>
- fix/<short-name>
- refactor/<short-name>
- docs/<short-name>
- chore/<short-name>

Rules:
- no long-lived feature branches without explicit decision
- PR size target under 500 lines changed when practical
- each PR must be reversible
- no direct push to main except emergency hotfix with post-review

## 5.4 Commit Rules
Conventional format:
- feat: add state taxonomy contracts
- fix: correct scenario update weight normalization
- docs: add event ontology v1
- refactor: separate market impact engine from scenario engine

## 5.5 Pull Request Rules
Every PR must include:
- purpose
- scope
- screenshots if UI changes
- test coverage summary
- migration note if schema changes
- rollback note if risky
- related issue or ADR reference

## 5.6 Issue Management
Issue types:
- Feature
- Bug
- Refactor
- Research spike
- Data source integration
- Documentation
- Incident

Suggested labels:
- priority:p0 p1 p2
- area:frontend backend ingestion model graph docs infra
- state:mvp later blocked ready-review

Issue template fields:
- objective
- context
- acceptance criteria
- dependencies
- risk
- notes

## 5.7 QA Strategy
### Unit tests
- pure domain rules
- event parsing
- scenario update math

### Integration tests
- ingestion to extraction
- extraction to database
- database to scenario engine

### E2E tests
- load dashboard
- inspect event
- review state
- review scenario change
- trigger alert

### Golden set evaluation
Maintain a reviewed benchmark set for:
- event extraction quality
- state classification
- scenario movement explanation

## 5.8 Documentation Rules
Required docs:
- README
- architecture overview
- ADRs
- data source catalog
- event ontology
- scenario engine spec
- API docs
- operations runbook
- incident response guide

Every new subsystem must ship with:
- purpose
- inputs
- outputs
- failure modes
- owner

## 5.9 ADR Rules
Store architecture decisions in /docs/adr.
Format:
- context
- decision
- alternatives considered
- consequences
- status

## 5.10 Definition of Done
A task is done only if:
- code merged
- tests passing
- docs updated
- contracts updated if needed
- screenshots or evidence attached
- monitoring considered

---

# 6. CODEX.md

```md
# CODEX.md

## Mission
Build and maintain the Geopolitical State Engine as a real-time, evidence-traceable geopolitical sensing and scenario platform.

This system is not a news summarizer. It is a state engine that ingests signals, extracts events, updates state, shifts scenario probabilities, and explains why.

## Product Intent
The platform must detect weak signals, model thresholds, and identify phase changes before conventional narratives stabilize.

## Core Rules
1. Preserve domain purity. Core logic must live in pure Python packages under /packages/domain, /packages/scenarios, /packages/explanations, and /packages/contracts.
2. Keep adapters separate. Source-specific ingestion, parsing, and API logic must live under /packages/adapters.
3. Be contract-first. Define or update schemas before implementing behavior.
4. Make everything evidence-traceable. No derived output without source provenance.
5. Favor explainability. Prefer simpler, auditable models over opaque complexity unless there is proven gain.
6. Support analyst override. Human-in-the-loop correction is a first-class product requirement.
7. Keep changes reversible. Avoid large entangled refactors unless explicitly planned.

## Architecture Constraints
- Frontend: Next.js, TypeScript, Tailwind
- Backend: FastAPI, Python
- Storage: Postgres, TimescaleDB, graph database
- Async jobs: Celery or Temporal
- Infra: Docker first

## Repository Structure
- /apps/web for frontend
- /apps/api for public API
- /apps/worker for background jobs
- /packages/contracts for schemas and type definitions
- /packages/domain for pure logic
- /packages/adapters for external sources
- /packages/scenarios for probability engine
- /packages/explanations for reasoning and summaries
- /docs for all product and engineering documentation

## Development Priorities
When working, prioritize in this order:
1. correctness
2. traceability
3. explainability
4. simplicity
5. performance
6. polish

## Required Workflow
For every meaningful task:
1. read relevant docs and contracts
2. create or update contract if needed
3. implement smallest useful slice
4. add or update tests
5. update docs
6. prepare concise PR summary with risk notes

## PR Expectations
Every PR must include:
- what changed
- why it changed
- screenshots if UI affected
- test summary
- schema migration summary if relevant
- rollback note for risky behavior

## Modeling Guidance
- treat states as dynamic and revisable
- never present certainty where evidence is ambiguous
- preserve contradictory evidence
- separate observed facts from inferred dynamics
- keep scenario updates auditable

## Data Handling Rules
- store raw source payloads
- preserve timestamps and source metadata
- do not overwrite extracted events silently
- version analyst overrides

## Testing Rules
Minimum required:
- unit tests for domain logic
- integration tests for ingestion and extraction pipeline
- scenario math tests for probability updates
- at least one end-to-end happy path for user-facing flows

## Documentation Rules
Update documentation whenever behavior, contracts, architecture, workflows, or data sources change.

Mandatory docs to maintain:
- README
- architecture overview
- event ontology
- scenario engine spec
- operations runbook
- ADRs

## Anti-Patterns
Do not:
- bury business logic inside UI or adapters
- ship black-box scenario updates with no explanation
- mix raw source truth with inference without labeling
- create large undocumented services
- make silent schema changes

## Immediate Build Order
1. state taxonomy and scenario taxonomy
2. event ontology
3. schema v1
4. ingestion pipeline
5. extraction pipeline
6. state engine v1
7. scenario engine v1
8. explanation panel
9. map and threshold board
10. replay and evaluation

## Quality Standard
The product is successful when an analyst can answer:
- what changed
- why it matters
- what state the system is in
- which scenarios strengthened or weakened
- what to monitor next

and can verify every major claim back to evidence.
```

---

# 7. Prompt Instruction Pack for Building the Product

## 7.1 Master Build Prompt
Use this prompt with Codex or another implementation agent.

```text
You are the principal engineer for a product called Geopolitical State Engine.
Your job is to build a real-time geopolitical sensing platform, not a news dashboard.

Product purpose:
- ingest live geopolitical, economic, shipping, and official-statement signals
- extract entities and events
- classify the current system state
- update scenario probabilities continuously
- explain why each probability changed
- show actor-level and market-level impacts
- expose trigger thresholds for phase transitions

You must follow these rules strictly:
1. Use contract-first development.
2. Keep core logic pure and framework-independent.
3. Preserve evidence provenance for every derived output.
4. Separate facts from inferences explicitly.
5. Favor explainable models over black-box models.
6. Keep the system modular and production-gradable.
7. Update documentation with every architectural or behavioral change.

Required stack:
- Next.js + TypeScript + Tailwind for frontend
- FastAPI + Python for backend
- Postgres + TimescaleDB for relational and time-series data
- graph database for entity and event relationships
- Celery or Temporal for background processing
- Docker-based local development

Build order:
1. define contracts for state taxonomy, scenario taxonomy, actor model, and event ontology
2. scaffold monorepo structure
3. implement ingestion service with source abstraction
4. implement event extraction pipeline
5. implement current-state engine v1
6. implement scenario probability engine v1 using weighted Bayesian updates plus rules
7. implement explanation engine
8. implement web UI with overview dashboard, scenario cards, map, actor view, and threshold board
9. implement analyst annotation workflow
10. implement replay and evaluation support

For every task you perform:
- explain what you are building
- explain why it belongs in that layer
- update tests
- update docs
- keep changes small and reversible

Do not produce generic placeholder code.
Produce production-structured code with comments only where useful.
Be explicit about assumptions and unresolved questions.
```

## 7.2 Prompt for Architecture Phase
```text
Design the initial architecture for Geopolitical State Engine.
Output:
- monorepo folder structure
- service boundaries
- contract files
- ADR drafts
- local development setup
- API boundaries
- data flow diagram in markdown

Constrain yourself to a maintainable MVP that can scale later.
Preserve domain purity and evidence traceability.
```

## 7.3 Prompt for Backend Phase
```text
Implement the backend foundation for Geopolitical State Engine.
Focus on:
- FastAPI app structure
- contracts package
- domain package
- ingestion abstractions
- raw document storage
- event extraction interfaces
- state engine interface
- scenario engine interface

Requirements:
- type-safe Python
- clean package boundaries
- tests for core logic
- docs for each module
- no hidden coupling between adapters and domain logic
```

## 7.4 Prompt for Frontend Phase
```text
Implement the frontend foundation for Geopolitical State Engine.
Build:
- overview dashboard
- current state panel
- scenario probability cards
- top driver panels
- event feed
- threshold board
- map shell
- actor detail shell

Requirements:
- Next.js with TypeScript
- Tailwind styling
- clean reusable components
- API client layer separated from components
- loading, empty, and error states
- analyst-grade readability over decorative visuals
```

## 7.5 Prompt for Scenario Engine Phase
```text
Build scenario probability engine v1.
Use:
- prior probabilities
- evidence likelihood weighting
- source reliability weighting
- severity weighting
- novelty weighting
- rule-based caps and floors

Output for each scenario:
- probability
- delta from prior window
- top supporting evidence
- top contradicting evidence
- dominant drivers
- trigger thresholds

The engine must be explainable and fully testable.
```

## 7.6 Prompt for Workflow and Documentation Discipline
```text
Enforce engineering workflow discipline across the repo.
Create:
- PR template
- issue templates
- ADR template
- contributor guide
- definition of done
- test strategy doc
- docs update checklist
- changelog policy

All templates must reflect a contract-first, evidence-traceable, explainable-system philosophy.
```

---

# 8. Suggested Immediate Next Deliverables

1. architecture diagram document
2. database schema v1 document
3. event ontology document
4. state and scenario contract files
5. repo scaffold
6. PR and issue templates
7. MVP wireframes
8. first implementation sprint board

---

# 9. Recommended Next Step

Start by generating:
- database schema v1
- repo scaffold
- CODEX.md as a file in root
- architecture ADR set
- first 10 issues for implementation

This gives an executable starting point instead of staying at concept level.

