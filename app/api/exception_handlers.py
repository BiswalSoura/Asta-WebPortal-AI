from fastapi import Request
from fastapi.responses import JSONResponse

from app.core.exceptions import AstaError
from app.core.telemetry import classify_error, emit


async def asta_exception_handler(
    request: Request,
    exc: AstaError,
) -> JSONResponse:
    request_id = getattr(
        request.state,
        "request_id",
        None,
    )

    request.state.operational_error_code = classify_error(exc)
    emit("application_error", request_id=request_id, error_code=classify_error(exc))

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

    request.state.operational_error_code = classify_error(exc)
    emit("application_error", request_id=request_id, error_code=classify_error(exc))

    return JSONResponse(
        status_code=500,
        headers={"X-Request-ID": request_id} if request_id else {},
        content={
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected error occurred.",
            },
            "request_id": request_id,
        },
    )