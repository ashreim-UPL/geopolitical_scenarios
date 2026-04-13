# Real-Time Geopolitical Sensing Platform Blueprint

## Purpose
Build a web-based geopolitical sensing and prediction system that ingests real-time signals, infers the current system state, simulates forward scenarios, and explains impact across actors, markets, logistics, and conflict zones.

This is not a news dashboard.
It is a state-detection and scenario engine.

---

## 1. Product Thesis

Traditional geopolitical analysis is event-driven, slow, and narrative-heavy.
The platform should instead:

- detect weak signals before the narrative catches up
- model pressure, thresholds, and state transitions
- update probabilities continuously
- separate observable facts from inferred dynamics
- quantify impact on each actor, region, and system layer

Core output:

1. What state is the system in now?
2. What changed in the last 1h, 6h, 24h, 7d?
3. Which scenario paths are strengthening or weakening?
4. What thresholds would trigger a phase change?
5. Who gains, who loses, and through which mechanism?

---

## 2. Product Scope

### In scope
- Real-time signal ingestion
- Event extraction and normalization
- State engine
- Scenario probability engine
- Impact engine
- Explainable reasoning layer
- Interactive web UI
- Alerting and threshold monitoring
- Historical replay and backtesting

### Out of scope for MVP
- Full autonomous trading
- Classified or private intelligence ingestion
- Fully automated policy recommendations without human review
- Direct military prediction claims beyond probabilistic modeling

---

## 3. Core Users

### Primary
- strategic analysts
- sovereign / institutional risk teams
- commodity and shipping intelligence teams
- geopolitical researchers
- executive decision-makers

### Secondary
- journalists
- think tanks
- academic researchers
- advanced retail macro users

---

## 4. System Design Principles

1. State over headlines
2. Pressure over narrative
3. Probabilities over absolutes
4. Explainability over black-box confidence
5. Multi-layer causality over single-cause storytelling
6. Continuous update over static reports
7. Human-in-the-loop for high-stakes interpretation

---

## 5. Conceptual Model

The platform tracks five interacting layers:

### Layer A. Physical layer
- shipping routes
- ports
- chokepoints
- bases
- strikes
- military movement
- satellite / thermal anomalies

### Layer B. Economic layer
- oil prices
- LNG prices
- insurance rates
- freight costs
- sovereign spreads
- FX stress
- equity reaction

### Layer C. Political layer
- official statements
- sanctions
- summits
- diplomatic visits
- legal framing
- alliance coordination

### Layer D. Narrative layer
- semantic drift in speeches
- media framing changes
- social clustering and velocity
- propaganda themes
- religious / ideological framing

### Layer E. Strategic layer
- incentives
- red lines
- thresholds
- coalition cohesion
- deterrence clarity
- tempo control

The product must fuse these into a single evolving system state.

---

## 6. State Model

The engine should classify the current system into one of several states.

### Suggested state taxonomy
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

Each state has:
- confidence score
- dominant drivers
- rising signals
- fading signals
- likely exit paths

---

## 7. Scenario Engine

The scenario engine does not output one forecast.
It outputs a probability distribution over multiple futures.

### Base scenario types
1. Managed confrontation
2. Hybrid pressure equilibrium
3. Maritime / infrastructure shock
4. Controlled partial reopening / corridor deal
5. Regional war escalation
6. Internal fragmentation / political rupture
7. Negotiated stabilization

### For each scenario, compute
- current probability
- delta vs previous period
- key supporting signals
- key contradictory signals
- actor-level impact
- trigger thresholds to next phase

---

## 8. Trigger Threshold Engine

Each scenario requires quantified or semi-quantified triggers.

### Examples
- number of merchant vessel attacks in rolling 7 days
- percentage of pre-crisis Hormuz throughput
- Brent above a threshold for N consecutive days
- repeated drone attacks from Iraqi territory into Gulf states
- public rhetoric shift from conditional to absolute terms
- confirmed deaths of peacekeepers / diplomats
- official move from escort posture to blockade posture
- major desalination / refinery / LNG facility damage

The system should support:
- soft thresholds
- hard thresholds
- composite thresholds
- actor-specific red lines

