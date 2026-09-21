import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.core.errors import AppError
from app.models import Conversation, Dataset, Message, QueryRun
from app.schemas.conversations import (
    AddQuestionRequest,
    ConversationResponse,
    CreateConversationRequest,
    CreatedPlanResponse,
    CreatePlanRequest,
    MessageResponse,
)
from app.services.analysis_provider import build_dataset_context, get_analysis_plan_provider
from app.services.analysis_validation import validate_plan_for_dataset

router = APIRouter(prefix="/conversations", tags=["conversations"])


@router.post("", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
def create_conversation(
    body: CreateConversationRequest,
    db: Session = Depends(get_db),
) -> Conversation:
    if not db.get(Dataset, body.dataset_id):
        raise AppError("dataset_not_found", "That dataset is no longer available.", status_code=404)
    conversation = Conversation(
        dataset_id=body.dataset_id,
        title="Untitled analysis",
        business_context=body.business_context,
    )
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    return conversation


@router.get("", response_model=list[ConversationResponse])
def list_conversations(
    dataset_id: uuid.UUID | None = Query(default=None),
    db: Session = Depends(get_db),
) -> list[Conversation]:
    statement = select(Conversation).order_by(Conversation.updated_at.desc())
    if dataset_id:
        statement = statement.where(Conversation.dataset_id == dataset_id)
    return list(db.scalars(statement).all())


@router.get("/{conversation_id}/messages", response_model=list[MessageResponse])
def list_messages(
    conversation_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> list[Message]:
    if not db.get(Conversation, conversation_id):
        raise AppError(
            "conversation_not_found", "That conversation is no longer available.", status_code=404
        )
    statement = (
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.asc())
    )
    return list(db.scalars(statement).all())


@router.post(
    "/{conversation_id}/messages",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_question(
    conversation_id: uuid.UUID,
    body: AddQuestionRequest,
    db: Session = Depends(get_db),
) -> Message:
    conversation = db.get(Conversation, conversation_id)
    if not conversation:
        raise AppError(
            "conversation_not_found", "That conversation is no longer available.", status_code=404
        )
    message = Message(conversation_id=conversation_id, role="user", content=body.content.strip())
    db.add(message)
    if conversation.title == "Untitled analysis":
        conversation.title = conversation_title(message.content)
    db.commit()
    db.refresh(message)
    return message


@router.post("/{conversation_id}/plans", response_model=CreatedPlanResponse)
async def create_analysis_plan(
    conversation_id: uuid.UUID,
    body: CreatePlanRequest,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> CreatedPlanResponse:
    conversation = db.scalar(
        select(Conversation)
        .options(selectinload(Conversation.dataset))
        .where(Conversation.id == conversation_id)
    )
    if not conversation:
        raise AppError(
            "conversation_not_found", "That conversation is no longer available.", status_code=404
        )
    message = db.get(Message, body.message_id)
    if not message or message.conversation_id != conversation_id or message.role != "user":
        raise AppError(
            "question_not_found", "Choose a valid question from this conversation.", status_code=404
        )

    dataset = db.scalar(
        select(Dataset)
        .options(selectinload(Dataset.columns))
        .where(Dataset.id == conversation.dataset_id)
    )
    if not dataset:
        raise AppError("dataset_not_found", "That dataset is no longer available.", status_code=404)

    provider = get_analysis_plan_provider(settings)
    result = await provider.create_plan(message.content, build_dataset_context(dataset))
    plan = validate_plan_for_dataset(result.plan, dataset)
    query_run = QueryRun(
        conversation_id=conversation.id,
        dataset_id=dataset.id,
        user_question=message.content,
        analysis_plan=plan.model_dump(mode="json"),
        validation_outcome={"valid": True},
        execution_status="needs_clarification" if plan.clarification_needed else "planned",
        correction_attempts=[],
        model_identifier=result.model,
        prompt_version=result.prompt_version,
        token_usage=result.token_usage,
    )
    assistant = Message(
        conversation_id=conversation.id,
        role="assistant",
        content=plan.clarification_question if plan.clarification_needed else plan.approach,
        payload={"type": "analysis_plan", "plan": plan.model_dump(mode="json")},
    )
    db.add_all([query_run, assistant])
    db.commit()
    db.refresh(query_run)
    db.refresh(assistant)
    return CreatedPlanResponse(
        query_run_id=query_run.id,
        assistant_message=MessageResponse.model_validate(assistant),
        plan=plan,
        provider=result.provider,
        model=result.model,
        prompt_version=result.prompt_version,
        mode=result.mode,
    )


def conversation_title(question: str) -> str:
    compact = " ".join(question.strip().split())
    return compact if len(compact) <= 64 else compact[:61].rstrip() + "…"
