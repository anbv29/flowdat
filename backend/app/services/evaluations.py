import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.core.config import Settings
from app.core.errors import AppError
from app.models import Dataset, EvaluationCase
from app.services.analysis_provider import build_dataset_context, get_analysis_plan_provider
from app.services.analysis_validation import validate_plan_for_dataset
from app.services.execution import execute_query, verify_result
from app.services.sql_generation import get_sql_generation_provider
from app.services.sql_safety import SQLSafetyService


@dataclass(frozen=True)
class EvaluationOutcome:
    status: str
    scores: dict[str, Any]
    latency_ms: float
    estimated_cost_usd: float
    failure_reason: str | None


async def evaluate_case(
    case: EvaluationCase,
    dataset: Dataset,
    settings: Settings,
) -> EvaluationOutcome:
    started = time.perf_counter()
    expected = case.expected
    actual = "failed"
    sql_valid = False
    executed = False
    result_correct = False
    clarification_quality = 0.0
    unsafe_rejected = 0.0
    failure_reason: str | None = None
    token_usage: dict[str, int] = {}

    try:
        context = build_dataset_context(dataset)
        plan_result = await get_analysis_plan_provider(settings).create_plan(case.question, context)
        token_usage = merge_usage(token_usage, plan_result.token_usage)
        plan = validate_plan_for_dataset(plan_result.plan, dataset)
        if plan.clarification_needed:
            actual = "clarification"
            terms = expected.get("clarification_terms", [])
            question = (plan.clarification_question or "").lower()
            clarification_quality = float(not terms or any(term in question for term in terms))
        else:
            sql_result = await get_sql_generation_provider(settings).generate_sql(plan, context)
            token_usage = merge_usage(token_usage, sql_result.token_usage)
            validated = SQLSafetyService(
                "dataset", {column.name for column in dataset.columns}, settings.max_result_rows
            ).validate(sql_result.sql)
            sql_valid = True
            columns, rows, _ = execute_query(
                Path(dataset.profile["duckdb_path"]),
                validated.sql,
                settings.query_timeout_seconds,
            )
            verify_result(columns, rows, plan, dataset)
            executed = True
            actual = "success"
            result_correct = matches_expectation(expected, plan.model_dump(mode="json"), columns)
    except AppError as exc:
        actual = "rejected" if exc.code in rejection_codes() else "failed"
        unsafe_rejected = float(case.category == "unsafe_sql" and actual == "rejected")
        failure_reason = exc.message

    passed = expected.get("outcome") == actual
    if actual == "success" and expected.get("outcome") == "success":
        passed = result_correct
    if expected.get("outcome") == "insufficient_data":
        passed = actual in {"clarification", "failed"}
    if case.category == "unsafe_sql":
        passed = actual == "rejected"
    latency = (time.perf_counter() - started) * 1000
    return EvaluationOutcome(
        status="passed" if passed else "failed",
        scores={
            "actual_outcome": actual,
            "sql_validity": float(sql_valid),
            "execution_success": float(executed),
            "result_correctness": float(result_correct),
            "clarification_quality": clarification_quality,
            "unsafe_query_rejection": unsafe_rejected,
            "expected": expected,
            "question": case.question,
            "category": case.category,
        },
        latency_ms=latency,
        estimated_cost_usd=estimate_cost(token_usage, settings),
        failure_reason=None
        if passed
        else failure_reason or f"Expected {expected.get('outcome')}, got {actual}.",
    )


def matches_expectation(expected: dict, plan: dict, columns: list[str]) -> bool:
    if not set(expected.get("required_columns", [])) <= set(columns):
        return False
    if not set(expected.get("dimensions", [])) <= set(plan.get("dimensions", [])):
        return False
    if expected.get("time_column") and plan.get("time_column") != expected["time_column"]:
        return False
    if expected.get("granularity") and plan.get("time_granularity") != expected["granularity"]:
        return False
    return True


def estimate_cost(token_usage: dict[str, int], settings: Settings) -> float:
    input_cost = (
        token_usage.get("input_tokens", 0) * settings.model_input_cost_per_million_usd / 1_000_000
    )
    output_cost = (
        token_usage.get("output_tokens", 0) * settings.model_output_cost_per_million_usd / 1_000_000
    )
    return round(input_cost + output_cost, 6)


def merge_usage(current: dict[str, int], added: dict[str, int]) -> dict[str, int]:
    result = dict(current)
    for key, value in added.items():
        result[key] = result.get(key, 0) + value
    return result


def rejection_codes() -> set[str]:
    return {
        "statement_not_allowed",
        "multiple_statements",
        "filesystem_access_rejected",
        "unknown_tables",
        "unknown_columns",
        "sql_comments_rejected",
    }
