"""Persistence access for policy insights and comparisons."""

import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.policy import PolicyComparison, PolicyInsight


def document_ids_with_insights(db: Session, document_ids: list[uuid.UUID]) -> set[uuid.UUID]:
    if not document_ids:
        return set()
    return set(
        db.scalars(
            select(PolicyInsight.document_id).where(PolicyInsight.document_id.in_(document_ids))
        )
    )


def get_insight(db: Session, document_id: uuid.UUID) -> PolicyInsight | None:
    return db.scalar(select(PolicyInsight).where(PolicyInsight.document_id == document_id))


def upsert_insight(
    db: Session,
    *,
    document_id: uuid.UUID,
    payload: dict[str, Any],
    method: str,
    llm_model: str | None,
) -> PolicyInsight:
    insight = get_insight(db, document_id)
    if insight is None:
        insight = PolicyInsight(
            document_id=document_id,
            payload=payload,
            extraction_method=method,
            llm_model=llm_model,
        )
    else:
        insight.payload = payload
        insight.extraction_method = method
        insight.llm_model = llm_model
    db.add(insight)
    return insight


def create_comparison(
    db: Session,
    *,
    user_id: uuid.UUID,
    title: str,
    document_ids: list[str],
    payload: dict[str, Any],
) -> PolicyComparison:
    comparison = PolicyComparison(
        user_id=user_id, title=title[:200], document_ids=document_ids, payload=payload
    )
    db.add(comparison)
    db.flush()
    return comparison


def get_comparison_owned(
    db: Session, comparison_id: uuid.UUID, user_id: uuid.UUID
) -> PolicyComparison | None:
    return db.scalar(
        select(PolicyComparison).where(
            PolicyComparison.id == comparison_id, PolicyComparison.user_id == user_id
        )
    )


def list_comparisons(
    db: Session, user_id: uuid.UUID, *, page: int, page_size: int
) -> tuple[list[PolicyComparison], int]:
    total = (
        db.scalar(
            select(func.count())
            .select_from(PolicyComparison)
            .where(PolicyComparison.user_id == user_id)
        )
        or 0
    )
    items = list(
        db.scalars(
            select(PolicyComparison)
            .where(PolicyComparison.user_id == user_id)
            .order_by(PolicyComparison.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    )
    return items, total


def delete_comparison(db: Session, comparison: PolicyComparison) -> None:
    db.delete(comparison)


def count_for_user(db: Session, user_id: uuid.UUID) -> int:
    return (
        db.scalar(
            select(func.count())
            .select_from(PolicyComparison)
            .where(PolicyComparison.user_id == user_id)
        )
        or 0
    )
