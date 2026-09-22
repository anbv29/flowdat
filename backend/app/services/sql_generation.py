import json
from dataclasses import dataclass
from typing import Any, Protocol

from openai import AsyncOpenAI

from app.core.config import Settings
from app.core.errors import AppError
from app.schemas.analysis import Aggregation, AnalysisPlan, TimeGranularity
from app.schemas.results import SQLDraft
from app.services.analysis_provider import DatasetContext

SQL_PROMPT_VERSION = "sql-generation-v1"


@dataclass(frozen=True)
class SQLResult:
    sql: str
    provider: str
    model: str
    mode: str
    token_usage: dict[str, int]


class SQLGenerationProvider(Protocol):
    async def generate_sql(self, plan: AnalysisPlan, context: DatasetContext) -> SQLResult: ...

    async def correct_sql(
        self,
        plan: AnalysisPlan,
        context: DatasetContext,
        failed_sql: str,
        error_code: str,
    ) -> SQLResult: ...


class OpenAISQLGenerationProvider:
    def __init__(self, api_key: str, model: str) -> None:
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = model

    async def generate_sql(self, plan: AnalysisPlan, context: DatasetContext) -> SQLResult:
        payload = {
            "plan": plan.model_dump(mode="json"),
            "table": "dataset",
            "columns": [{"name": item.name, "type": item.data_type} for item in context.columns],
        }
        try:
            response = await self.client.responses.parse(
                model=self.model,
                instructions=SQL_INSTRUCTIONS,
                input=json.dumps(payload, separators=(",", ":")),
                text_format=SQLDraft,
                store=False,
            )
        except Exception as exc:
            raise AppError(
                "sql_provider_failed",
                "The analysis service could not prepare a query. Please try again.",
                status_code=502,
                details={"provider": "openai", "reason": exc.__class__.__name__},
            ) from exc
        if response.output_parsed is None:
            raise AppError(
                "sql_missing",
                "The analysis service did not return a usable query.",
                status_code=502,
            )
        usage = response.usage
        return SQLResult(
            sql=response.output_parsed.sql,
            provider="openai",
            model=self.model,
            mode="openai",
            token_usage={
                "input_tokens": usage.input_tokens if usage else 0,
                "output_tokens": usage.output_tokens if usage else 0,
            },
        )

    async def correct_sql(
        self,
        plan: AnalysisPlan,
        context: DatasetContext,
        failed_sql: str,
        error_code: str,
    ) -> SQLResult:
        payload = {
            "plan": plan.model_dump(mode="json"),
            "table": "dataset",
            "columns": [{"name": item.name, "type": item.data_type} for item in context.columns],
            "rejected_sql": failed_sql,
            "validation_error": error_code,
        }
        try:
            response = await self.client.responses.parse(
                model=self.model,
                instructions=SQL_CORRECTION_INSTRUCTIONS,
                input=json.dumps(payload, separators=(",", ":")),
                text_format=SQLDraft,
                store=False,
            )
        except Exception as exc:
            raise AppError(
                "sql_correction_failed",
                "The analysis service could not safely correct the query.",
                status_code=502,
            ) from exc
        if response.output_parsed is None:
            raise AppError("sql_correction_missing", "No corrected query was returned.")
        usage = response.usage
        return SQLResult(
            sql=response.output_parsed.sql,
            provider="openai",
            model=self.model,
            mode="openai",
            token_usage={
                "input_tokens": usage.input_tokens if usage else 0,
                "output_tokens": usage.output_tokens if usage else 0,
            },
        )


class LocalSQLGenerationProvider:
    async def generate_sql(self, plan: AnalysisPlan, context: DatasetContext) -> SQLResult:
        return SQLResult(
            sql=build_sql(plan),
            provider="local",
            model="deterministic-sql-v1",
            mode="local_fallback",
            token_usage={},
        )

    async def correct_sql(
        self,
        plan: AnalysisPlan,
        context: DatasetContext,
        failed_sql: str,
        error_code: str,
    ) -> SQLResult:
        del context, failed_sql, error_code
        return SQLResult(
            sql=build_sql(plan),
            provider="local",
            model="deterministic-sql-v1",
            mode="local_fallback",
            token_usage={},
        )


def get_sql_generation_provider(settings: Settings) -> SQLGenerationProvider:
    if settings.openai_api_key:
        return OpenAISQLGenerationProvider(settings.openai_api_key, settings.openai_model)
    return LocalSQLGenerationProvider()


