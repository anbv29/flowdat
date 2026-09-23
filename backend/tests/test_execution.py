import asyncio
import uuid
from pathlib import Path

import duckdb
import pytest

from app.api.query_runs import MAX_SQL_ATTEMPTS, should_correct
from app.core.errors import AppError
from app.models import Dataset, DatasetColumn
from app.schemas.analysis import AnalysisPlan
from app.services.analysis_provider import DatasetContext
from app.services.execution import execute_query, verify_result
from app.services.profiling import profile_dataset
from app.services.sql_generation import LocalSQLGenerationProvider, build_sql


def plan(dataset_id: uuid.UUID) -> AnalysisPlan:
    return AnalysisPlan.model_validate(
        {
            "restated_question": "Total revenue by region.",
            "intent": "comparison",
            "selected_dataset": dataset_id,
            "metrics": [{"column": "revenue", "aggregation": "sum", "alias": "total_revenue"}],
            "dimensions": ["region"],
            "filters": [],
            "time_column": None,
            "time_granularity": None,
            "required_joins": [],
            "assumptions": [],
            "clarification_needed": False,
            "clarification_question": None,
            "suggested_chart": "bar",
            "approach": "Sum revenue and group by region.",
        }
    )


def test_builds_and_executes_grouped_sql(tmp_path: Path) -> None:
    source = tmp_path / "orders.csv"
    source.write_text("region,revenue\nNorth,10\nSouth,20\nNorth,15\n")
    profile = profile_dataset(source)
    sql = build_sql(plan(uuid.uuid4()))
    columns, rows, _ = execute_query(Path(profile["duckdb_path"]), sql + " LIMIT 100", 5)
    verify_result(columns, rows)
    assert columns == ["region", "total_revenue"]
    assert rows == [
        {"region": "North", "total_revenue": 25.0},
        {"region": "South", "total_revenue": 20.0},
    ]


def test_local_sql_provider_labels_fallback_mode() -> None:
    dataset_id = uuid.uuid4()
    context = DatasetContext(
        id=str(dataset_id), name="Orders", description=None, row_count=1, columns=[]
    )
    result = asyncio.run(LocalSQLGenerationProvider().generate_sql(plan(dataset_id), context))
    assert result.mode == "local_fallback"
    assert 'SUM("revenue")' in result.sql


def test_empty_result_is_rejected() -> None:
    with pytest.raises(AppError, match="No rows matched") as caught:
        verify_result(["region"], [])
    assert caught.value.code == "empty_result"


def test_percentage_with_zero_denominator_is_rejected() -> None:
    payload = plan(uuid.uuid4()).model_dump(mode="json")
    payload["metrics"] = [
        {
            "column": "revenue",
            "aggregation": "percentage_change",
            "alias": "revenue_change",
        }
    ]
    percentage_plan = AnalysisPlan.model_validate(payload)
    with pytest.raises(AppError) as caught:
        verify_result(
            ["region", "revenue_change"],
            [{"region": "North", "revenue_change": None}],
            percentage_plan,
        )
    assert caught.value.code == "invalid_percentage_result"


def test_date_filter_outside_profile_range_is_rejected() -> None:
    dataset = Dataset(
        id=uuid.uuid4(),
        user_id=None,
        name="Orders",
        description=None,
        original_filename="orders.csv",
        storage_key="orders.csv",
        media_type="text/csv",
        size_bytes=10,
        row_count=100,
        column_count=2,
        profile_status="ready",
        profile={},
    )
    dataset.columns = [
        DatasetColumn(
            name="ordered_at",
            position=0,
            data_type="DATE",
            semantic_type="date",
            nullable=False,
            null_count=0,
            distinct_count=10,
            statistics={"min": "2026-01-01", "max": "2026-01-31"},
            sample_values=[],
        )
    ]
    payload = plan(dataset.id).model_dump(mode="json")
    payload["filters"] = [{"column": "ordered_at", "operator": "gte", "value": "2025-01-01"}]
    filtered_plan = AnalysisPlan.model_validate(payload)
    with pytest.raises(AppError) as caught:
        verify_result(
            ["region", "total_revenue"],
            [{"region": "North", "total_revenue": 10}],
            filtered_plan,
            dataset,
        )
    assert caught.value.code == "date_range_unavailable"


def test_duckdb_interrupt_becomes_friendly_timeout(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    class InterruptedConnection:
        def interrupt(self) -> None:
            pass

        def execute(self, sql: str) -> None:
            raise duckdb.InterruptException("interrupted")

        def close(self) -> None:
            pass

    monkeypatch.setattr(duckdb, "connect", lambda *args, **kwargs: InterruptedConnection())
    with pytest.raises(AppError) as caught:
        execute_query(tmp_path / "data.duckdb", "SELECT 1", 5)
    assert caught.value.code == "query_timeout"


def test_only_one_sql_correction_is_allowed() -> None:
    correctable = {"empty_result"}
    assert MAX_SQL_ATTEMPTS == 2
    assert should_correct(1, "empty_result", correctable)
    assert not should_correct(2, "empty_result", correctable)
    assert not should_correct(1, "statement_not_allowed", correctable)
