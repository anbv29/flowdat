import asyncio
import uuid
from pathlib import Path

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
