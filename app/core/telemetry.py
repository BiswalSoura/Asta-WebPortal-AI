"""Allowlisted operational events. Payloads and exception text are never accepted."""
import math
import re
from contextlib import contextmanager
from time import perf_counter
from uuid import uuid4
import structlog
from sqlalchemy.exc import SQLAlchemyError
from app.core.constants import APP_VERSION, SERVICE_NAME
from app.core.exceptions import AstaError, ConfigurationError
from app.core.config import get_settings

_ID = re.compile(r'[A-Za-z0-9][A-Za-z0-9._-]{0,63}', re.ASCII)
ERROR_CODES = frozenset({'none', 'validation_error', 'conversation_not_found',
    'database_unavailable', 'provider_unavailable', 'configuration_error',
    'application_error', 'http_error', 'internal_error'})
EVENTS = frozenset({'request_started', 'request_completed', 'request_failed',
    'application_error', 'stage_started', 'stage_completed', 'stage_failed',
    'chat_outcome', 'conversation_outcome'})


def normalize_request_id(value):
    return value if isinstance(value, str) and _ID.fullmatch(value) else str(uuid4())


def classify_error(exc=None, *, status_code=None):
    if isinstance(exc, ConfigurationError):
        return 'configuration_error'
    if isinstance(exc, SQLAlchemyError):
        return 'database_unavailable'
    if isinstance(exc, AstaError):
        if exc.error_code == 'CONVERSATION_NOT_FOUND':
            return 'conversation_not_found'
        if exc.error_code in {'LLM_REQUEST_ERROR', 'EMPTY_LLM_RESPONSE'}:
            return 'provider_unavailable'
        if exc.error_code == 'LLM_CONFIGURATION_ERROR':
            return 'configuration_error'
        return 'application_error'
    if exc is not None:
        return 'internal_error'
    if status_code == 422:
        return 'validation_error'
    if status_code is not None and status_code >= 500:
        return 'internal_error'
    if status_code is not None and status_code >= 400:
        return 'http_error'
    return 'none'


def safe_fields(fields):
    result = {}
    enums = {'error_code': ERROR_CODES, 'stage': {'conversation', 'rag', 'retrieval', 'llm'},
             'path': {'guardrail_bypass', 'rag'},
             'outcome': {'bypass', 'grounded', 'insufficient_information'},
             'method': {'GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS', 'HEAD', 'TRACE', 'CONNECT'}}
    for key, value in fields.items():
        if key in enums and isinstance(value, str) and value in enums[key]:
            result[key] = value
        elif key == 'request_id' and isinstance(value, str) and _ID.fullmatch(value):
            result[key] = value
        elif key in {'grounded', 'contextualized', 'model_used'} and type(value) is bool:
            result[key] = value
        elif key in {'source_count', 'status_code'} and type(value) is int and 0 <= value <= 9999:
            result[key] = value
        elif key == 'elapsed_ms' and type(value) in (int, float) and math.isfinite(value) and value >= 0:
            result[key] = value
        elif key == 'route' and isinstance(value, str) and value in {
            'unmatched', '/api/v1/health', '/api/v1/ready', '/api/v1/chat/conversations',
            '/api/v1/chat/conversations/{conversation_id}/messages'}:
            result[key] = value
        elif key == 'route':
            result[key] = 'unmatched'
    return result


def emit(event, **fields):
    if event not in EVENTS:
        return
    context = structlog.contextvars.get_contextvars()
    safe = safe_fields({'request_id': context.get('request_id'), **fields})
    structlog.contextvars.clear_contextvars()
    try:
        environment = get_settings().environment
        if environment not in {'development', 'test', 'testing', 'staging', 'production', 'local'}:
            environment = 'other'
        structlog.get_logger(__name__).info(event, service=SERVICE_NAME, version=APP_VERSION,
                                           environment=environment, **safe)
    finally:
        structlog.contextvars.bind_contextvars(**context)


@contextmanager
def observe(stage):
    start = perf_counter()
    emit('stage_started', stage=stage)
    try:
        yield
    except Exception as exc:
        emit('stage_failed', stage=stage, error_code=classify_error(exc),
             elapsed_ms=round((perf_counter()-start)*1000, 3))
        raise
    else:
        emit('stage_completed', stage=stage, elapsed_ms=round((perf_counter()-start)*1000, 3))
