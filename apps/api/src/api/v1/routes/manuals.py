from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from fastapi.responses import Response
from sqlalchemy import delete, select

from src.api.v1.deps import DbSession, get_current_admin_user
from src.api.v1.schemas.manuals import (
    DocumentLanguage,
    ManualListResponse,
    ManualReviewSummaryListResponse,
    ManualReviewSummaryResponse,
    ManualResponse,
    ManualUpdateRequest,
    StaleProcessingResult,
)
from src.db.models import (
    Manual,
    ManualChunk,
    ManualChunkReview,
    ManualReviewSummary,
    User,
)
from src.services.manuals import (
    ManualStorageError,
    ManualStorageService,
    build_storage_key,
    get_manual_storage_service,
    serialize_manual,
)

router = APIRouter()


def normalize_optional_text(value: str | None) -> str | None:
    if value is None:
        return None

    normalized = value.strip()
    return normalized or None


def get_manual_or_404(db_session: DbSession, manual_id: int) -> Manual:
    manual = db_session.get(Manual, manual_id)
    if not manual:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No se encontro el manual solicitado.",
        )
    return manual


def find_duplicate_manual_by_sha256(
    db_session: DbSession,
    storage_service: ManualStorageService,
    content: bytes,
) -> Manual | None:
    incoming_hash = hashlib.sha256(content).hexdigest()
    candidates = list(
        db_session.scalars(
            select(Manual)
            .where(Manual.size_bytes == len(content))
            .order_by(Manual.created_at.desc(), Manual.id.desc())
        )
    )

    for candidate in candidates:
        try:
            existing_content = storage_service.download_manual(candidate.storage_key)
        except ManualStorageError:
            continue

        existing_hash = hashlib.sha256(existing_content).hexdigest()
        if existing_hash == incoming_hash:
            return candidate

    return None


def ensure_manual_sha256(
    db_session: DbSession,
    storage_service: ManualStorageService,
    manual: Manual,
) -> None:
    if manual.sha256:
        return

    try:
        content = storage_service.download_manual(manual.storage_key)
    except ManualStorageError:
        return

    manual.sha256 = hashlib.sha256(content).hexdigest()
    db_session.add(manual)


def reset_manual_ingestion_state(db_session: DbSession, manual: Manual) -> None:
    db_session.execute(delete(ManualChunk).where(ManualChunk.manual_id == manual.id))
    db_session.execute(
        delete(ManualChunkReview).where(ManualChunkReview.manual_id == manual.id)
    )
    db_session.execute(
        delete(ManualReviewSummary).where(ManualReviewSummary.manual_id == manual.id)
    )

    manual.status = "pending"
    manual.chunk_count = 0
    manual.last_error = None
    manual.processing_started_at = None
    manual.indexed_at = None
    db_session.add(manual)


def serialize_manual_review_summary(
    summary: ManualReviewSummary,
) -> ManualReviewSummaryResponse:
    return ManualReviewSummaryResponse(
        manual_id=summary.manual_id,
        initial_chunk_count=summary.initial_chunk_count,
        final_chunk_count=summary.final_chunk_count,
        reviewed_count=summary.reviewed_count,
        skipped_count=summary.skipped_count,
        error_count=summary.error_count,
        merge_actions=summary.merge_actions,
        split_actions=summary.split_actions,
        keep_actions=summary.keep_actions,
        regenerate_actions=summary.regenerate_actions,
        applied_autofixes=summary.applied_autofixes,
        avg_coherence_score=summary.avg_coherence_score,
        avg_completeness_score=summary.avg_completeness_score,
        avg_boundary_quality_score=summary.avg_boundary_quality_score,
        estimated_input_tokens=summary.estimated_input_tokens,
        estimated_output_tokens=summary.estimated_output_tokens,
        estimated_cost_usd=summary.estimated_cost_usd,
        updated_at=summary.updated_at,
    )


