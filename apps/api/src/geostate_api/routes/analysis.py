from __future__ import annotations

import asyncio
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from geostate_api.services.scenario_analysis import ALTERNATIVE_SOURCE_FEEDS, ISSUE_CATALOG, build_alternative_snapshot, build_dashboard_snapshot

router = APIRouter(tags=["analysis"])
_SNAPSHOT_CACHE: dict[str, dict[str, Any]] = {}
_SNAPSHOT_TIMESTAMPS: dict[str, datetime] = {}
_SNAPSHOT_HISTORY: dict[str, list[dict[str, Any]]] = {}
_REFRESH_TASKS: dict[str, asyncio.Task[Any]] = {}
_STORE_PATH = Path(__file__).resolve().parents[3] / "data" / "snapshot_store.json"
_BACKGROUND_TASK: asyncio.Task[Any] | None = None
_BACKGROUND_LAST_RUN_UTC: datetime | None = None

_DEFAULT_ISSUES: list[str] = [
    "red-sea-shipping",
    "gulf-energy-security",
    "russia-ukraine-war",
    "iran-israel-dynamics",
]
_BACKGROUND_PROFILES: list[dict[str, Any]] = [
    {
        "mode": "main",
        "selected_issues": _DEFAULT_ISSUES,
        "use_live": True,
        "lens": "global",
        "focus": None,
        "local_ai_enabled": True,
    },
    {
        "mode": "alternative",
        "selected_issues": _DEFAULT_ISSUES,
        "use_live": True,
        "lens": "global",
        "focus": None,
        "local_ai_enabled": True,
    },
]


def _cache_key(*, mode: str, selected_issues: list[str], use_live: bool, lens: str, focus: str | None, local_ai_enabled: bool) -> str:
    issues = ",".join(sorted(selected_issues))
    return f"{mode}|{issues}|{use_live}|{lens}|{focus or ''}|{local_ai_enabled}"


def _ttl_seconds(use_live: bool) -> int:
    return 900 if use_live else 7200


def get_refresh_status() -> dict[str, Any]:
    return {
        "background_refresh_enabled": True,
        "background_refresh_interval_seconds": int(os.getenv("BACKGROUND_REFRESH_INTERVAL_SECONDS", "3600")),
        "last_background_refresh_utc": None if _BACKGROUND_LAST_RUN_UTC is None else _BACKGROUND_LAST_RUN_UTC.isoformat(),
        "cached_profiles": len(_SNAPSHOT_CACHE),
    }


def _history_row(snapshot: dict[str, Any]) -> dict[str, Any]:
    return {
        "generated_utc": snapshot.get("generated_utc"),
        "mode": snapshot.get("mode"),
        "top_scenario": ((snapshot.get("scenarios") or [{}])[0]).get("name"),
        "overall_criticality": (snapshot.get("overall_criticality") or {}).get("percent"),
        "conflict_escalation": (snapshot.get("conflict_escalation") or {}).get("percent"),
    }


def _attach_cache_metadata(
    key: str,
    snapshot: dict[str, Any],
    cache_hit: bool,
    *,
    stale_fallback: bool = False,
    warning: str | None = None,
) -> dict[str, Any]:
    return {
        **snapshot,
        "snapshot_history": _SNAPSHOT_HISTORY.get(key, []),
        "cache": {
            "cache_hit": cache_hit,
            "cached_at_utc": (_SNAPSHOT_TIMESTAMPS.get(key) or datetime.now(UTC)).isoformat(),
            "stale_fallback": stale_fallback,
            "warning": warning,
        },
    }


def _find_latest_snapshot_for_mode(mode: str) -> tuple[str, dict[str, Any]] | None:
    candidates: list[tuple[str, datetime, dict[str, Any]]] = []
    for key, snapshot in _SNAPSHOT_CACHE.items():
        if not isinstance(snapshot, dict):
            continue
        if snapshot.get("mode") != mode:
            continue
        ts = _SNAPSHOT_TIMESTAMPS.get(key, datetime.min.replace(tzinfo=UTC))
        candidates.append((key, ts, snapshot))
    if not candidates:
        return None
    candidates.sort(key=lambda item: item[1], reverse=True)
    latest_key, _, latest_snapshot = candidates[0]
    return latest_key, latest_snapshot


