import uuid
from datetime import datetime

from pydantic import Field

from app.schemas.analysis import StrictModel


class SaveInsightRequest(StrictModel):
    query_run_id: uuid.UUID
    title: str = Field(min_length=2, max_length=255)
    note: str | None = Field(default=None, max_length=2000)


class SavedInsightResponse(StrictModel):
    id: uuid.UUID
    dataset_id: uuid.UUID
    query_run_id: uuid.UUID
    title: str
    note: str | None
    created_at: datetime
    updated_at: datetime