@router.get("", response_model=ManualListResponse)
async def list_manuals(
    db_session: DbSession,
    _: User = Depends(get_current_admin_user),
    storage_service: ManualStorageService = Depends(get_manual_storage_service),
) -> ManualListResponse:
    manuals = list(
        db_session.scalars(
            select(Manual).order_by(Manual.created_at.desc(), Manual.id.desc())
        )
    )

    updated_any = False
    for manual in manuals:
        previous_hash = manual.sha256
        ensure_manual_sha256(db_session, storage_service, manual)
        if not previous_hash and manual.sha256:
            updated_any = True

    if updated_any:
        db_session.commit()

    return ManualListResponse(
        items=[serialize_manual(manual) for manual in manuals], total=len(manuals)
    )


@router.get("/review-summaries", response_model=ManualReviewSummaryListResponse)
async def list_manual_review_summaries(
    db_session: DbSession,
    _: User = Depends(get_current_admin_user),
) -> ManualReviewSummaryListResponse:
    summaries = list(
        db_session.scalars(
            select(ManualReviewSummary).order_by(ManualReviewSummary.updated_at.desc())
        )
    )
    return ManualReviewSummaryListResponse(
        items=[serialize_manual_review_summary(summary) for summary in summaries],
        total=len(summaries),
    )


@router.get("/{manual_id}", response_model=ManualResponse)
async def get_manual(
    manual_id: int,
    db_session: DbSession,
    _: User = Depends(get_current_admin_user),
    storage_service: ManualStorageService = Depends(get_manual_storage_service),
) -> ManualResponse:
    manual = get_manual_or_404(db_session, manual_id)
    previous_hash = manual.sha256
    ensure_manual_sha256(db_session, storage_service, manual)
    if not previous_hash and manual.sha256:
        db_session.commit()
        db_session.refresh(manual)
    return serialize_manual(manual)


@router.get("/{manual_id}/file")
async def open_manual_file(
    manual_id: int,
    db_session: DbSession,
    _: User = Depends(get_current_admin_user),
    storage_service: ManualStorageService = Depends(get_manual_storage_service),
) -> Response:
    manual = get_manual_or_404(db_session, manual_id)

    try:
        content = storage_service.download_manual(manual.storage_key)
    except ManualStorageError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc

    filename = manual.original_filename.replace('"', "")
    return Response(
        content=content,
        media_type=manual.content_type,
        headers={
            "Content-Disposition": f'inline; filename="{filename}"',
        },
    )


@router.post("", response_model=ManualResponse, status_code=status.HTTP_201_CREATED)
async def upload_manual(
    title: Annotated[str, Form(min_length=3, max_length=255)],
    file: Annotated[UploadFile, File(...)],
    db_session: DbSession,
    current_user: User = Depends(get_current_admin_user),
    storage_service: ManualStorageService = Depends(get_manual_storage_service),
    robot_model: Annotated[str | None, Form(max_length=120)] = None,
    controller_version: Annotated[str | None, Form(max_length=80)] = None,
    document_language: Annotated[DocumentLanguage, Form()] = "es",
    notes: Annotated[str | None, Form(max_length=1000)] = None,
    as_new_version: Annotated[bool, Form()] = False,
) -> ManualResponse:
    normalized_title = title.strip()
    if len(normalized_title) < 3:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="El titulo del manual debe contener al menos 3 caracteres utiles.",
        )

    original_filename = (file.filename or "").strip()
    if not original_filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Solo se permiten archivos PDF.",
        )

    content = await file.read()
    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El archivo PDF no puede estar vacio.",
        )

    content_sha256 = hashlib.sha256(content).hexdigest()

    duplicate_manual = find_duplicate_manual_by_sha256(
        db_session, storage_service, content
    )
    if duplicate_manual and not as_new_version:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Ya existe un manual con el mismo SHA-256 "
                f"(manual #{duplicate_manual.id}). "
                "Confirma 'cargar como nueva version' para continuar o cancela la carga."
            ),
        )

    content_type = file.content_type or "application/pdf"
    storage_key = build_storage_key(original_filename)

    normalized_notes = normalize_optional_text(notes)
    if duplicate_manual and as_new_version:
        version_note = (
            f"Nueva version de manual #{duplicate_manual.id} (SHA-256 duplicado)."
        )
        normalized_notes = (
            f"{normalized_notes} {version_note}".strip()
            if normalized_notes
            else version_note
        )

    try:
        storage_service.upload_manual(content, storage_key, content_type)
    except ManualStorageError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc

    manual = Manual(
        title=normalized_title,
        original_filename=original_filename,
        storage_key=storage_key,
        content_type=content_type,
        size_bytes=len(content),
        sha256=content_sha256,
        status="pending",
        chunk_count=0,
        robot_model=normalize_optional_text(robot_model),
        controller_version=normalize_optional_text(controller_version),
        document_language=document_language,
        notes=normalized_notes,
        last_error=None,
        processing_started_at=None,
        uploaded_by_user_id=current_user.id,
        uploaded_by_email=current_user.email,
        indexed_at=None,
    )
    db_session.add(manual)
    db_session.commit()
    db_session.refresh(manual)

    return serialize_manual(manual)