---

## 9. Data Architecture

### Ingestion sources for MVP
#### Structured / high-signal
- news APIs
- market data APIs
- shipping / AIS feeds
- flight tracking APIs
- commodities APIs
- social firehose summary sources
- official government / ministry RSS feeds

#### Semi-structured
- press releases
- speeches
- X / Telegram summaries
- analyst notes
- think tank updates

### Data pipeline stages
1. ingestion
2. deduplication
3. source reliability scoring
4. entity extraction
5. event extraction
6. temporal normalization
7. geo-normalization
8. causal linking
9. state update
10. scenario update

---

## 10. Machine Intelligence Stack

### A. Event extraction models
Detect:
- attacks
- threats
- sanctions
- statements
- deployments
- maritime disruptions
- infrastructure damage

### B. Narrative analysis models
Detect:
- tone shift
- semantic drift
- coercive language
- de-escalatory language
- ideological framing
- denial vs signaling

### C. Anomaly detection models
Detect:
- unusual shipping patterns
- unusual rhetoric shifts
- unusual market dislocations
- weak-signal clustering before visible escalation

### D. Scenario probability models
Use a hybrid system:
- rules engine for hard constraints
- Bayesian updating for probability shifts
- graph model for path propagation
- optional agent-based simulation later

### E. Explanation engine
Translate model output into analyst-grade reasoning:
- what changed
- why probability moved
- what to watch next

---

## 11. Knowledge Representation

Use a graph-centric backend.

### Entities
- actor
- state
- militia
- leader
- asset
- port
- chokepoint
- facility
- vessel
- event
- statement
- market signal
- scenario

### Relationships
- threatens
- attacked
- signaled
- denied
- supports
- coordinated_with
- constrained_by
- impacts
- escalates_to
- de-escalates_to

This makes causal tracing and visualization much stronger than a pure relational model.

---

## 12. Reasoning Strategy

Use a hybrid reasoning pipeline:

### Deterministic layer
Hard constraints and first-principles rules:
- geography
- military feasibility
- chokepoint capacity
- economic exposure
- actor red lines

### Probabilistic layer
- update scenario weights from observed evidence
- handle uncertainty and contradiction

### Narrative layer
- explain why observable facts may not map cleanly to public rhetoric
- model actors who are non-linear, prestige-driven, ideological, or domestically constrained

---

## 13. Website UX Structure

### Primary screens

#### 1. System Overview
Shows:
- current state
- top 4 scenarios with probabilities
- key shifts in last 24h
- dominant drivers
- global impact summary

#### 2. Live Signal Board
Shows:
- incoming signals by severity
- source quality
- confidence
- geography
- signal type

#### 3. Scenario Explorer
Shows:
- scenario cards
- probability trend over time
- supporting / contradictory evidence
- actor impact breakdown
- trigger thresholds

#### 4. Map View
Shows:
- chokepoints
- active incidents
- shipping / flight overlays
- infrastructure nodes
- signal density
- pressure heatmap

#### 5. Actor View
Shows:
- objectives
- constraints
- current posture
- hidden incentives
- stress indicators
- likely next moves

#### 6. Impact View
Shows:
- oil / LNG / freight / insurance / FX / sovereign spread impact
- sector exposure by region
- country-level winners / losers

#### 7. Replay / Backtest
Shows:
- state timeline
- scenario evolution
- “what the system believed at the time”

#### 8. Alerts / Thresholds
Shows:
- watched indicators
- threshold distances
- what would cause state transition

---

## 14. Recommended MVP

### MVP goal
Build a working version that can:
- ingest live signals
- produce a current state
- display top 4 scenarios with probabilities
- explain probability changes
- show trigger thresholds

### MVP feature list
- live news and official statement ingestion
- event extraction pipeline
- manual source weighting panel
- state classification engine
- scenario probability dashboard
- map with incidents and chokepoints
- actor cards
- daily snapshot archive

### MVP non-goals
- perfect automated truth
- fully autonomous signal scoring
- social media full-stream ingestion
- advanced simulation of all actors

---

## 15. Tech Stack Recommendation