def _serialize_store() -> dict[str, Any]:
    records: dict[str, Any] = {}
    for key, latest in _SNAPSHOT_CACHE.items():
        records[key] = {
            "cached_at_utc": (_SNAPSHOT_TIMESTAMPS.get(key) or datetime.now(UTC)).isoformat(),
            "latest": latest,
            "history": _SNAPSHOT_HISTORY.get(key, []),
        }
    return {"records": records}


def _persist_store() -> None:
    _STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    _STORE_PATH.write_text(json.dumps(_serialize_store()), encoding="utf-8")


def _load_store() -> None:
    if not _STORE_PATH.exists():
        return
    try:
        parsed = json.loads(_STORE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return
    records = parsed.get("records") if isinstance(parsed, dict) else None
    if not isinstance(records, dict):
        return
    for key, row in records.items():
        if not isinstance(row, dict):
            continue
        latest = row.get("latest")
        cached_at = row.get("cached_at_utc")
        history = row.get("history") or []
        if isinstance(latest, dict):
            _SNAPSHOT_CACHE[key] = latest
            if isinstance(cached_at, str):
                try:
                    _SNAPSHOT_TIMESTAMPS[key] = datetime.fromisoformat(cached_at)
                except ValueError:
                    _SNAPSHOT_TIMESTAMPS[key] = datetime.now(UTC)
            else:
                _SNAPSHOT_TIMESTAMPS[key] = datetime.now(UTC)
        if isinstance(history, list):
            _SNAPSHOT_HISTORY[key] = history[:2]


async def _refresh_cache(
    *,
    key: str,
    mode: str,
    selected_issues: list[str],
    use_live: bool,
    lens: str,
    focus: str | None,
    local_ai_enabled: bool,
) -> None:
    try:
        if mode == "alternative":
            snapshot = await build_alternative_snapshot(
                selected_issues,
                use_live=use_live,
                lens=lens,
                focus=focus,
                local_ai_enabled=local_ai_enabled,
            )
        else:
            snapshot = await build_dashboard_snapshot(
                selected_issues,
                use_live=use_live,
                lens=lens,
                focus=focus,
                local_ai_enabled=local_ai_enabled,
            )
        _SNAPSHOT_CACHE[key] = snapshot
        _SNAPSHOT_TIMESTAMPS[key] = datetime.now(UTC)
        history = _SNAPSHOT_HISTORY.setdefault(key, [])
        history.insert(0, _history_row(snapshot))
        del history[2:]
        _persist_store()
    finally:
        _REFRESH_TASKS.pop(key, None)


async def _get_cached_snapshot(
    *,
    mode: str,
    selected_issues: list[str],
    use_live: bool,
    lens: str,
    focus: str | None,
    local_ai_enabled: bool,
) -> dict[str, Any]:
    key = _cache_key(
        mode=mode,
        selected_issues=selected_issues,
        use_live=use_live,
        lens=lens,
        focus=focus,
        local_ai_enabled=local_ai_enabled,
    )
    cached = _SNAPSHOT_CACHE.get(key)
    cached_at = _SNAPSHOT_TIMESTAMPS.get(key)
    ttl = _ttl_seconds(use_live)
    now = datetime.now(UTC)

    async def _refresh_now() -> None:
        await _refresh_cache(
            key=key,
            mode=mode,
            selected_issues=selected_issues,
            use_live=use_live,
            lens=lens,
            focus=focus,
            local_ai_enabled=local_ai_enabled,
        )

    if cached is None or cached_at is None:
        try:
            await _refresh_now()
            return _attach_cache_metadata(key, _SNAPSHOT_CACHE[key], False)
        except Exception as error:
            fallback = _find_latest_snapshot_for_mode(mode)
            if fallback is not None:
                fallback_key, fallback_snapshot = fallback
                return _attach_cache_metadata(
                    fallback_key,
                    fallback_snapshot,
                    True,
                    stale_fallback=True,
                    warning=f"refresh_failed:{error.__class__.__name__}",
                )
            raise

    age = (now - cached_at).total_seconds()
    if age >= ttl and key not in _REFRESH_TASKS:
        _REFRESH_TASKS[key] = asyncio.create_task(
            _refresh_cache(
                key=key,
                mode=mode,
                selected_issues=selected_issues,
                use_live=use_live,
                lens=lens,
                focus=focus,
                local_ai_enabled=local_ai_enabled,
            )
        )
    return _attach_cache_metadata(key, cached, True)


async def _run_background_refresh_once() -> None:
    global _BACKGROUND_LAST_RUN_UTC
    for profile in _BACKGROUND_PROFILES:
        await _get_cached_snapshot(
            mode=profile["mode"],
            selected_issues=profile["selected_issues"],
            use_live=profile["use_live"],
            lens=profile["lens"],
            focus=profile["focus"],
            local_ai_enabled=profile["local_ai_enabled"],
        )
    _BACKGROUND_LAST_RUN_UTC = datetime.now(UTC)


async def _background_refresh_loop() -> None:
    interval = max(300, int(os.getenv("BACKGROUND_REFRESH_INTERVAL_SECONDS", "3600")))
    while True:
        try:
            await _run_background_refresh_once()
        except Exception:
            # keep loop alive; next cycle retries
            pass
        await asyncio.sleep(interval)


async def start_background_refresh_loop() -> None:
    global _BACKGROUND_TASK
    if _BACKGROUND_TASK is None or _BACKGROUND_TASK.done():
        _BACKGROUND_TASK = asyncio.create_task(_background_refresh_loop())


async def stop_background_refresh_loop() -> None:
    global _BACKGROUND_TASK
    if _BACKGROUND_TASK is None:
        return
    _BACKGROUND_TASK.cancel()
    try:
        await _BACKGROUND_TASK
    except asyncio.CancelledError:
        pass
    _BACKGROUND_TASK = None


class AnalyzeRequest(BaseModel):
    selected_issues: list[str] = Field(default_factory=list)
    use_live: bool = True
    lens: str = "global"
    focus: str | None = None
    local_ai_enabled: bool = True


class AlternativeAnalyzeRequest(BaseModel):
    selected_issues: list[str] = Field(default_factory=list)
    use_live: bool = True
    lens: str = "global"
    focus: str | None = None
    local_ai_enabled: bool = True


_load_store()


@router.get("/issues")
def list_issue_catalog() -> dict[str, Any]:
    return {"issues": [{"slug": slug, "label": label} for slug, label in ISSUE_CATALOG.items()]}


@router.get("/alternative-sources")
def list_alternative_sources() -> dict[str, Any]:
    return {
        "disclaimer": "Alternative/esoteric/conspiracy-adjacent sources are for narrative contrast, not verified truth.",
        "sources": ALTERNATIVE_SOURCE_FEEDS,
    }


@router.post("/analyze")
async def analyze(request: AnalyzeRequest) -> dict[str, Any]:
    return await _get_cached_snapshot(
        mode="main",
        selected_issues=request.selected_issues,
        use_live=request.use_live,
        lens=request.lens,
        focus=request.focus,
        local_ai_enabled=request.local_ai_enabled,
    )


@router.post("/alternative/analyze")
async def analyze_alternative(request: AlternativeAnalyzeRequest) -> dict[str, Any]:
    return await _get_cached_snapshot(
        mode="alternative",
        selected_issues=request.selected_issues,
        use_live=request.use_live,
        lens=request.lens,
        focus=request.focus,
        local_ai_enabled=request.local_ai_enabled,
    )


@router.get("/analyze/stream")
async def analyze_stream(
    issues: str = Query(default=""),
    use_live: bool = Query(default=True),
    lens: str = Query(default="global"),
    focus: str | None = Query(default=None),
    local_ai_enabled: bool = Query(default=True),
    interval_seconds: int = Query(default=900, ge=300, le=10800),
) -> StreamingResponse:
    selected_issues = [item.strip() for item in issues.split(",") if item.strip()]

    async def event_generator() -> Any:
        while True:
            snapshot = await _get_cached_snapshot(
                mode="main",
                selected_issues=selected_issues,
                use_live=use_live,
                lens=lens,
                focus=focus,
                local_ai_enabled=local_ai_enabled,
            )
            payload = json.dumps(snapshot)
            yield f"event: snapshot\ndata: {payload}\n\n"
            await asyncio.sleep(interval_seconds)

    return StreamingResponse(event_generator(), media_type="text/event-stream")
