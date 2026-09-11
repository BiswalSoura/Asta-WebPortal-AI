"""Temporary server-configured internal/demo boundary, never browser role claims."""
import secrets
from fastapi import Depends, HTTPException, Request
from app.core.config import get_settings


def require_knowledge_admin(request: Request, settings=Depends(get_settings)):
    if not settings.knowledge_admin_api_enabled:
        raise HTTPException(404, detail="ADMIN_API_DISABLED")
    expected = settings.knowledge_admin_token
    secret = expected.get_secret_value() if expected else ""
    # Misconfiguration fails closed; blank/example/short tokens cannot enable management.
    if not 32 <= len(secret) <= 512:
        raise HTTPException(503, detail="ADMIN_NOT_CONFIGURED")
    supplied = request.headers.get("X-Asta-Admin-Token", "")
    if len(supplied) > 512 or not secrets.compare_digest(supplied.encode(), secret.encode()):
        raise HTTPException(401, detail="ADMIN_UNAUTHORIZED")
