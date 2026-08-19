from fastapi import APIRouter

from app.core.config import get_settings
from app.core.constants import (
    APP_VERSION,
    HEALTH_STATUS_HEALTHY,
    SERVICE_NAME,
)
from app.schemas.health import HealthResponse


router = APIRouter(
    prefix="/health",
    tags=["Health"],
)


@router.get(
    "",
    response_model=HealthResponse,
    summary="Check Asta service health",
)
async def health_check() -> HealthResponse:
    settings = get_settings()

    return HealthResponse(
        status=HEALTH_STATUS_HEALTHY,
        service=SERVICE_NAME,
        version=APP_VERSION,
        environment=settings.environment,
    )