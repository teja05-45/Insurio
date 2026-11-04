"""Persistence access for users and refresh sessions."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import User, UserSession


def get_by_email(db: Session, email: str) -> User | None:
    return db.scalar(select(User).where(User.email == email.lower()))


def get_by_id(db: Session, user_id: uuid.UUID) -> User | None:
    return db.get(User, user_id)


def create(db: Session, *, email: str, hashed_password: str, full_name: str) -> User:
    user = User(email=email.lower(), hashed_password=hashed_password, full_name=full_name)
    db.add(user)
    db.flush()
    return user


def touch_login(db: Session, user: User) -> None:
    user.last_login_at = datetime.now(UTC)
    db.add(user)


def create_session(
    db: Session,
    *,
    user_id: uuid.UUID,
    token_hash: str,
    expires_at: datetime,
    user_agent: str,
    ip_address: str,
) -> UserSession:
    session = UserSession(
        user_id=user_id,
        token_hash=token_hash,
        expires_at=expires_at,
        user_agent=user_agent[:300],
        ip_address=ip_address[:64],
        created_at=datetime.now(UTC),
    )
    db.add(session)
    db.flush()
    return session


def get_session_by_hash(db: Session, token_hash: str) -> UserSession | None:
    return db.scalar(select(UserSession).where(UserSession.token_hash == token_hash))


def revoke_session(db: Session, session: UserSession) -> None:
    if session.revoked_at is None:
        session.revoked_at = datetime.now(UTC)
        db.add(session)


def list_active(db: Session, user_id: uuid.UUID) -> list[UserSession]:
    now = datetime.now(UTC)
    return list(
        db.scalars(
            select(UserSession)
            .where(
                UserSession.user_id == user_id,
                UserSession.revoked_at.is_(None),
                UserSession.expires_at > now,
            )
            .order_by(UserSession.created_at.desc())
        )
    )


def revoke_all_sessions(db: Session, user_id: uuid.UUID, except_id: uuid.UUID | None = None) -> None:
    now = datetime.now(UTC)
    stmt = select(UserSession).where(
        UserSession.user_id == user_id, UserSession.revoked_at.is_(None)
    )
    for session in db.scalars(stmt):
        if except_id is not None and session.id == except_id:
            continue
        session.revoked_at = now
        db.add(session)
