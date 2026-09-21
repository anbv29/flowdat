import pytest

from app.core.errors import AppError
from app.services.sql_safety import SQLSafetyService


@pytest.fixture
def safety() -> SQLSafetyService:
    return SQLSafetyService("dataset", {"region", "revenue", "ordered_at"}, max_rows=100)


@pytest.mark.parametrize(
    "sql",
    [
        "INSERT INTO dataset VALUES ('North', 10, DATE '2026-01-01')",
        "UPDATE dataset SET revenue = 0",
        "DELETE FROM dataset",
        "DROP TABLE dataset",
        "ALTER TABLE dataset ADD COLUMN secret TEXT",
        "CREATE TABLE copied AS SELECT * FROM dataset",
        "ATTACH 'private.db' AS private",
        "COPY dataset TO 'leak.csv'",
    ],
)
def test_rejects_mutating_and_external_statements(safety: SQLSafetyService, sql: str) -> None:
    with pytest.raises(AppError) as error:
        safety.validate(sql)
    assert error.value.code == "statement_not_allowed"


def test_rejects_multiple_statements(safety: SQLSafetyService) -> None:
    with pytest.raises(AppError) as error:
        safety.validate("SELECT * FROM dataset; DROP TABLE dataset")
    assert error.value.code == "multiple_statements"


def test_rejects_comments(safety: SQLSafetyService) -> None:
    with pytest.raises(AppError) as error:
        safety.validate("SELECT * FROM dataset -- harmless looking")
    assert error.value.code == "sql_comments_rejected"


def test_rejects_filesystem_functions(safety: SQLSafetyService) -> None:
    with pytest.raises(AppError) as error:
        safety.validate("SELECT * FROM read_csv_auto('/etc/passwd')")
    assert error.value.code == "filesystem_access_rejected"


def test_rejects_unknown_tables_and_columns(safety: SQLSafetyService) -> None:
    with pytest.raises(AppError) as table_error:
        safety.validate("SELECT * FROM private_data")
    assert table_error.value.code == "unknown_tables"

    with pytest.raises(AppError) as column_error:
        safety.validate("SELECT customer_email FROM dataset")
    assert column_error.value.code == "unknown_columns"


def test_adds_and_caps_result_limits(safety: SQLSafetyService) -> None:
    unbounded = safety.validate("SELECT region, SUM(revenue) AS total FROM dataset GROUP BY region")
    oversized = safety.validate("SELECT * FROM dataset LIMIT 5000")
    assert "LIMIT 100" in unbounded.sql
    assert "LIMIT 100" in oversized.sql
    assert unbounded.limit_applied is True


def test_accepts_ctes_over_the_allowed_dataset(safety: SQLSafetyService) -> None:
    validated = safety.validate(
        "WITH totals AS (SELECT region, SUM(revenue) AS total FROM dataset GROUP BY region) "
        "SELECT region, total FROM totals ORDER BY total DESC"
    )
    assert "WITH totals AS" in validated.sql
