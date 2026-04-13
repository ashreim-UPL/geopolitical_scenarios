from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from geostate_api.routes.analysis import router as analysis_router
from geostate_api.routes.health import router as health_router


def create_app() -> FastAPI:
    app = FastAPI(
        title="Geopolitical State Engine API",
        version="0.1.0",
        description="Evidence-traceable geopolitical sensing and scenario backend."
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
