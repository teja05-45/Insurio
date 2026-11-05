"""Conversation, message-streaming, regeneration, and feedback routes."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import StreamingResponse

from app.api.deps import CurrentUser, DbSession, OwnedConversation
from app.core.config import get_settings
from app.core.errors import AppError
from app.core.rate_limit import rate_limit
from app.repositories import conversations as conversation_repo
from app.schemas.chat import (
    AskRequest,
    ConversationCreateRequest,
    ConversationDetail,
    ConversationOut,
    ConversationUpdateRequest,
    FeedbackRequest,
)
from app.schemas.common import MessageResponse, Page
from app.services import answering
from app.services import conversations as conversation_service

router = APIRouter(tags=["chat"])
settings = get_settings()
chat_limiter = rate_limit("chat", settings.CHAT_RATE_LIMIT_PER_MINUTE)


def _require_llm() -> None:
    if not settings.llm_configured:
        raise AppError(
            "AI answers are not configured on this deployment. Set GROQ_API_KEY to enable chat.",
            code="llm_not_configured",
            status_code=503,
        )


@router.post(
    "/conversations",
    response_model=ConversationOut,
    status_code=status.HTTP_201_CREATED,
)
def create_conversation(
    payload: ConversationCreateRequest, user: CurrentUser, db: DbSession
) -> ConversationOut:
    return conversation_service.create(db, user, payload.document_id, payload.title)


@router.get("/conversations", response_model=Page[ConversationOut])
def list_conversations(
    user: CurrentUser,
    db: DbSession,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> Page[ConversationOut]:
    items, total = conversation_service.list_for_user(db, user, page=page, page_size=page_size)
    return Page(items=items, total=total, page=page, page_size=page_size)


@router.get("/conversations/{conversation_id}", response_model=ConversationDetail)
def get_conversation(
    conversation: OwnedConversation, user: CurrentUser, db: DbSession
) -> ConversationDetail:
    return conversation_service.get_detail(db, conversation, user)


@router.patch("/conversations/{conversation_id}", response_model=ConversationOut)
def rename_conversation(
    payload: ConversationUpdateRequest,
    conversation: OwnedConversation,
    user: CurrentUser,
    db: DbSession,
) -> ConversationOut:
    conversation_service.rename(db, conversation, payload.title)
    db.refresh(conversation)
    return ConversationOut(
        id=conversation.id,
        document_id=conversation.document_id,
        title=conversation.title,
        last_activity_at=conversation.last_activity_at,
        created_at=conversation.created_at,
    )


@router.delete("/conversations/{conversation_id}", response_model=MessageResponse)
def delete_conversation(conversation: OwnedConversation, db: DbSession) -> MessageResponse:
    conversation_service.delete(db, conversation)
    return MessageResponse(message="Conversation deleted.")


@router.post(
    "/conversations/{conversation_id}/messages",
    dependencies=[Depends(chat_limiter)],
    response_class=StreamingResponse,
)
def ask_question(
    payload: AskRequest,
    conversation: OwnedConversation,
    user: CurrentUser,
    db: DbSession,
) -> StreamingResponse:
    _require_llm()
    if conversation.last_activity_at is None:
        conversation_repo.touch(db, conversation)
        db.commit()
    user_message, assistant, _ = conversation_service.begin_exchange(
        db, conversation.id, payload.question
    )
    stream = answering.stream_exchange(
        conversation_id=conversation.id,
        user_message_id=user_message.id,
        assistant_id=assistant.id,
        question=payload.question,
        top_k=payload.top_k,
    )
    return StreamingResponse(stream, media_type="text/event-stream", headers=answering.SSE_HEADERS)


@router.post(
    "/conversations/{conversation_id}/regenerate",
    dependencies=[Depends(chat_limiter)],
    response_class=StreamingResponse,
)
def regenerate_answer(
    conversation: OwnedConversation,
    db: DbSession,
    top_k: Annotated[int | None, Query(ge=1, le=10)] = None,
) -> StreamingResponse:
    _require_llm()
    question, assistant = conversation_service.prepare_regenerate(db, conversation)
    user_message_id = conversation_repo.last_user_message_id(db, conversation.id) or assistant.id
    stream = answering.stream_exchange(
        conversation_id=conversation.id,
        user_message_id=user_message_id,
        assistant_id=assistant.id,
        question=question,
        top_k=top_k,
    )
    return StreamingResponse(stream, media_type="text/event-stream", headers=answering.SSE_HEADERS)


@router.post("/messages/{message_id}/feedback", response_model=MessageResponse)
def message_feedback(
    message_id: uuid.UUID,
    payload: FeedbackRequest,
    user: CurrentUser,
    db: DbSession,
) -> MessageResponse:
    message = conversation_repo.get_message_owned(db, message_id, user.id)
    if message is None:
        raise AppError("Message not found.", code="message_not_found", status_code=404)
    conversation_service.add_feedback(db, message, user, payload.rating, payload.comment)
    return MessageResponse(message="Thanks for the feedback.")
