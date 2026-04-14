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

- `POST /v1/analyze` supports `use_live=true` for live Google News RSS ingestion by issue query.
- `POST /v1/analyze` supports lensing fields:
  - `lens`: `global` | `region` | `country`
  - `focus`: optional string such as `Gulf` or `India`
- Scenario generation uses multi-method consensus:
  - driving forces
  - game-theory utility scoring
  - finite chessboard best-response simulation (bounded horizon)
- If live ingestion fails, API falls back to deterministic demo signals.

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
```

Default is hourly (`3600` seconds).
