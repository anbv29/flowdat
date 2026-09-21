import math
import threading
import time
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import duckdb

from app.core.errors import AppError


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


def verify_result(columns: list[str], rows: list[dict[str, Any]]) -> None:
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
