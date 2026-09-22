import csv
import io
import uuid
from datetime import UTC, datetime
from pathlib import Path

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.core.errors import AppError
from app.models import Dataset, Message, QueryRun
from app.schemas.analysis import AnalysisPlan
from app.schemas.results import ExecuteRunResponse, QueryRunHistoryItem
from app.services.analysis_provider import build_dataset_context
from app.services.answers import build_answer
from app.services.execution import execute_query, verify_result
from app.services.sql_generation import get_sql_generation_provider
from app.services.sql_safety import SQLSafetyService

router = APIRouter(prefix="/query-runs", tags=["query runs"])


@router.get("", response_model=list[QueryRunHistoryItem])
def list_query_runs(
    dataset_id: uuid.UUID | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
) -> list[QueryRunHistoryItem]:
    statement = (
        select(QueryRun, Dataset.name)
        .join(Dataset, Dataset.id == QueryRun.dataset_id)
        .order_by(QueryRun.created_at.desc())
        .limit(limit)
    )
    if dataset_id:
        statement = statement.where(QueryRun.dataset_id == dataset_id)
    return [
        QueryRunHistoryItem(
            id=run.id,
            dataset_id=run.dataset_id,
            dataset_name=dataset_name,
            conversation_id=run.conversation_id,
            user_question=run.user_question,
            execution_status=run.execution_status,
            execution_time_ms=run.execution_time_ms,
            row_count=run.row_count,
            answer_summary=(run.answer or {}).get("direct_answer"),
            created_at=run.created_at,
        )
        for run, dataset_name in db.execute(statement).all()
    ]


@router.get("/{query_run_id}/export")
def export_query_result(
    query_run_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> StreamingResponse:
    query_run = db.get(QueryRun, query_run_id)
    if not query_run or query_run.execution_status != "completed" or not query_run.answer:
        raise AppError(
            "result_not_available",
            "This analysis does not have an exportable result.",
            status_code=404,
        )
    answer = query_run.answer
    columns = answer.get("columns", [])
    rows = answer.get("rows", [])
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=columns, extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        writer.writerow({column: safe_csv_value(row.get(column)) for column in columns})
    filename = f"signaldesk-{str(query_run.id)[:8]}.csv"
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def safe_csv_value(value: object) -> object:
    if isinstance(value, str) and value.startswith(("=", "+", "-", "@")):
        return "'" + value
    return value


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
    if query_run.conversation_id:
        db.add(
            Message(
                conversation_id=query_run.conversation_id,
                role="assistant",
                content=answer.direct_answer,
                payload={"type": "analysis_answer", "answer": answer.model_dump(mode="json")},
            )
        )
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
