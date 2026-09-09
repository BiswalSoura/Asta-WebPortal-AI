from fastapi import APIRouter

from app.api.routes.health import router as health_router

from app.api.routes import chat
from app.api.routes.ready import router as ready_router

api_router = APIRouter()

api_router.include_router(health_router)
api_router.include_router(ready_router)

api_router.include_router(
    chat.router
)