### Frontend
- Next.js
- TypeScript
- Tailwind
- React Query
- Mapbox GL or deck.gl
- Recharts or ECharts

### Backend
- Python FastAPI
- Celery or Temporal for jobs
- Postgres + TimescaleDB for time series
- Neo4j or Memgraph for causal graph
- Redis for caching and queues

### ML / AI layer
- Python
- spaCy / transformers for NER and extraction
- sentence embeddings for clustering and semantic drift
- Bayesian / probabilistic modeling libraries
- graph analytics

### Infra
- Docker
- Kubernetes later, start with Docker Compose
- object storage for raw source archive
- observability with OpenTelemetry

---

## 16. Data Model Sketch

### Core tables
- sources
- raw_documents
- extracted_events
- entities
- event_entity_links
- scenario_snapshots
- state_snapshots
- signal_scores
- actor_profiles
- thresholds
- alerts

### Time-series tables
- market_signals
- throughput_signals
- freight_signals
- insurance_signals
- rhetoric_shift_signals

---

## 17. Scoring Framework

Each signal should have:
- source reliability score
- confidence score
- relevance score
- novelty score
- severity score
- directional effect on each scenario

Example:
- drone attack on Gulf infrastructure
  - reliability: high
  - severity: high
  - novelty: medium
  - scenario impact:
    - regional war +0.12
    - hybrid pressure +0.05
    - controlled reopening -0.10

---

## 18. Suggested First Scenario Math

Start simple.

### Use weighted Bayesian adjustment
- prior probability per scenario
- apply evidence likelihood ratios
- normalize to 100%

### Add rule-based overrides
Example:
- if throughput < X and repeated merchant strikes > Y, suppress stabilization scenario cap
- if direct naval clash occurs, boost regional war floor

This gives explainability before you move to heavier ML.

---

## 19. Human-in-the-Loop Controls

Essential for trust.

Allow analysts to:
- approve / reject extracted events
- adjust source credibility
- annotate key signals
- set custom thresholds
- pin strategic assumptions

The machine should augment analysts, not replace them.

---

## 20. What the Machine Adds Beyond Human Analysis

1. Detect weak signals before headlines
2. Track thousands of signals simultaneously
3. Measure narrative drift continuously
4. Estimate phase transitions before visible escalation
5. Simulate multiple future paths in parallel
6. Maintain memory across cycles without narrative fatigue
7. Quantify contradiction rather than hide it

---

## 21. Differentiation

This product is not:
- a geopolitical newsletter
- a sentiment dashboard
- a map of incidents
- a generic LLM wrapper

It is:
- a geopolitical state engine
- a threshold monitor
- a scenario probability system
- an explanation layer for dynamic conflict systems

---

## 22. Build Order

### Phase 1
- define actor taxonomy
- define state taxonomy
- define scenario taxonomy
- define signal schema
- create manual input dataset from recent conflict history

### Phase 2
- implement ingestion pipeline
- implement event extraction
- implement dashboard skeleton
- implement probability engine v1

### Phase 3
- add map + graph views
- add threshold alerts
- add replay / backtest

### Phase 4
- add richer social / narrative drift
- add anomaly detection
- add simulation layer

---

## 23. Immediate Next Deliverables

1. Product Requirements Document
2. System architecture diagram
3. Database schema v1
4. Event ontology
5. Scenario probability engine spec
6. UI wireframes
7. MVP implementation plan by sprint

---

## 24. Recommended Immediate Next Step

Start with a narrow operational theater for the MVP:
- Hormuz
- Gulf infrastructure
- Iraqi militia spillover
- Lebanon front

This is enough complexity to prove the engine without drowning in global scope.

---

## 25. Success Criteria for MVP

The MVP is successful if it can do the following reliably:
- explain the current system state
- show which scenario probabilities moved and why
- identify 3 to 5 trigger thresholds worth monitoring
- present impact by actor and by system layer
- support analyst review and correction

---

## 26. Final Product Statement

This platform should function like a geopolitical wind tunnel.
It should not merely describe events.
It should show how pressure moves through a system, where thresholds are weakening, and which future paths are becoming more likely before they become obvious.

