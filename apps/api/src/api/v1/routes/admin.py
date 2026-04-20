from fastapi import APIRouter

from src.api.v1.schemas.admin import AdminStatusResponse

router = APIRouter()


@router.get("/status", response_model=AdminStatusResponse)
async def admin_status() -> AdminStatusResponse:
    return AdminStatusResponse(
        manuals_indexed=0,
        active_users=0,
        pending_jobs=0,
    )
