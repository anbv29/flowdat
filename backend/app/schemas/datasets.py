import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class DatasetColumnResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str
    position: int
    data_type: str
    semantic_type: str
    nullable: bool
    null_count: int
    distinct_count: int
    statistics: dict[str, Any]
    sample_values: list[Any]


class DatasetSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: str | None
    original_filename: str
    media_type: str
    size_bytes: int
    row_count: int
    column_count: int
    profile_status: str
    created_at: datetime
    updated_at: datetime


class DatasetDetail(DatasetSummary):
    columns: list[DatasetColumnResponse]
    preview: list[dict[str, Any]]


class DatasetListResponse(BaseModel):
    items: list[DatasetSummary]
    total: int
