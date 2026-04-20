from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select

from src.api.v1.deps import DbSession, get_current_admin_user
from src.api.v1.schemas.manuals import DocumentLanguage, ManualListResponse, ManualResponse
from src.db.models import Manual, User
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


@router.get("", response_model=ManualListResponse)
async def list_manuals(
    db_session: DbSession,
    _: User = Depends(get_current_admin_user),
) -> ManualListResponse:
    manuals = list(
        db_session.scalars(select(Manual).order_by(Manual.created_at.desc(), Manual.id.desc()))
    )
    return ManualListResponse(items=[serialize_manual(manual) for manual in manuals], total=len(manuals))


@router.get("/{manual_id}", response_model=ManualResponse)
async def get_manual(
    manual_id: int,
    db_session: DbSession,
    _: User = Depends(get_current_admin_user),
) -> ManualResponse:
    manual = db_session.get(Manual, manual_id)
    if not manual:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No se encontro el manual solicitado.",
        )

    return serialize_manual(manual)


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

    content_type = file.content_type or "application/pdf"
    storage_key = build_storage_key(original_filename)

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
        status="pending",
        chunk_count=0,
        robot_model=normalize_optional_text(robot_model),
        controller_version=normalize_optional_text(controller_version),
        document_language=document_language,
        notes=normalize_optional_text(notes),
        last_error=None,
        uploaded_by_user_id=current_user.id,
        uploaded_by_email=current_user.email,
        indexed_at=None,
    )
    db_session.add(manual)
    db_session.commit()
    db_session.refresh(manual)

    return serialize_manual(manual)
