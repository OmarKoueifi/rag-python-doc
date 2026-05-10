from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.core.config import Settings, get_settings
from app.core.rate_limit import limiter
from app.db.session import create_all
from app.routers import admin, chat, health

log = logging.getLogger(__name__)


@asynccontextmanager
async def _lifespan(_app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    _warn_if_admin_unconfigured(settings)
    await create_all()
    if settings.seed_on_startup:
        from scripts.seed_db import _is_empty, _seed

        if await _is_empty():
            log.info("Seeding fixture data on startup")
            await _seed()
    log.info("Startup complete — environment=%s", settings.environment)
    yield


def _warn_if_admin_unconfigured(settings: Settings) -> None:
    if not settings.admin_password:
        log.warning("ADMIN_PASSWORD not set — /api/admin/login will reject everything.")
    if not settings.session_secret:
        log.warning("SESSION_SECRET not set — admin login will fail at request time.")


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="Ask the Python Docs — API",
        description=(
            "Retrieval-augmented chat over Python's asyncio and typing docs, "
            "with an admin dashboard for question + retrieval observability."
        ),
        version="0.1.0",
        lifespan=_lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type"],
    )

    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.add_middleware(SlowAPIMiddleware)

    app.include_router(health.router)
    app.include_router(chat.router)
    app.include_router(admin.router)

    return app


app = create_app()
