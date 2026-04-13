# API App

## Run

```bash
pip install -e .[dev]
uvicorn geostate_api.main:app --reload --host 0.0.0.0 --port 8000
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
