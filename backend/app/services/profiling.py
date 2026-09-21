import math
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import duckdb

from app.core.errors import AppError

NUMERIC_TYPES = {"TINYINT", "SMALLINT", "INTEGER", "BIGINT", "HUGEINT", "UTINYINT", "USMALLINT", "UINTEGER", "UBIGINT", "FLOAT", "DOUBLE", "DECIMAL", "REAL"}
DATE_TYPES = {"DATE", "TIMESTAMP", "TIMESTAMP WITH TIME ZONE", "TIMESTAMP_NS", "TIMESTAMP_MS", "TIMESTAMP_S"}


def quote_identifier(value: str) -> str:
    return f'"{value.replace(chr(34), chr(34) * 2)}"'


def profile_dataset(source: Path) -> dict[str, Any]:
    database_path = source.with_suffix(".duckdb")
    loader = "read_csv_auto(?, sample_size = -1, normalize_names = false)" if source.suffix == ".csv" else "read_parquet(?)"

    try:
        with duckdb.connect(str(database_path)) as connection:
            connection.execute("DROP TABLE IF EXISTS dataset")
            connection.execute(f"CREATE TABLE dataset AS SELECT * FROM {loader}", [str(source)])
            schema = connection.execute("DESCRIBE dataset").fetchall()
            row_count = connection.execute("SELECT COUNT(*) FROM dataset").fetchone()[0]
            columns = [
                _profile_column(connection, name=row[0], data_type=row[1], row_count=row_count, position=index)
                for index, row in enumerate(schema)
            ]
            preview_rows = connection.execute("SELECT * FROM dataset LIMIT 8").fetchall()
    except (duckdb.Error, UnicodeDecodeError) as exc:
        database_path.unlink(missing_ok=True)
        raise AppError(
            "profiling_failed",
            "SignalDesk could not read this file. Check that it is a valid CSV or Parquet dataset.",
            details={"reason": exc.__class__.__name__},
        ) from exc

    names = [row[0] for row in schema]
    return {
        "row_count": row_count,
        "column_count": len(columns),
        "columns": columns,
        "preview": [dict(zip(names, (_json_value(value) for value in row), strict=True)) for row in preview_rows],
        "duckdb_path": str(database_path),
    }


def _profile_column(
    connection: duckdb.DuckDBPyConnection,
    *,
    name: str,
    data_type: str,
    row_count: int,
    position: int,
) -> dict[str, Any]:
    column = quote_identifier(name)
    null_count, distinct_count = connection.execute(
        f"SELECT COUNT(*) FILTER (WHERE {column} IS NULL), COUNT(DISTINCT {column}) FROM dataset"
    ).fetchone()
    base_type = data_type.split("(", 1)[0].upper()
    statistics: dict[str, Any] = {
        "null_percentage": round((null_count / row_count * 100) if row_count else 0, 2)
    }

    if base_type in NUMERIC_TYPES:
        minimum, maximum, mean, median = connection.execute(
            f"SELECT MIN({column}), MAX({column}), AVG({column}), MEDIAN({column}) FROM dataset"
        ).fetchone()
        statistics.update(min=_json_value(minimum), max=_json_value(maximum), mean=_json_value(mean), median=_json_value(median))
    elif base_type in DATE_TYPES:
        minimum, maximum = connection.execute(
            f"SELECT MIN({column}), MAX({column}) FROM dataset"
        ).fetchone()
        statistics.update(min=_json_value(minimum), max=_json_value(maximum))

    samples = connection.execute(
        f"SELECT DISTINCT {column} FROM dataset WHERE {column} IS NOT NULL LIMIT 5"
    ).fetchall()
    return {
        "name": name,
        "position": position,
        "data_type": data_type,
        "semantic_type": _semantic_type(name, base_type, distinct_count, row_count),
        "nullable": null_count > 0,
        "null_count": null_count,
        "distinct_count": distinct_count,
        "statistics": statistics,
        "sample_values": [_json_value(row[0]) for row in samples],
    }


def _semantic_type(name: str, data_type: str, distinct_count: int, row_count: int) -> str:
    lowered = name.lower()
    if data_type in DATE_TYPES or any(token in lowered for token in ("date", "time", "month", "year")):
        return "date"
    if lowered == "id" or lowered.endswith("_id") or (row_count > 0 and distinct_count == row_count):
        return "identifier"
    if data_type in NUMERIC_TYPES:
        return "measure"
    return "category"


def _json_value(value: Any) -> Any:
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, Decimal):
        result = float(value)
        return result if math.isfinite(result) else None
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return str(value)[:200]
