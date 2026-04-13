# Web App

## Run

```bash
npm install
npm run dev
```

## Build

```bash
npm run build
```

## Features in this starter

- Issue-based filtering for global scenarios
- Lens-based impact views (`global`, `region`, `country`) with reweighted criticality
- Realtime updates from API SSE stream
- Scenario probability board and force trend cards
- Expandable explanation panel
- Generated SVG force-pressure image
- Optional Chrome on-device Prompt API analysis when available
- Criticality bands: `0-20 Low`, `21-40 Guarded`, `41-60 Elevated`, `61-80 High`, `81-100 Critical`
- Dual-risk semantics:
  - `Systemic Criticality`: broad instability/spillover index
  - `Conflict Escalation Likelihood`: escalation-path risk index
- `Stable` trend means signal velocity is flat; for `Pre-war transition`, this can mean a dangerous high-tension plateau
- Three-Sector Model visual cards (Primary/Secondary/Tertiary)
- Maslow-style hierarchy risk panel with max-biased aggregation (Safety cannot be averaged away)
