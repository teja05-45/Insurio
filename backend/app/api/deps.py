"""Shared FastAPI dependencies: authentication and ownership checks."""

import uuid
from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.errors import AppError
from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.document import Document
from app.models.user import User
from app.repositories import documents as document_repo
from app.repositories import users as user_repo

bearer_scheme = HTTPBearer(auto_error=False, description="JWT access token")

DbSession = Annotated[Session, Depends(get_db)]
SettingsDep = Annotated[Settings, Depends(get_settings)]


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    db: DbSession,
    settings: SettingsDep,
) -> User:
    if credentials is None or not credentials.credentials:
        raise AppError("Authentication required.", code="not_authenticated", status_code=401)
    payload = decode_access_token(credentials.credentials, settings)
    try:
        user_id = uuid.UUID(str(payload["sub"]))
    except (ValueError, KeyError) as exc:
        raise AppError("Invalid authentication token.", code="invalid_token", status_code=401) from exc
    user = user_repo.get_by_id(db, user_id)
    if user is None or not user.is_active:
        raise AppError("Account is unavailable.", code="account_unavailable", status_code=401)
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def get_owned_document(
    document_id: uuid.UUID,
    db: DbSession,
    user: CurrentUser,
) -> Document:
    document = document_repo.get_owned(db, document_id, user.id)
    if document is None:
        # 404 rather than 403 so document existence is not disclosed.
        raise AppError("Document not found.", code="document_not_found", status_code=404)
    return document


OwnedDocument = Annotated[Document, Depends(get_owned_document)]


def client_meta(request: Request) -> dict[str, str]:
    return {
        "user_agent": request.headers.get("user-agent", "")[:300],
        "ip_address": (request.client.host if request.client else "")[:64],
    }
