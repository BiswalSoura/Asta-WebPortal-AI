"""Finite errors and bounded body reading only for M16 routes."""
from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.routing import APIRoute
from pydantic import ValidationError
from app.knowledge.exceptions import KnowledgeError
from app.services.knowledge_operations import OperationsError


class OperationsRoute(APIRoute):
    def get_route_handler(self):
        original = super().get_route_handler()
        async def handler(request):
            try:
                return await original(request)
            except (RequestValidationError, ValidationError):
                raise HTTPException(422, detail="INVALID_REQUEST") from None
            except OperationsError as exc:
                raise HTTPException(exc.status, detail=exc.code) from None
            except KnowledgeError as exc:
                code = exc.error_code if exc.error_code in {
                    'UNSUPPORTED_DOCUMENT_TYPE', 'DOCUMENT_TOO_LARGE', 'EMPTY_DOCUMENT',
                    'DOCUMENT_LOAD_ERROR'} else 'PROCESSING_FAILED'
                raise HTTPException(422, detail=code) from None
            except HTTPException:
                raise
            except Exception:
                # Never pass raw loader/SQL/model exceptions to the HTTP server logger.
                raise HTTPException(500, detail="OPERATIONS_FAILED") from None
        return handler


async def bounded_stream(request: Request, limit: int):
    length = request.headers.get('content-length')
    if length is not None:
        if not length.isascii() or not length.isdecimal():
            raise HTTPException(400, detail="INVALID_CONTENT_LENGTH")
        if len(length) > 12 or int(length) > limit:
            raise HTTPException(413, detail="BODY_TOO_LARGE")
    total = 0
    async for part in request.stream():
        total += len(part)
        if total > limit:
            raise HTTPException(413, detail="BODY_TOO_LARGE")
        yield part
