import math
import threading
import time
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import duckdb

from app.core.errors import AppError
from app.models import Dataset
from app.schemas.analysis import Aggregation, AnalysisIntent, AnalysisPlan


def execute_query(
    database_path: Path, sql: str, timeout_seconds: int
) -> tuple[list[str], list[dict[str, Any]], float]:
    started = time.perf_counter()
    connection = duckdb.connect(str(database_path), read_only=True)
    timer = threading.Timer(timeout_seconds, connection.interrupt)
    timer.start()
    try:
        cursor = connection.execute(sql)
        columns = [item[0] for item in cursor.description]
        values = cursor.fetchall()
    except duckdb.InterruptException as exc:
        raise AppError(
            "query_timeout", "This analysis took too long and was stopped.", status_code=408
        ) from exc
    except duckdb.Error as exc:
        raise AppError(
            "query_execution_failed",
            "The generated query could not be executed safely.",
            details={"reason": exc.__class__.__name__},
        ) from exc
    finally:
        timer.cancel()
        connection.close()
    elapsed_ms = (time.perf_counter() - started) * 1000
    rows = [
        dict(zip(columns, (_json_value(value) for value in row), strict=True)) for row in values
    ]
    return columns, rows, elapsed_ms


def verify_result(
    columns: list[str],
    rows: list[dict[str, Any]],
    plan: AnalysisPlan | None = None,
    dataset: Dataset | None = None,
) -> list[str]:
    if not rows:
        raise AppError(
            "empty_result", "No rows matched this analysis. Try broadening the question."
        )
    if not columns:
        raise AppError("missing_result_columns", "The query returned no usable columns.")
    for row in rows:
        for value in row.values():
            if isinstance(value, float) and not math.isfinite(value):
                raise AppError(
                    "non_finite_result", "The result contains a value that cannot be displayed."
                )
    if not plan:
        return []
    expected = {metric.alias for metric in plan.metrics}
    expected.update(
        "period" if item == plan.time_column and plan.time_granularity else item
        for item in plan.dimensions
    )
    missing = sorted(expected - set(columns))
    if missing:
        raise AppError(
            "missing_required_columns",
            "The result does not contain all fields required by the analysis plan.",
            details={"columns": missing},
        )
    for metric in plan.metrics:
        if metric.aggregation == Aggregation.PERCENTAGE_CHANGE:
            if any(row.get(metric.alias) is None for row in rows):
                raise AppError(
                    "invalid_percentage_result",
                    "A percentage could not be calculated because its denominator was zero.",
                )
    warnings: list[str] = []
    if dataset and plan.intent == AnalysisIntent.RECORD_LOOKUP and plan.filters:
        threshold = max(1, int(dataset.row_count * 0.01))
        if len(rows) <= threshold:
            warnings.append("The applied filters retained fewer than 1% of source rows.")
    _validate_date_filters(plan, dataset)
    return warnings


def _validate_date_filters(plan: AnalysisPlan, dataset: Dataset | None) -> None:
    if not dataset:
        return
    profiles = {column.name: column for column in dataset.columns}
    for item in plan.filters:
        column = profiles.get(item.column)
        if not column or column.semantic_type != "date":
            continue
        minimum = column.statistics.get("min")
        maximum = column.statistics.get("max")
        values = item.value if isinstance(item.value, list) else [item.value]
        if (
            minimum
            and maximum
            and any(str(value) < str(minimum) or str(value) > str(maximum) for value in values)
        ):
            raise AppError(
                "date_range_unavailable",
                f"The requested date range is outside the available {minimum} to {maximum} range.",
            )


def _json_value(value: Any) -> Any:
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return str(value)
