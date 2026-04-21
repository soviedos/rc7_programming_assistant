from fastapi import APIRouter, HTTPException, Request, status
from sqlalchemy import select

from src.api.v1.deps import DbSession, get_current_user
from src.api.v1.schemas.chat import (
    ChatHistoryItemResponse,
    ChatHistoryListResponse,
    ChatRequest,
    ChatResponse,
    ReferenceItem,
)
from src.db.models.chat_history import ChatHistory
from src.services.chat.service import generate_rag_response

router = APIRouter()


def _serialize_history_item(item: ChatHistory) -> ChatHistoryItemResponse:
    return ChatHistoryItemResponse(
        id=item.id,
        prompt=item.prompt,
        summary=item.summary,
        pac_code=item.pac_code,
        references=[
            ReferenceItem(title=r.get("title", ""), page=r.get("page", ""))
            for r in (item.references or [])
        ],
        robot_config=item.robot_config or {},
        entry_type=item.entry_type,
        created_at=item.created_at,
    )


@router.post("/generate", response_model=ChatResponse)
async def generate_code(
    request: Request,
    payload: ChatRequest,
    db: DbSession,
) -> ChatResponse:
    user = get_current_user(request, db)  # raises 401 if not authenticated

    try:
        result = generate_rag_response(db, payload)
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc

    # Persist to chat history
    entry_type = (
        "code" if result.pac_code and result.pac_code.strip() else "troubleshooting"
    )
    history_item = ChatHistory(
        user_id=user.id,
        prompt=payload.prompt,
        summary=result.summary,
        pac_code=result.pac_code or "",
        references=[{"title": r.title, "page": r.page} for r in result.references],
        robot_config={
            "robot_type": payload.robot_type,
            "controller": payload.controller,
            "io_profile": payload.io_profile,
            "payload_kg": payload.payload_kg,
            "tool_number": payload.tool_number,
            "max_speed_pct": payload.max_speed_pct,
            "hand_type": payload.hand_type,
            "install_type": payload.install_type,
            "has_io_expansion": payload.has_io_expansion,
            "expansion_io_inputs": payload.expansion_io_inputs,
            "expansion_io_outputs": payload.expansion_io_outputs,
        },
        entry_type=entry_type,
    )
    db.add(history_item)
    db.commit()

    return result


@router.get("/history", response_model=ChatHistoryListResponse)
async def list_chat_history(
    request: Request,
    db: DbSession,
    limit: int = 50,
    offset: int = 0,
) -> ChatHistoryListResponse:
    user = get_current_user(request, db)

    items = list(
        db.scalars(
            select(ChatHistory)
            .where(ChatHistory.user_id == user.id)
            .order_by(ChatHistory.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
    )
    from sqlalchemy import func as sa_func  # noqa: PLC0415

    count = (
        db.scalar(
            select(sa_func.count())
            .select_from(ChatHistory)
            .where(ChatHistory.user_id == user.id)
        )
        or 0
    )

    return ChatHistoryListResponse(
        items=[_serialize_history_item(item) for item in items],
        total=count,
    )


@router.delete("/history/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_chat_history_item(
    item_id: int,
    request: Request,
    db: DbSession,
) -> None:
    user = get_current_user(request, db)

    item = db.scalar(
        select(ChatHistory).where(
            ChatHistory.id == item_id,
            ChatHistory.user_id == user.id,
        )
    )
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Item no encontrado."
        )

    db.delete(item)
    db.commit()
