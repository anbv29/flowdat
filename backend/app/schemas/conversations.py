import uuid
from datetime import datetime
from typing import Any

from pydantic import ConfigDict, Field

from app.schemas.analysis import AnalysisPlan, StrictModel


class CreateConversationRequest(StrictModel):
    dataset_id: uuid.UUID
    business_context: str | None = Field(default=None, max_length=4000)


class ConversationResponse(StrictModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: uuid.UUID
    dataset_id: uuid.UUID
    title: str
    business_context: str | None
    created_at: datetime
    updated_at: datetime


class AddQuestionRequest(StrictModel):
    content: str = Field(min_length=2, max_length=2000)


class MessageResponse(StrictModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: uuid.UUID
    conversation_id: uuid.UUID
    role: str
    content: str
    payload: dict[str, Any] | None
    created_at: datetime


class CreatePlanRequest(StrictModel):
    message_id: uuid.UUID


class CreatedPlanResponse(StrictModel):
    query_run_id: uuid.UUID
    assistant_message: MessageResponse
    plan: AnalysisPlan
    provider: str
    model: str
    prompt_version: str
    mode: str
