from datetime import UTC, datetime

from fastapi import APIRouter

router = APIRouter(tags=["system"])


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/meta")
def meta() -> dict[str, str]:
    return {
        "service": "geostate-api",
        "version": "0.1.0",
        "timestamp_utc": datetime.now(UTC).isoformat()
    }

