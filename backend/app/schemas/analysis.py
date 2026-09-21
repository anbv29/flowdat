import uuid
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class AnalysisIntent(StrEnum):
    AGGREGATION = "aggregation"
    COMPARISON = "comparison"
    TIME_SERIES = "time_series"
    RANKING = "ranking"
    DISTRIBUTION = "distribution"
    RELATIONSHIP = "relationship"
    RECORD_LOOKUP = "record_lookup"


class Aggregation(StrEnum):
    SUM = "sum"
    AVERAGE = "average"
    COUNT = "count"
    COUNT_DISTINCT = "count_distinct"
    MINIMUM = "minimum"
    MAXIMUM = "maximum"
    MEDIAN = "median"
    PERCENTAGE_CHANGE = "percentage_change"


class ChartType(StrEnum):
    NONE = "none"
    KPI = "kpi"
    LINE = "line"
    BAR = "bar"
    DONUT = "donut"
    HISTOGRAM = "histogram"
    SCATTER = "scatter"
    TABLE = "table"


class TimeGranularity(StrEnum):
    DAY = "day"
    WEEK = "week"
    MONTH = "month"
    QUARTER = "quarter"
    YEAR = "year"


class Metric(StrictModel):
    column: str | None = None
    aggregation: Aggregation
    alias: str = Field(min_length=1, max_length=80)


class AnalysisFilter(StrictModel):
    column: str
    operator: Literal["eq", "neq", "gt", "gte", "lt", "lte", "in", "between", "contains"]
    value: Any


class AnalysisPlan(StrictModel):
    restated_question: str = Field(min_length=3, max_length=500)
    intent: AnalysisIntent
    selected_dataset: uuid.UUID
    metrics: list[Metric] = Field(default_factory=list, max_length=8)
    dimensions: list[str] = Field(default_factory=list, max_length=6)
    filters: list[AnalysisFilter] = Field(default_factory=list, max_length=12)
    time_column: str | None = None
    time_granularity: TimeGranularity | None = None
    required_joins: list[str] = Field(default_factory=list, max_length=4)
    assumptions: list[str] = Field(default_factory=list, max_length=8)
    clarification_needed: bool = False
    clarification_question: str | None = Field(default=None, max_length=300)
    suggested_chart: ChartType
    approach: str = Field(min_length=5, max_length=1000)

    @model_validator(mode="after")
    def validate_clarification(self) -> "AnalysisPlan":
        if self.clarification_needed and not self.clarification_question:
            raise ValueError("clarification_question is required when clarification_needed is true")
        if not self.clarification_needed and self.clarification_question:
            raise ValueError("clarification_question must be empty when no clarification is needed")
        if self.time_granularity and not self.time_column:
            raise ValueError("time_column is required when time_granularity is set")
        return self


class PlanRequest(StrictModel):
    question: str = Field(min_length=2, max_length=2000)


class PlanResponse(StrictModel):
    plan: AnalysisPlan
    provider: str
    model: str
    prompt_version: str
    mode: Literal["openai", "local_fallback"]
