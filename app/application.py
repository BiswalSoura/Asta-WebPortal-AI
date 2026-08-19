from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import api_router
from app.api.exception_handlers import (
    asta_exception_handler,
    unhandled_exception_handler,
)
from app.api.middleware import RequestIDMiddleware
from app.core.config import get_settings
from app.core.constants import APP_VERSION
from app.core.exceptions import AstaError
from app.core.logging import configure_logging


logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()

    logger.info(
        "application_started",
        app_name=settings.app_name,
        environment=settings.environment,
        version=APP_VERSION,
    )

    yield

    logger.info(
        "application_stopped",
        app_name=settings.app_name,
    )


def create_application() -> FastAPI:
    settings = get_settings()

    configure_logging(settings.log_level)

    application = FastAPI(
        title=settings.app_name,
        version=APP_VERSION,
        description=(
            "Enterprise AI knowledge assistant API "
            "for A&A Engineering WebPortal."
        ),
        lifespan=lifespan,
    )

    application.add_middleware(
        RequestIDMiddleware,
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=[],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    application.add_exception_handler(
        AstaError,
        asta_exception_handler,
    )

    application.add_exception_handler(
        Exception,
        unhandled_exception_handler,
    )

    application.include_router(
        api_router,
        prefix=settings.api_v1_prefix,
    )

    return application