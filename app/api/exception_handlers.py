import structlog
from fastapi import Request
from fastapi.responses import JSONResponse

from app.core.exceptions import AstaError


logger = structlog.get_logger(__name__)


async def asta_exception_handler(
    request: Request,
    exc: AstaError,
) -> JSONResponse:
    request_id = getattr(
        request.state,
        "request_id",
        None,
    )

    logger.warning(
        "asta_application_error",
        error_code=exc.error_code,
        error_message=exc.message,
    )

    return JSONResponse(
        status_code=400,
        content={
            "error": {
                "code": exc.error_code,
                "message": exc.message,
            },
            "request_id": request_id,
        },
    )


async def unhandled_exception_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    request_id = getattr(
        request.state,
        "request_id",
        None,
    )

    logger.exception(
        "unhandled_application_error",
        exception_type=type(exc).__name__,
    )

    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected error occurred.",
            },
            "request_id": request_id,
        },
    )