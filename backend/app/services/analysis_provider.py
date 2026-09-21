import json
import re
from dataclasses import dataclass
from typing import Protocol

from openai import AsyncOpenAI
from pydantic import BaseModel

from app.core.config import Settings
from app.core.errors import AppError
from app.models import Dataset
from app.schemas.analysis import (
    Aggregation,
    AnalysisIntent,
    AnalysisPlan,
    ChartType,
    Metric,
    TimeGranularity,
)

PROMPT_VERSION = "analysis-plan-v1"


class ContextColumn(BaseModel):
    name: str
    data_type: str
    semantic_type: str
    null_percentage: float
    distinct_count: int
    statistics: dict
    representative_values: list


class DatasetContext(BaseModel):
    id: str
    name: str
    description: str | None
    row_count: int
    columns: list[ContextColumn]


@dataclass(frozen=True)
class PlanResult:
    plan: AnalysisPlan
    provider: str
    model: str
    prompt_version: str
    mode: str
    token_usage: dict[str, int]


class AnalysisPlanProvider(Protocol):
    async def create_plan(self, question: str, context: DatasetContext) -> PlanResult: ...


class OpenAIAnalysisPlanProvider:
    def __init__(self, api_key: str, model: str) -> None:
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = model

    async def create_plan(self, question: str, context: DatasetContext) -> PlanResult:
        try:
            response = await self.client.responses.parse(
                model=self.model,
                instructions=PLAN_INSTRUCTIONS,
                input=_plan_input(question, context),
                text_format=AnalysisPlan,
                store=False,
            )
        except Exception as exc:
            raise AppError(
                "analysis_provider_failed",
                "The analysis service could not prepare a plan. Please try again.",
                status_code=502,
                details={"provider": "openai", "reason": exc.__class__.__name__},
            ) from exc

        if response.output_parsed is None:
            raise AppError(
                "analysis_plan_missing",
                "The analysis service did not return a usable plan.",
                status_code=502,
            )
        usage = response.usage
        return PlanResult(
            plan=response.output_parsed,
            provider="openai",
            model=self.model,
            prompt_version=PROMPT_VERSION,
            mode="openai",
            token_usage={
                "input_tokens": usage.input_tokens if usage else 0,
                "output_tokens": usage.output_tokens if usage else 0,
            },
        )


class LocalAnalysisPlanProvider:
    """Small, explicit planner for development without an API key."""

    async def create_plan(self, question: str, context: DatasetContext) -> PlanResult:
        return PlanResult(
            plan=_local_plan(question, context),
            provider="local",
            model="deterministic-planner-v1",
            prompt_version=PROMPT_VERSION,
            mode="local_fallback",
            token_usage={},
        )


def get_analysis_plan_provider(settings: Settings) -> AnalysisPlanProvider:
    if settings.openai_api_key:
        return OpenAIAnalysisPlanProvider(settings.openai_api_key, settings.openai_model)
    return LocalAnalysisPlanProvider()


def build_dataset_context(dataset: Dataset) -> DatasetContext:
    return DatasetContext(
        id=str(dataset.id),
        name=dataset.name,
        description=dataset.description,
        row_count=dataset.row_count,
        columns=[
            ContextColumn(
                name=column.name,
                data_type=column.data_type,
                semantic_type=column.semantic_type,
                null_percentage=float(column.statistics.get("null_percentage", 0)),
                distinct_count=column.distinct_count,
                statistics=column.statistics,
                representative_values=column.sample_values[:5],
            )
            for column in dataset.columns
        ],
    )


PLAN_INSTRUCTIONS = """You plan read-only analysis of one DuckDB dataset.
Use only column names present in the supplied dataset context. Never invent joins.
Do not write SQL. Restate the question, choose explicit metrics, dimensions, filters,
time handling, assumptions, and one restrained chart. Ask one concise clarification
only when a material ambiguity changes the result. The selected_dataset must exactly
match the supplied dataset id. A row count metric uses aggregation=count and column=null.
"""


def _plan_input(question: str, context: DatasetContext) -> str:
    payload = {"question": question, "dataset": context.model_dump(mode="json")}
    return json.dumps(payload, separators=(",", ":"), ensure_ascii=False)