SQL_INSTRUCTIONS = """Generate one DuckDB SELECT query for the supplied approved plan.
Use only the dataset table and listed columns. Never use comments, multiple statements,
file-reading functions, extensions, pragmas, DDL, or DML. Quote identifiers with double
quotes. Return SQL only in the structured sql field. Do not add an explanation.
"""

SQL_CORRECTION_INSTRUCTIONS = """Correct one rejected DuckDB SELECT query using the
approved plan, schema, and non-sensitive validation error. Return exactly one read-only
query in the structured sql field. Never use comments, external files, extensions,
pragmas, DDL, or DML. Do not repeat an unknown table or column.
"""


def build_sql(plan: AnalysisPlan) -> str:
    if plan.clarification_needed:
        raise AppError(
            "clarification_required", "Answer the clarification before running this plan."
        )
    dimensions = [_dimension_expression(item, plan) for item in plan.dimensions]
    metrics = [
        _metric_expression(item.column, item.aggregation, item.alias) for item in plan.metrics
    ]
    if not dimensions and not metrics:
        raise AppError("empty_analysis_plan", "The plan does not contain anything to calculate.")

    projections = dimensions + metrics
    sql = f"SELECT {', '.join(projections)} FROM dataset"
    if plan.filters:
        sql += " WHERE " + " AND ".join(_filter_expression(item) for item in plan.filters)
    if dimensions:
        sql += " GROUP BY " + ", ".join(str(index) for index in range(1, len(dimensions) + 1))
    if plan.intent.value == "ranking" and metrics:
        sql += f" ORDER BY {_quote(plan.metrics[0].alias)} DESC"
    elif dimensions:
        sql += " ORDER BY 1"
    return sql


def _dimension_expression(column: str, plan: AnalysisPlan) -> str:
    quoted = _quote(column)
    if column == plan.time_column and plan.time_granularity:
        unit = {
            TimeGranularity.DAY: "day",
            TimeGranularity.WEEK: "week",
            TimeGranularity.MONTH: "month",
            TimeGranularity.QUARTER: "quarter",
            TimeGranularity.YEAR: "year",
        }[plan.time_granularity]
        return f"DATE_TRUNC('{unit}', {quoted}) AS period"
    return quoted


def _metric_expression(column: str | None, aggregation: Aggregation, alias: str) -> str:
    if aggregation == Aggregation.COUNT:
        expression = "COUNT(*)" if column is None else f"COUNT({_quote(column)})"
    else:
        if not column:
            raise AppError("metric_column_required", "This metric requires a numeric field.")
        functions = {
            Aggregation.SUM: "SUM",
            Aggregation.AVERAGE: "AVG",
            Aggregation.COUNT_DISTINCT: "COUNT(DISTINCT",
            Aggregation.MINIMUM: "MIN",
            Aggregation.MAXIMUM: "MAX",
            Aggregation.MEDIAN: "MEDIAN",
        }
        if aggregation == Aggregation.PERCENTAGE_CHANGE:
            raise AppError(
                "local_metric_not_supported",
                "Percentage change needs an AI-generated query or "
                "a more specific comparison period.",
            )
        function = functions[aggregation]
        expression = f"{function}({_quote(column)})"
        if aggregation == Aggregation.COUNT_DISTINCT:
            expression += ")"
    return f"{expression} AS {_quote(alias)}"


def _filter_expression(item: Any) -> str:
    column = _quote(item.column)
    operator = item.operator
    if operator == "in":
        if not isinstance(item.value, list) or not item.value:
            raise AppError("invalid_filter", "An ‘in’ filter requires one or more values.")
        return f"{column} IN ({', '.join(_literal(value) for value in item.value)})"
    if operator == "between":
        if not isinstance(item.value, list) or len(item.value) != 2:
            raise AppError("invalid_filter", "A range filter requires two values.")
        return f"{column} BETWEEN {_literal(item.value[0])} AND {_literal(item.value[1])}"
    if operator == "contains":
        return f"{column} ILIKE '%' || {_literal(item.value)} || '%'"
    operators = {"eq": "=", "neq": "!=", "gt": ">", "gte": ">=", "lt": "<", "lte": "<="}
    return f"{column} {operators[operator]} {_literal(item.value)}"


def _quote(value: str) -> str:
    return f'"{value.replace(chr(34), chr(34) * 2)}"'


def _literal(value: Any) -> str:
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, (int, float)):
        return str(value)
    return "'" + str(value).replace("'", "''") + "'"
