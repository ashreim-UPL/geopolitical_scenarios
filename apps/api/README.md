# API App

## Run

```bash
pip install -e .[dev]
uvicorn geostate_api.main:app --env-file .env --reload --host 0.0.0.0 --port 8000
```

## Test

```bash
pytest -q
```

## Endpoints

- `GET /v1/health`
- `GET /v1/meta`
- `GET /v1/issues`
- `POST /v1/analyze`
- `POST /v1/alternative/analyze`
- `GET /v1/analyze/stream` (SSE)

## Notes

- `POST /v1/analyze` supports `use_live=true` for live multi-source ingestion:
  - Google News issue RSS (query-specific)
  - BBC World RSS
  - Guardian World RSS
  - Al Jazeera RSS
  - Optional Feedly stream ingestion (`FEEDLY_API_KEY` + stream IDs)
- `POST /v1/analyze` supports lensing fields:
  - `lens`: `global` | `region` | `country`
  - `focus`: optional string such as `Gulf` or `India`
- Scenario generation uses multi-method consensus:
  - driving forces
  - game-theory utility scoring
  - finite chessboard best-response simulation (bounded horizon)
- If live ingestion fails for a source, engine continues with remaining sources and records source health.
- If all live ingestion fails, API falls back to deterministic demo signals.
- Relevance filtering is LLM-assisted when provider keys are available:
  - each signal gets semantic summary + keywords + assigned issue bucket + relevance score
  - out-of-scope signals are excluded from live tape

## AI Provider Setup (.env)

Provider resolution order:

1. `nano` tier when request sends `local_ai_enabled=true` and `WINDOW_AI_AVAILABLE=true`
2. Gemini cloud when `GEMINI_API_KEY` is set
3. OpenAI when `OPENAI_API_KEY` is set
4. deterministic fallback

Create `.env` from the template:

```powershell
cd D:\dev\geopolitical_scenarios\apps\api
Copy-Item .env.example .env
```

Then edit `.env`:

```env
GEMINI_API_KEY=your_gemini_key
# or:
# OPENAI_API_KEY=your_openai_key
# optional local AI gate:
# WINDOW_AI_AVAILABLE=true
# optional Feedly ingestion:
# FEEDLY_API_KEY=your_feedly_token
# FEEDLY_STREAM_IDS=user/<id>/category/global,user/<id>/category/geopolitics
# FEEDLY_ALT_STREAM_IDS=user/<id>/category/misinformation,user/<id>/category/rumor-monitor
# optional extra RSS sources:
# ADDITIONAL_RSS_FEEDS=Reuters World|https://...;AP Top|https://...
# optional alternative RSS-only sources:
# ALTERNATIVE_RSS_FEEDS=EUvsDisinfo|https://euvsdisinfo.eu/feed/;HKS Review|https://misinforeview.hks.harvard.edu/feed/
# default auto-selected issue bucket:
# DEFAULT_ISSUE_BUCKET=iran-israel-dynamics
```

Run API with env file:

```powershell
uvicorn geostate_api.main:app --env-file .env --reload --host 0.0.0.0 --port 8000
```

If the API is already running, restart it after updating `.env`.

## Production Refresh Model

- Snapshots are cached server-side and persisted to:
  - `apps/api/data/snapshot_store.json`
- User requests return latest saved snapshot immediately.
- Stale caches are refreshed in background (non-blocking for UI).
- Last 2 snapshot frames are retained per profile.
- Background refresh loop runs automatically on API startup.

Optional cadence override:

```env
BACKGROUND_REFRESH_INTERVAL_SECONDS=3600
BACKGROUND_INGEST_INTERVAL_SECONDS=120
SIGNAL_INGEST_TTL_SECONDS=180
SCENARIO_IMAGE_CACHE_TTL_MINUTES=120
SEMANTIC_PARSE_CACHE_TTL_MINUTES=30
```

Defaults:
- snapshot refresh loop: hourly (`3600` seconds)
- ingestion loop: every 2 minutes (`120` seconds)
