"""Deterministic, evidence-backed policy comparison."""

import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.ai.extraction import FIELDS, normalize_for_match
from app.core.errors import AppError
from app.models.user import User
from app.repositories import documents as document_repo
from app.repositories import policies as policy_repo


def build_payload(documents: list[Any], insights: list[Any]) -> dict[str, Any]:
    fields: list[dict[str, Any]] = []
    for spec in FIELDS:
        values = []
        found_values: set[str] = set()
        statuses: set[str] = set()
        missing_in: list[str] = []
        for document, insight in zip(documents, insights, strict=True):
            field = next(
                (item for item in insight.payload.get("fields", []) if item.get("key") == spec.key),
                None,
            )
            if field is None or field.get("status") == "missing":
                statuses.add("missing")
                missing_in.append(str(document.id))
                values.append(
                    {
                        "document_id": str(document.id),
                        "value": "",
                        "status": "missing",
                        "page": None,
                        "quote": "",
                        "confidence": 0.0,
                    }
                )
                continue
            statuses.add(field.get("status", "found"))
            if field.get("status") == "found":
                found_values.add(normalize_for_match(str(field.get("value", ""))))
            values.append(
                {
                    "document_id": str(document.id),
                    "value": field.get("value", ""),
                    "status": field.get("status", "found"),
                    "page": field.get("page"),
                    "quote": field.get("quote", ""),
                    "confidence": field.get("confidence", 0.0),
                }
            )

        differs = len(found_values) > 1 or "missing" in statuses
        # Ignore fields absent from every document: they are not a comparison.
        if len(missing_in) == len(documents):
            continue
        fields.append(
            {
                "key": spec.key,
                "label": spec.label,
                "category": spec.category,
                "values": values,
                "differs": differs,
                "missing_in": missing_in,
            }
        )

    return {
        "documents": [
            {"id": str(document.id), "filename": document.original_filename}
            for document in documents
        ],
        "fields": fields,
        "summary": {
            "fields_compared": len(fields),
            "differences": sum(1 for field in fields if field["differs"]),
            "fields_missing_somewhere": sum(1 for field in fields if field["missing_in"]),
        },
    }


def create_comparison(
    db: Session, user: User, document_ids: list[uuid.UUID], title: str | None
) -> Any:
    unique_ids: list[uuid.UUID] = []
    for document_id in document_ids:
        if document_id not in unique_ids:
            unique_ids.append(document_id)
    if len(unique_ids) < 2:
        raise AppError(
            "Select at least two different policies to compare.",
            code="comparison_needs_two",
            status_code=400,
        )
    if len(unique_ids) > 5:
        raise AppError(
            "You can compare up to five policies.", code="comparison_too_many", status_code=400
        )

    documents = []
    insights = []
    for document_id in unique_ids:
        document = document_repo.get_owned(db, document_id, user.id)
        if document is None:
            raise AppError(
                "One or more documents were not found.",
                code="document_not_found",
                status_code=404,
                details={"document_id": str(document_id)},
            )
        if document.status != "ready":
            raise AppError(
                "Every document must finish processing before comparison.",
                code="document_not_ready",
                status_code=409,
                details={"document_id": str(document_id), "status": document.status},
            )
        insight = policy_repo.get_insight(db, document.id)
        if insight is None:
            raise AppError(
                "Insights are not available for one or more documents.",
                code="insights_missing",
                status_code=409,
                details={"document_id": str(document.id)},
            )
        documents.append(document)
        insights.append(insight)

    payload = build_payload(documents, insights)
    default_title = " vs ".join(
        document.original_filename.rsplit(".", 1)[0][:60] for document in documents
    )
    comparison = policy_repo.create_comparison(
        db,
        user_id=user.id,
        title=title or default_title,
        document_ids=[str(document.id) for document in documents],
        payload=payload,
    )
    db.commit()
    db.refresh(comparison)
    return comparison


def serialize(comparison: Any) -> dict[str, Any]:
    return {
        "id": comparison.id,
        "title": comparison.title,
        "document_ids": [uuid.UUID(value) for value in comparison.document_ids],
        "documents": comparison.payload.get("documents", []),
        "fields": comparison.payload.get("fields", []),
        "summary": comparison.payload.get("summary", {}),
        "created_at": comparison.created_at,
    }
