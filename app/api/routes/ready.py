from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

from app.core.constants import APP_VERSION, SERVICE_NAME
from app.core.readiness import Readiness, check_readiness

router = APIRouter(tags=["Health"])


async def readiness_probe():
    return await check_readiness()


@router.get("/ready", summary="Check database readiness")
async def ready(request: Request, result: Readiness = Depends(readiness_probe)):
    if not result.ready:
        request.state.operational_error_code = "database_unavailable"
    return JSONResponse(status_code=200 if result.ready else 503, content={
        "status": "ready" if result.ready else "not_ready",
        "service": SERVICE_NAME, "version": APP_VERSION,
        "components": result.components(),
    })
