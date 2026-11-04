"""Authentication and account routes."""

from fastapi import APIRouter, Depends, Request, status

from app.api.deps import CurrentUser, DbSession, client_meta
from app.core.config import get_settings
from app.core.rate_limit import rate_limit
from app.schemas.auth import (
    AuthResponse,
    ChangePasswordRequest,
    DeleteAccountRequest,
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    LoginRequest,
    LogoutRequest,
    ProfileUpdateRequest,
    RefreshRequest,
    RegisterRequest,
    ResetPasswordRequest,
    SessionOut,
    UserOut,
)
from app.schemas.common import MessageResponse
from app.services import auth_service
from app.services.auth_service import list_active_sessions

router = APIRouter(prefix="/auth", tags=["auth"])

_settings = get_settings()
auth_limiter = rate_limit("auth", _settings.AUTH_RATE_LIMIT_PER_MINUTE)


@router.post(
    "/register",
    response_model=AuthResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(auth_limiter)],
)
def register(payload: RegisterRequest, request: Request, db: DbSession) -> AuthResponse:
    return auth_service.register(db, payload, **client_meta(request))


@router.post("/login", response_model=AuthResponse, dependencies=[Depends(auth_limiter)])
def login(payload: LoginRequest, request: Request, db: DbSession) -> AuthResponse:
    return auth_service.login(db, payload, **client_meta(request))


@router.post("/refresh", response_model=AuthResponse, dependencies=[Depends(auth_limiter)])
def refresh(payload: RefreshRequest, request: Request, db: DbSession) -> AuthResponse:
    return auth_service.rotate_refresh_token(db, payload.refresh_token, get_settings())


@router.post("/logout", response_model=MessageResponse)
def logout(payload: LogoutRequest, db: DbSession) -> MessageResponse:
    auth_service.logout(db, payload.refresh_token)
    return MessageResponse(message="Signed out.")


@router.post(
    "/forgot-password",
    response_model=ForgotPasswordResponse,
    dependencies=[Depends(auth_limiter)],
)
def forgot_password(payload: ForgotPasswordRequest, db: DbSession) -> ForgotPasswordResponse:
    token = auth_service.request_password_reset(db, payload.email)
    response = ForgotPasswordResponse(
        message="If an account exists for that email, a password reset link has been created."
    )
    if token:
        # Development convenience only; production requires email delivery.
        response.reset_token = token
    return response


@router.post(
    "/reset-password",
    response_model=MessageResponse,
    dependencies=[Depends(auth_limiter)],
)
def reset_password(payload: ResetPasswordRequest, db: DbSession) -> MessageResponse:
    auth_service.reset_password(db, payload.token, payload.new_password)
    return MessageResponse(message="Password updated. Please sign in.")


@router.get("/me", response_model=UserOut)
def me(user: CurrentUser) -> UserOut:
    return UserOut.model_validate(user)


@router.patch("/me", response_model=UserOut)
def update_me(payload: ProfileUpdateRequest, user: CurrentUser, db: DbSession) -> UserOut:
    return auth_service.update_profile(db, user, payload.full_name)


@router.post("/change-password", response_model=MessageResponse)
def change_password(
    payload: ChangePasswordRequest, user: CurrentUser, db: DbSession
) -> MessageResponse:
    auth_service.change_password(db, user, payload.current_password, payload.new_password)
    return MessageResponse(message="Password changed. Please sign in again.")


@router.delete("/me", response_model=MessageResponse)
def delete_me(payload: DeleteAccountRequest, user: CurrentUser, db: DbSession) -> MessageResponse:
    auth_service.delete_account(db, user, payload.password)
    return MessageResponse(message="Account deleted.")


@router.get("/sessions", response_model=list[SessionOut])
def sessions(user: CurrentUser, db: DbSession) -> list[SessionOut]:
    return [SessionOut.model_validate(s) for s in list_active_sessions(db, user.id)]
