"""Application entry point.

All bootstrap lives in build_app(); importing this module performs no I/O so
tests can build isolated apps and `uvicorn main:app` still works out of the box.
"""

import logging
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api.routes import router as api_router
from core.config import Settings
from core.logging_config import setup_logging
from core.pdns import PdnsError, PolicyError

logger = logging.getLogger(__name__)


def build_app(settings: Settings | None = None) -> FastAPI:
    """Construct the FastAPI app: lifespan-managed HTTP clients, CORS, error
    handlers, and the API router. Takes an explicit Settings so tests can
    build isolated apps without touching the process environment."""
    # Called here, not at module level, so importing main.py still performs
    # no I/O on its own — only running the app (or a test building one) does.
    setup_logging()
    settings = settings or Settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.http = httpx.AsyncClient(
            base_url=settings.pdns_api_url,
            headers={"X-API-Key": settings.pdns_api_key},
            timeout=10.0,
        )
        # Separate client for JWKS fetches: the PowerDNS client above carries
        # X-API-Key, which must never be sent to Keycloak.
        app.state.oidc_http = httpx.AsyncClient(timeout=10.0)
        # A log line, not state: `docker compose logs backend` shows exactly
        # what PROTECTED_ZONES resolved to at startup.
        logger.info("Protected zones: %s", sorted(settings.protected_zones) or "(none)")
        yield
        await app.state.http.aclose()
        await app.state.oidc_http.aclose()

    app = FastAPI(title="pdns-admin-lite", lifespan=lifespan)
    app.state.settings = settings

    if settings.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origins,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    @app.exception_handler(PdnsError)
    @app.exception_handler(PolicyError)
    async def pdns_error_handler(request: Request, exc: PdnsError | PolicyError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code, content={"detail": exc.detail, "code": exc.code}
        )

    app.include_router(api_router, prefix="/api")
    return app


app = build_app()
