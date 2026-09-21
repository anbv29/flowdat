import uuid
from datetime import UTC, datetime
from pathlib import Path

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.core.errors import AppError
from app.models import Dataset, QueryRun
from app.schemas.analysis import AnalysisPlan
from app.schemas.results import ExecuteRunResponse
from app.services.analysis_provider import build_dataset_context
from app.services.answers import build_answer
from app.services.execution import execute_query, verify_result
from app.services.sql_generation import get_sql_generation_provider
from app.services.sql_safety import SQLSafetyService

router = APIRouter(prefix="/query-runs", tags=["query runs"])


@router.post("/{query_run_id}/execute", response_model=ExecuteRunResponse)
async def execute_analysis(
    query_run_id: uuid.UUID,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> ExecuteRunResponse:
    query_run = db.get(QueryRun, query_run_id)
    if not query_run:
        raise AppError(
            "query_run_not_found", "That analysis is no longer available.", status_code=404
        )
    if query_run.execution_status == "completed" and query_run.answer:
        return ExecuteRunResponse(
            query_run_id=query_run.id,
            status="completed",
            answer=query_run.answer,
            model=query_run.model_identifier or "unknown",
            mode="local_fallback"
            if (query_run.model_identifier or "").startswith("deterministic")
            else "openai",
        )

    plan = AnalysisPlan.model_validate(query_run.analysis_plan)
    if plan.clarification_needed:
        raise AppError(
            "clarification_required", "Answer the clarification before running this plan."
        )
    dataset = db.scalar(
        select(Dataset)
        .options(selectinload(Dataset.columns))
        .where(Dataset.id == query_run.dataset_id)
    )
    if not dataset:
        raise AppError("dataset_not_found", "That dataset is no longer available.", status_code=404)

    provider = get_sql_generation_provider(settings)
    generated = await provider.generate_sql(plan, build_dataset_context(dataset))
    query_run.sql = generated.sql
    query_run.correction_attempts = [{"attempt": 1, "sql": generated.sql, "stage": "generated"}]
    try:
        safety = SQLSafetyService(
            "dataset", {column.name for column in dataset.columns}, settings.max_result_rows
        )
        validated = safety.validate(generated.sql)
        query_run.sql = validated.sql
        query_run.validation_outcome = {
            "valid": True,
            "limit_applied": validated.limit_applied,
            "max_rows": validated.max_rows,
        }
        columns, rows, elapsed_ms = execute_query(
            Path(dataset.profile["duckdb_path"]),
            validated.sql,
            settings.query_timeout_seconds,
        )
        verify_result(columns, rows)
        answer = build_answer(plan, columns, rows, validated.sql, elapsed_ms)
    except AppError as exc:
        query_run.execution_status = (
            "rejected"
            if exc.code.startswith("sql_")
            or exc.code
            in {
                "statement_not_allowed",
                "unknown_tables",
                "unknown_columns",
                "filesystem_access_rejected",
                "multiple_statements",
            }
            else "failed"
        )
        query_run.validation_outcome = {
            "valid": False,
            "code": exc.code,
            "message": exc.message,
        }
        query_run.completed_at = datetime.now(UTC)
        db.commit()
        raise

    query_run.execution_status = "completed"
    query_run.execution_time_ms = elapsed_ms
    query_run.row_count = len(rows)
    query_run.answer = answer.model_dump(mode="json")
    query_run.model_identifier = generated.model
    query_run.token_usage = _merge_usage(query_run.token_usage, generated.token_usage)
    query_run.correction_attempts = [
        {"attempt": 1, "sql": validated.sql, "stage": "executed", "row_count": len(rows)}
    ]
    query_run.completed_at = datetime.now(UTC)
    db.commit()
    return ExecuteRunResponse(
        query_run_id=query_run.id,
        status="completed",
        answer=answer,
        model=generated.model,
        mode=generated.mode,
    )


def _merge_usage(current: dict | None, added: dict[str, int]) -> dict[str, int]:
    result = dict(current or {})
    for key, value in added.items():
        result[key] = int(result.get(key, 0)) + value
    return result
