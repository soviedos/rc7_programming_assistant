import json
from collections.abc import Generator

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy import delete, func as sa_func, select

from src.api.v1.deps import DbSession, get_current_user
from src.api.v1.schemas.chat import (
    ChatHistoryItemResponse,
    ChatHistoryListResponse,
    ChatRequest,
    ReferenceItem,
)
from src.core.config import settings
from src.db.models.chat_history import ChatHistory
from src.services.audit_service import log_event
from src.services.chat.service import generate_rag_response, stream_rag_response
from src.services.settings.service import get_setting_value

router = APIRouter()

_SSE_HEADERS = {
    "Cache-Control": "no-cache",
    "X-Accel-Buffering": "no",
}


def _save_history_and_prune(
    db,
    user,
    payload: ChatRequest,
    summary: str,
    pac_code: str,
    references: list,
) -> None:
    entry_type = "code" if pac_code.strip() else "troubleshooting"
    history_item = ChatHistory(
        user_id=user.id,
        prompt=payload.prompt,
        summary=summary,
        pac_code=pac_code,
        references=references,
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

    max_entries = int(get_setting_value(db, "history_max_entries", "50"))
    keep_ids = (
        select(ChatHistory.id)
        .where(ChatHistory.user_id == user.id)
        .order_by(ChatHistory.created_at.desc())
        .limit(max_entries)
        .scalar_subquery()
    )
    db.execute(
        delete(ChatHistory)
        .where(ChatHistory.user_id == user.id)
        .where(ChatHistory.id.not_in(keep_ids))
    )
    db.commit()


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


@router.post("/generate")
def generate_code(
    request: Request,
    payload: ChatRequest,
    db: DbSession,
) -> StreamingResponse:
    user = get_current_user(request, db)  # raises 401 if not authenticated
    ip = request.client.host if request.client else None

    if not settings.enable_streaming:
        # Fallback: run the pipeline synchronously and emit a single done event
        try:
            result = generate_rag_response(db, payload)
        except RuntimeError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=str(exc),
            ) from exc
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Error inesperado al procesar la consulta: {exc}",
            ) from exc

        refs = [{"title": r.title, "page": r.page} for r in result.references]
        _save_history_and_prune(
            db, user, payload, result.summary, result.pac_code, refs
        )
        entry_type = "code" if result.pac_code.strip() else "troubleshooting"
        log_event(
            db,
            "CHAT_QUERY",
            "Consulta de chat procesada",
            actor_id=user.id,
            actor_email=user.email,
            resource_type="chat",
            metadata={
                "robot_type": payload.robot_type,
                "entry_type": entry_type,
                "references_count": len(result.references),
            },
            ip_address=ip,
        )

        def _single() -> Generator[str, None, None]:
            yield f"data: {json.dumps({'type': 'done', 'summary': result.summary, 'pac_code': result.pac_code, 'references': refs})}\n\n"

        return StreamingResponse(
            _single(), media_type="text/event-stream", headers=_SSE_HEADERS
        )

    # ── Streaming path ────────────────────────────────────────────
    def _stream() -> Generator[str, None, None]:
        summary = ""
        pac_code = ""
        references: list = []
        entry_type = "troubleshooting"
        try:
            for sse_line in stream_rag_response(db, payload):
                yield sse_line
                # Intercept the done event to capture parsed fields for history
                if sse_line.startswith("data: "):
                    try:
                        evt = json.loads(sse_line[6:].strip())
                        if evt.get("type") == "done":
                            summary = evt.get("summary", "")
                            pac_code = evt.get("pac_code", "")
                            references = evt.get("references", [])
                            entry_type = (
                                "code" if pac_code.strip() else "troubleshooting"
                            )
                    except Exception:
                        pass
        except Exception as exc:
            # Audit the failure (best-effort) so a mid-stream error is observable
            # even though no history entry is persisted for a partial response.
            try:
                log_event(
                    db,
                    "CHAT_QUERY_FAILED",
                    "Pipeline de chat falló durante el streaming",
                    actor_id=user.id,
                    actor_email=user.email,
                    resource_type="chat",
                    metadata={"robot_type": payload.robot_type, "error": str(exc)[:300]},
                    ip_address=ip,
                )
            except Exception:
                pass
            yield f"data: {json.dumps({'type': 'error', 'message': 'Pipeline fallido'})}\n\n"
            return

        # After stream finishes: persist history and audit
        try:
            _save_history_and_prune(db, user, payload, summary, pac_code, references)
            log_event(
                db,
                "CHAT_QUERY",
                "Consulta de chat procesada",
                actor_id=user.id,
                actor_email=user.email,
                resource_type="chat",
                metadata={
                    "robot_type": payload.robot_type,
                    "entry_type": entry_type,
                    "references_count": len(references),
                },
                ip_address=ip,
            )
        except Exception:
            pass  # Never fail the response due to persistence errors

    return StreamingResponse(
        _stream(), media_type="text/event-stream", headers=_SSE_HEADERS
    )


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
