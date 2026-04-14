from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from geostate_api.routes.analysis import (
    router as analysis_router,
    start_background_refresh_loop,
    stop_background_refresh_loop,
)
from geostate_api.routes.health import router as health_router


@asynccontextmanager
async def lifespan(_app: FastAPI):
    await start_background_refresh_loop()
    try:
        yield
    finally:
        await stop_background_refresh_loop()


def create_app() -> FastAPI:
    app = FastAPI(
        title="Geopolitical State Engine API",
        version="0.1.0",
        description="Evidence-traceable geopolitical sensing and scenario backend.",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health_router, prefix="/v1")
    app.include_router(analysis_router, prefix="/v1")
    return app


app = create_app()
