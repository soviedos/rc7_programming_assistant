from fastapi import APIRouter

from src.api.v1.routes import admin, auth, chat, health, manuals, profile

api_router = APIRouter()
api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(profile.router, prefix="/profile", tags=["profile"])
api_router.include_router(manuals.router, prefix="/manuals", tags=["manuals"])
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])
