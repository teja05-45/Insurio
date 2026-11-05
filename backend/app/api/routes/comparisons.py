"""Structured policy comparison routes."""

import uuid

from fastapi import APIRouter, Query, status

from app.api.deps import CurrentUser, DbSession
from app.core.errors import AppError
from app.repositories import policies as policy_repo
from app.schemas.common import MessageResponse, Page
from app.schemas.documents import ComparisonCreateRequest, ComparisonOut
from app.services import comparison as comparison_service

router = APIRouter(prefix="/comparisons", tags=["comparisons"])


@router.post("", response_model=ComparisonOut, status_code=status.HTTP_201_CREATED)
def create_comparison(
    payload: ComparisonCreateRequest, user: CurrentUser, db: DbSession
) -> ComparisonOut:
    comparison = comparison_service.create_comparison(db, user, payload.document_ids, payload.title)
    return ComparisonOut.model_validate(comparison_service.serialize(comparison))


@router.get("", response_model=Page[ComparisonOut])
def list_comparisons(
    user: CurrentUser,
    db: DbSession,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> Page[ComparisonOut]:
    items, total = policy_repo.list_comparisons(db, user.id, page=page, page_size=page_size)
    return Page(
        items=[ComparisonOut.model_validate(comparison_service.serialize(item)) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{comparison_id}", response_model=ComparisonOut)
def get_comparison(comparison_id: uuid.UUID, user: CurrentUser, db: DbSession) -> ComparisonOut:
    comparison = policy_repo.get_comparison_owned(db, comparison_id, user.id)
    if comparison is None:
        raise AppError("Comparison not found.", code="comparison_not_found", status_code=404)
    return ComparisonOut.model_validate(comparison_service.serialize(comparison))


@router.delete("/{comparison_id}", response_model=MessageResponse)
def delete_comparison(
    comparison_id: uuid.UUID, user: CurrentUser, db: DbSession
) -> MessageResponse:
    comparison = policy_repo.get_comparison_owned(db, comparison_id, user.id)
    if comparison is None:
        raise AppError("Comparison not found.", code="comparison_not_found", status_code=404)
    policy_repo.delete_comparison(db, comparison)
    db.commit()
    return MessageResponse(message="Comparison deleted.")
