from datetime import UTC, datetime

from fastapi import APIRouter

from geostate_api.routes.analysis import get_refresh_status

router = APIRouter(tags=["system"])


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/meta")
def meta() -> dict[str, str | dict]:
    return {
        "service": "geostate-api",
        "version": "0.1.0",
        "timestamp_utc": datetime.now(UTC).isoformat(),
        "refresh": get_refresh_status(),
    }
