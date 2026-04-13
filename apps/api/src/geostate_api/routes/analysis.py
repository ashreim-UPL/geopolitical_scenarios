from __future__ import annotations

import asyncio
import json
from typing import Any

from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from geostate_api.services.scenario_analysis import ISSUE_CATALOG, build_dashboard_snapshot

router = APIRouter(tags=["analysis"])


class AnalyzeRequest(BaseModel):
    selected_issues: list[str] = Field(default_factory=list)
    use_live: bool = True
    lens: str = "global"
    focus: str | None = None


@router.get("/issues")
def list_issue_catalog() -> dict[str, Any]:
    return {"issues": [{"slug": slug, "label": label} for slug, label in ISSUE_CATALOG.items()]}


@router.post("/analyze")
async def analyze(request: AnalyzeRequest) -> dict[str, Any]:
    return await build_dashboard_snapshot(
        request.selected_issues,
        use_live=request.use_live,
        lens=request.lens,
        focus=request.focus,
    )


@router.get("/analyze/stream")
async def analyze_stream(
    issues: str = Query(default=""),
    use_live: bool = Query(default=True),
    lens: str = Query(default="global"),
    focus: str | None = Query(default=None),
    interval_seconds: int = Query(default=30, ge=5, le=300),
) -> StreamingResponse:
    selected_issues = [item.strip() for item in issues.split(",") if item.strip()]

    async def event_generator() -> Any:
        while True:
            snapshot = await build_dashboard_snapshot(selected_issues, use_live=use_live, lens=lens, focus=focus)
            payload = json.dumps(snapshot)
            yield f"event: snapshot\ndata: {payload}\n\n"
            await asyncio.sleep(interval_seconds)

    return StreamingResponse(event_generator(), media_type="text/event-stream")
