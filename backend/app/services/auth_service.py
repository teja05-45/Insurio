"""Authentication and account business logic."""

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.errors import AppError
from app.core.security import (
    create_access_token,
    hash_password,
    hash_refresh_token,
    new_refresh_token,
    new_reset_token,
    verify_password,
)
from app.models.user import PasswordResetToken, User, UserSession
from app.repositories import users as user_repo
from app.schemas.auth import AuthResponse, LoginRequest, RegisterRequest, UserOut


def _auth_response(
    db: Session,
    user: User,
    settings: Settings,
    *,
    user_agent: str = "",
    ip_address: str = "",
) -> AuthResponse:
    access_token = create_access_token(str(user.id), settings)
    refresh_token = new_refresh_token()
    user_repo.create_session(
        db,
        user_id=user.id,
        token_hash=hash_refresh_token(refresh_token),
        expires_at=datetime.now(UTC) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        user_agent=user_agent,
        ip_address=ip_address,
    )
    db.commit()
    db.refresh(user)
    return AuthResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=UserOut.model_validate(user),
    )


def register(
    db: Session, payload: RegisterRequest, *, user_agent: str = "", ip_address: str = ""
) -> AuthResponse:
    settings = get_settings()
    if user_repo.get_by_email(db, payload.email):
        raise AppError(
            "An account with this email already exists.",
            code="email_taken",
            status_code=409,
        )
    user = user_repo.create(
        db,
        email=payload.email,
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name.strip(),
    )
    user_repo.touch_login(db, user)
    return _auth_response(
        db, user, settings, user_agent=user_agent, ip_address=ip_address
    )


def login(
    db: Session, payload: LoginRequest, *, user_agent: str = "", ip_address: str = ""
) -> AuthResponse:
    settings = get_settings()
    user = user_repo.get_by_email(db, payload.email)
    if user is None or not verify_password(payload.password, user.hashed_password):
        # Identical response for unknown email and wrong password.
        raise AppError(
            "Email or password is incorrect.",
            code="invalid_credentials",
            status_code=401,
        )
    if not user.is_active:
        raise AppError("This account is disabled.", code="account_disabled", status_code=403)
    user_repo.touch_login(db, user)
    return _auth_response(
        db, user, settings, user_agent=user_agent, ip_address=ip_address
    )


def rotate_refresh_token(db: Session, raw_token: str, settings: Settings) -> AuthResponse:
    token_hash = hash_refresh_token(raw_token)
    session = user_repo.get_session_by_hash(db, token_hash)
    now = datetime.now(UTC)
    if session is None or session.revoked_at is not None:
        raise AppError("Session is no longer valid.", code="invalid_refresh", status_code=401)
    expires_at = session.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    if expires_at <= now:
        user_repo.revoke_session(db, session)
        db.commit()
        raise AppError("Session has expired. Please sign in again.", code="expired_refresh", status_code=401)

    user = user_repo.get_by_id(db, session.user_id)
    if user is None or not user.is_active:
        raise AppError("Session is no longer valid.", code="invalid_refresh", status_code=401)

    user_repo.revoke_session(db, session)
    db.flush()
    return _auth_response(db, user, settings)


def logout(db: Session, raw_token: str) -> None:
    session = user_repo.get_session_by_hash(db, hash_refresh_token(raw_token))
    if session is not None:
        user_repo.revoke_session(db, session)
        db.commit()


def request_password_reset(db: Session, email: str) -> str | None:
    """Always succeeds from the caller's perspective to prevent account enumeration.

    Returns the raw reset token only outside production; there is no email
    delivery integration in this build (documented limitation).
    """
    settings = get_settings()
    user = user_repo.get_by_email(db, email)
    if user is None:
        return None

    raw_token = new_reset_token()
    db.add(
        PasswordResetToken(
            user_id=user.id,
            token_hash=hash_refresh_token(raw_token),
            expires_at=datetime.now(UTC)
            + timedelta(minutes=settings.PASSWORD_RESET_EXPIRE_MINUTES),
            created_at=datetime.now(UTC),
        )
    )
    db.commit()
    return None if settings.is_production else raw_token


def reset_password(db: Session, raw_token: str, new_password: str) -> None:
    token_hash = hash_refresh_token(raw_token)
    now = datetime.now(UTC)
    record = db.scalar(
        select(PasswordResetToken).where(PasswordResetToken.token_hash == token_hash)
    )
    if record is None or record.used_at is not None:
        raise AppError(
            "This reset link is invalid or has already been used.",
            code="invalid_reset",
            status_code=400,
        )
    expires_at = record.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    if expires_at <= now:
        raise AppError("This reset link has expired.", code="expired_reset", status_code=400)

    user = user_repo.get_by_id(db, record.user_id)
    if user is None:
        raise AppError("This reset link is invalid.", code="invalid_reset", status_code=400)

    user.hashed_password = hash_password(new_password)
    record.used_at = now
    db.add(user)
    db.add(record)
    user_repo.revoke_all_sessions(db, user.id)
    db.commit()


def change_password(db: Session, user: User, current: str, new: str) -> None:
    if not verify_password(current, user.hashed_password):
        raise AppError("Current password is incorrect.", code="invalid_password", status_code=400)
    if current == new:
        raise AppError("New password must differ from the current password.", code="same_password", status_code=400)
    user.hashed_password = hash_password(new)
    db.add(user)
    user_repo.revoke_all_sessions(db, user.id)
    db.commit()


def update_profile(db: Session, user: User, full_name: str) -> UserOut:
    user.full_name = full_name.strip()
    db.add(user)
    db.commit()
    db.refresh(user)
    return UserOut.model_validate(user)


def delete_account(db: Session, user: User, password: str) -> None:
    if not verify_password(password, user.hashed_password):
        raise AppError("Password is incorrect.", code="invalid_password", status_code=400)
    db.delete(user)
    db.commit()


def get_user(db: Session, user_id: uuid.UUID) -> User:
    user = user_repo.get_by_id(db, user_id)
    if user is None:
        raise AppError("User not found.", code="not_found", status_code=404)
    return user


def list_active_sessions(db: Session, user_id: uuid.UUID) -> list[UserSession]:
    return user_repo.list_active(db, user_id)
