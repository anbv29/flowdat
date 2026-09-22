import uuid
from datetime import datetime
from typing import Any

from pydantic import Field

from app.schemas.analysis import ChartType, StrictModel


class SQLDraft(StrictModel):
    sql: str = Field(min_length=6, max_length=20000)


class ChartConfig(StrictModel):
    type: ChartType
    x_key: str | None = None
    y_keys: list[str] = Field(default_factory=list)


class AnalysisAnswer(StrictModel):
    direct_answer: str
    evidence: list[str] = Field(min_length=1, max_length=5)
    columns: list[str]
    rows: list[dict[str, Any]]
    chart: ChartConfig
    assumptions: list[str]
    limitations: list[str]
    generated_sql: str
    row_count: int
    execution_time_ms: float
    suggested_follow_ups: list[str] = Field(max_length=4)


class ExecuteRunResponse(StrictModel):
    query_run_id: uuid.UUID
    status: str
    answer: AnalysisAnswer
    model: str
    mode: str


class QueryRunHistoryItem(StrictModel):
    id: uuid.UUID
    dataset_id: uuid.UUID
    dataset_name: str
    conversation_id: uuid.UUID | None
    user_question: str
    execution_status: str
    execution_time_ms: float | None
    row_count: int | None
    answer_summary: str | None
    created_at: datetime