@router.put("/{manual_id}", response_model=ManualResponse)
async def update_manual(
    manual_id: int,
    payload: ManualUpdateRequest,
    db_session: DbSession,
    _: User = Depends(get_current_admin_user),
) -> ManualResponse:
    manual = get_manual_or_404(db_session, manual_id)

    normalized_title = payload.title.strip()
    if len(normalized_title) < 3:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="El titulo del manual debe contener al menos 3 caracteres utiles.",
        )

    manual.title = normalized_title
    manual.notes = normalize_optional_text(payload.notes)

    db_session.add(manual)
    db_session.commit()
    db_session.refresh(manual)
    return serialize_manual(manual)


@router.post("/{manual_id}/retry", response_model=ManualResponse)
async def retry_manual(
    manual_id: int,
    db_session: DbSession,
    _: User = Depends(get_current_admin_user),
) -> ManualResponse:
    manual = get_manual_or_404(db_session, manual_id)

    if manual.status == "processing":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El manual sigue en analisis. Espera a que finalice o falle para reintentar.",
        )

    if manual.status == "indexed":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El manual ya esta indexado. Usa reingesta solo para manuales con error o atascados.",
        )

    reset_manual_ingestion_state(db_session, manual)
    db_session.commit()
    db_session.refresh(manual)
    return serialize_manual(manual)


@router.post("/cleanup-stale-processing", response_model=StaleProcessingResult)
async def cleanup_stale_processing(
    db_session: DbSession,
    _: User = Depends(get_current_admin_user),
    older_than_minutes: int = Query(
        default=10,
        ge=1,
        le=1440,
        description="Tiempo minimo en minutos que un manual debe llevar en 'processing' para ser reencolado.",
    ),
) -> StaleProcessingResult:
    threshold = datetime.now(UTC) - timedelta(minutes=older_than_minutes)

    stale_manuals = list(
        db_session.scalars(
            select(Manual)
            .where(Manual.status == "processing")
            .where(Manual.updated_at < threshold)
        )
    )

    if not stale_manuals:
        return StaleProcessingResult(recovered=0, manual_ids=[])

    for manual in stale_manuals:
        manual.status = "pending"
        manual.chunk_count = 0
        manual.processing_started_at = None
        manual.indexed_at = None
        manual.last_error = f"Reencolado por limpieza de administrador (umbral: {older_than_minutes}min)."
        db_session.add(manual)

    db_session.commit()
    return StaleProcessingResult(
        recovered=len(stale_manuals),
        manual_ids=[m.id for m in stale_manuals],
    )


@router.delete("/{manual_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_manual(
    manual_id: int,
    db_session: DbSession,
    _: User = Depends(get_current_admin_user),
    storage_service: ManualStorageService = Depends(get_manual_storage_service),
) -> Response:
    manual = get_manual_or_404(db_session, manual_id)

    try:
        storage_service.delete_manual(manual.storage_key)
    except ManualStorageError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc

    reset_manual_ingestion_state(db_session, manual)
    db_session.delete(manual)
    db_session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
