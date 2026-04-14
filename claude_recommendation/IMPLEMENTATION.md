# Geopolitical State Engine — Redesign Implementation Guide

## Files delivered

| File | Destination in your repo | What it does |
|---|---|---|
| `globals.css` | `app/globals.css` | Full visual system: tokens, typography, all component styles |
| `page.tsx` | `app/page.tsx` (or wherever your main dashboard lives) | Complete Next.js App Router page with all components and dynamic weight logic |
| `weight_resolver.py` | `packages/scenarios/weight_resolver.py` | Python backend for dynamic method weights, with full test suite |

---

## Step-by-step instructions

### 1. Replace globals.css

```bash
cp globals.css <your-project>/app/globals.css
```

**What changes:**
- Background: solid `#070c14` (replaces the radial gradient which looked decorative rather than instrumental)
- Adds `JetBrains Mono` as a second font for all data labels, badges, and monospace values
- All CSS variables are renamed for clarity (`--bg`, `--bg2`...`--bg4`, `--panel`, `--panel2`, `--border`, `--border2`, `--border3`)
- Adds every new component class: `.command-row`, `.full-width-bar`, `.esc-bar-track`, `.scenario-row`, `.tape-severity`, `.weight-sliders`, etc.
- The old `.panel.compact` and `.grid-2 / .grid-3` classes are kept for backward compatibility

### 2. Replace page.tsx

```bash
cp page.tsx <your-project>/app/page.tsx
```

**What changes:**
- `'use client'` directive at top (required for useState/interactivity)
- All data arrays (`SCENARIOS`, `ACTORS`, `TAPE`, etc.) are at the top of the file — replace them with API calls when your backend is ready
- The `resolveWeights()` function is a pure TypeScript mirror of `weight_resolver.py` — keep both in sync
- `PHASE_PRESETS` maps state names to default weights — add new states here as the state engine grows
- Weight sliders use React `useState` and are fully interactive
- Issue filter pills use a `Set<string>` for O(1) toggle

**Connecting to your API (when ready):**

Replace the static data arrays at the top with `useEffect` + `fetch` calls:

```typescript
// Example: replace SCENARIOS with API data
const [scenarios, setScenarios] = useState(SCENARIOS);

useEffect(() => {
  fetch('/v1/analysis/scenarios')
    .then(r => r.json())
    .then(data => setScenarios(data.scenarios));
}, []);
```

The existing FastAPI route in `geostate_api/routes/analysis.py` is where to add the `/v1/analysis/scenarios` endpoint.

### 3. Add weight_resolver.py to your backend

```bash
cp weight_resolver.py <your-project>/packages/scenarios/weight_resolver.py
```

**Wire it into your FastAPI route:**

```python
# In geostate_api/routes/analysis.py
from packages.scenarios.weight_resolver import (
    resolve_method_weights, SystemState, PhaseVelocity, ForceType
)

@router.get("/v1/analysis/method-weights")
def get_method_weights(
    state: str = "managed_tension",
    velocity: str = "stable",
    force_type: str = "military"
):
    weights = resolve_method_weights(
        system_state=SystemState(state),
        phase_velocity=PhaseVelocity(velocity),
        dominant_force_type=ForceType(force_type),
    )
    return {
        "weights": weights.as_percentages(),
        "disagreement_index": weights.disagreement_index,
        "derived_from": weights.derived_from,
        "analyst_override": weights.analyst_override,
    }
```

**Run the built-in smoke test:**

```bash
python packages/scenarios/weight_resolver.py
```

Expected output:
```
managed_tension        | DF=33% GT=35% CB=32% | di=0.003
maritime_pressure      | DF=27% GT=27% CB=46% | di=0.022
pre_war_transition     | DF=23% GT=41% CB=36% | di=0.022
regional_war           | DF=18% GT=43% CB=39% | di=0.025
negotiated_stabilization | DF=45% GT=23% CB=32% | di=0.024
```

---

## Key design decisions

### Why `JetBrains Mono`?
All numerical data (percentages, indices, timestamps, actor confidence scores) uses the mono font. This gives the dashboard an intelligence-terminal aesthetic and makes numbers instantly distinguishable from prose labels.

### Why solid `#070c14` background instead of the radial gradient?
The radial gradient (green glow top-left, blue glow bottom-right) looks beautiful in a portfolio screenshot but undermines the "instrument panel" feel during actual use. Solid deep navy reads as authoritative and doesn't compete with the data.

### Why a 2-column layout instead of full-width stacked sections?
The original design stacked everything vertically, forcing the analyst to scroll to compare related data (e.g. scenario lattice vs actor moves). The 2-column layout puts high-density analysis on the left and right-panel reference cards (actors, force split, Maslow, countries, analysts) always visible together.

### The weight sliders
The sliders call `resolveWeights(rawDf, rawGt, rawCb)` on every change — a pure function that normalizes the raw values to sum to 100%. This means an analyst can move one slider and the other displayed values update live, showing exactly what the normalized result is before committing. The disagreement index also recalculates live.

### The 3px severity left-border on tape items
This is the single highest-impact design change to the live tape. Severity is now scannable in <1 second without reading any text: red = high, amber = medium, grey = low. The original flat list had no visual urgency signal.

---

## Known issues (from browser inspection)

1. **Blank rendering region (fixed in this redesign):** The original page had a large empty dark area mid-page between Impact Lens and the State + Trend grid. This was caused by `.visual-heavy` applying `gap: 0.9rem` to the outer grid while inner components had large implicit margins. The new layout uses explicit `flex-direction: column; gap: 1rem` on `.left-col` / `.right-col` which eliminates this.

2. **CORS wildcard:** `main.py` has `allow_origins=["*"]`. Add to your environment config:
```python
import os
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
# In production, this env var must NOT contain "*"
```

3. **Missing FastAPI lifespan handler:** When you add DB pool and Redis connections, add:
```python
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # startup
    await init_db_pool()
    yield
    # shutdown
    await close_db_pool()

app = FastAPI(lifespan=lifespan, ...)
```

---

## What to build next (priority order)

1. Connect `page.tsx` data arrays to `/v1/analysis/*` API endpoints
2. Add the `/v1/analysis/method-weights` endpoint using `weight_resolver.py`
3. Add the actor posture endpoint (currently static in the TSX)
4. Wire up the live tape to a real ingestion queue
5. Add a Mapbox chokepoint overlay (Hormuz / Bab el-Mandeb pressure heatmap)
6. Add the arc gauge for systemic criticality (SVG or canvas, replace the linear bar)