def _local_plan(question: str, context: DatasetContext) -> AnalysisPlan:
    lowered = question.lower()
    columns = {column.name.lower(): column for column in context.columns}
    measures = [column for column in context.columns if column.semantic_type == "measure"]
    dates = [column for column in context.columns if column.semantic_type == "date"]

    metric_column = _find_column(lowered, measures) or _alias_column(lowered, measures)
    wants_count = any(term in lowered for term in ("how many", "number of", "count", "orders"))
    aggregation = _aggregation(lowered, wants_count)
    if aggregation == Aggregation.COUNT:
        metric = Metric(column=None, aggregation=aggregation, alias="row_count")
    elif metric_column:
        metric = Metric(
            column=metric_column.name,
            aggregation=aggregation,
            alias=f"{aggregation.value}_{metric_column.name}",
        )
    else:
        metric = None

    dimension = _dimension_after_by(lowered, context.columns)
    wants_time = any(
        term in lowered for term in ("over time", "trend", "monthly", "weekly", "daily")
    )
    time_column = dates[0].name if wants_time and dates else None
    granularity = _granularity(lowered) if time_column else None
    if time_column and not dimension:
        dimension = time_column

    ambiguous = metric is None and not wants_count
    clarification = "Which measure should I use for this analysis?" if ambiguous else None
    intent = _intent(wants_time, dimension, lowered)
    assumptions = []
    if metric_column and "revenue" in lowered and metric_column.name.lower() != "revenue":
        assumptions.append(f"Revenue is represented by {metric_column.name}.")
    if (
        dimension
        and dimension.lower() in columns
        and columns[dimension.lower()].semantic_type == "category"
    ):
        assumptions.append(f"Results are grouped by {dimension}.")

    return AnalysisPlan(
        restated_question=question.strip().rstrip("?") + ".",
        intent=intent,
        selected_dataset=context.id,
        metrics=[metric] if metric else [],
        dimensions=[dimension] if dimension else [],
        filters=[],
        time_column=time_column,
        time_granularity=granularity,
        required_joins=[],
        assumptions=assumptions,
        clarification_needed=ambiguous,
        clarification_question=clarification,
        suggested_chart=_chart(intent, bool(dimension)),
        approach=_approach(metric, dimension, time_column, ambiguous),
    )


def _find_column(question: str, candidates: list[ContextColumn]) -> ContextColumn | None:
    return next((column for column in candidates if column.name.lower() in question), None)


def _alias_column(question: str, candidates: list[ContextColumn]) -> ContextColumn | None:
    aliases = {
        "revenue": ("revenue", "sales", "amount", "total"),
        "quantity": ("quantity", "units"),
    }
    for preferred_name, terms in aliases.items():
        if any(term in question for term in terms):
            exact = next(
                (column for column in candidates if column.name.lower() == preferred_name), None
            )
            if exact:
                return exact
    return None


def _dimension_after_by(question: str, candidates: list[ContextColumn]) -> str | None:
    match = re.search(r"\bby\s+([\w ]+)", question)
    search_area = match.group(1) if match else question
    return next((column.name for column in candidates if column.name.lower() in search_area), None)


def _aggregation(question: str, wants_count: bool) -> Aggregation:
    if wants_count:
        return Aggregation.COUNT
    if any(term in question for term in ("average", "avg", "mean")):
        return Aggregation.AVERAGE
    if "median" in question:
        return Aggregation.MEDIAN
    if "minimum" in question or "lowest" in question:
        return Aggregation.MINIMUM
    if "maximum" in question or "highest" in question:
        return Aggregation.MAXIMUM
    return Aggregation.SUM


def _granularity(question: str) -> TimeGranularity:
    if "daily" in question:
        return TimeGranularity.DAY
    if "weekly" in question:
        return TimeGranularity.WEEK
    if "quarter" in question:
        return TimeGranularity.QUARTER
    if "year" in question:
        return TimeGranularity.YEAR
    return TimeGranularity.MONTH


def _intent(wants_time: bool, dimension: str | None, question: str) -> AnalysisIntent:
    if wants_time:
        return AnalysisIntent.TIME_SERIES
    if any(term in question for term in ("top", "bottom", "rank", "highest", "lowest")):
        return AnalysisIntent.RANKING
    return AnalysisIntent.COMPARISON if dimension else AnalysisIntent.AGGREGATION


def _chart(intent: AnalysisIntent, has_dimension: bool) -> ChartType:
    if intent == AnalysisIntent.TIME_SERIES:
        return ChartType.LINE
    if has_dimension:
        return ChartType.BAR
    return ChartType.KPI


def _approach(
    metric: Metric | None, dimension: str | None, time_column: str | None, ambiguous: bool
) -> str:
    if ambiguous:
        return "Wait for the requested measure before constructing a query."
    metric_text = "Count rows" if metric and metric.column is None else f"Calculate {metric.alias}"
    if time_column:
        return f"{metric_text} across periods from {time_column}."
    if dimension:
        return f"{metric_text} and group the result by {dimension}."
    return f"{metric_text} across the complete dataset."
