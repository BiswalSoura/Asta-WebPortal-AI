"""HTTP correlation including CORS short circuits and handled errors."""
from time import perf_counter
import structlog
from starlette.datastructures import Headers, MutableHeaders
from starlette.requests import Request
from app.core.telemetry import classify_error, emit, normalize_request_id


class RequestIDMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http':
            return await self.app(scope, receive, send)
        values = Headers(scope=scope).getlist('x-request-id')
        request_id = normalize_request_id(values[0] if len(values) == 1 else None)
        state = scope.setdefault('state', {})
        state['request_id'] = request_id
        tokens = structlog.contextvars.bind_contextvars(request_id=request_id)
        started = perf_counter()
        status = 500
        response_started = False

        def fields():
            return dict(request_id=request_id, method=scope['method'],
                        route=getattr(scope.get('route'), 'path', 'unmatched'),
                        status_code=status, elapsed_ms=round((perf_counter()-started)*1000, 3))

        async def correlated_send(message):
            nonlocal status, response_started
            if message['type'] == 'http.response.start':
                status = message['status']
                response_started = True
                MutableHeaders(scope=message)['X-Request-ID'] = request_id
            await send(message)

        emit('request_started', request_id=request_id, method=scope['method'])
        try:
            try:
                await self.app(scope, receive, correlated_send)
            except Exception as exc:
                state['operational_error_code'] = classify_error(exc)
                if response_started:
                    emit('request_failed', **fields(), error_code=classify_error(exc))
                    raise
                # Preserve the authoritative central error response; avoid a server traceback.
                from app.api.exception_handlers import unhandled_exception_handler
                response = await unhandled_exception_handler(Request(scope), exc)
                await response(scope, receive, correlated_send)
            code = state.get('operational_error_code') or classify_error(status_code=status)
            if status >= 400:
                emit('request_failed', **fields(), error_code=code)
            emit('request_completed', **fields(), error_code=code)
        finally:
            structlog.contextvars.reset_contextvars(**tokens)
