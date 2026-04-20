from fastapi import APIRouter, Depends, Request
from sqlalchemy import func, select

from src.api.v1.deps import DbSession, get_current_admin_user
from src.api.v1.schemas.admin import AdminStatusResponse
from src.db.models import Manual, User

router = APIRouter()


@router.get("/status", response_model=AdminStatusResponse)
async def admin_status(
    db_session: DbSession,
    _: User = Depends(get_current_admin_user),
) -> AdminStatusResponse:
    manuals_indexed = db_session.scalar(
        select(func.count(Manual.id)).where(Manual.status == "indexed")
    )
    active_users = db_session.scalar(
        select(func.count(User.id)).where(User.is_active.is_(True))
    )
    pending_jobs = db_session.scalar(
        select(func.count(Manual.id)).where(
            Manual.status.in_(["pending", "processing"])
        )
    )

    return AdminStatusResponse(
        manuals_indexed=manuals_indexed or 0,
        active_users=active_users or 0,
        pending_jobs=pending_jobs or 0,
    )
