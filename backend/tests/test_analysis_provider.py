import asyncio
import uuid

from app.schemas.analysis import ChartType
from app.services.analysis_provider import ContextColumn, DatasetContext, LocalAnalysisPlanProvider


def context() -> DatasetContext:
    return DatasetContext(
        id=str(uuid.uuid4()),
        name="Orders",
        description=None,
        row_count=40,
        columns=[
            ContextColumn(
                name="region",
                data_type="VARCHAR",
                semantic_type="category",
                null_percentage=0,
                distinct_count=4,
                statistics={},
                representative_values=["North", "South"],
            ),
            ContextColumn(
                name="revenue",
                data_type="DOUBLE",
                semantic_type="measure",
                null_percentage=0,
                distinct_count=39,
                statistics={"min": 40, "max": 230},
                representative_values=[116, 52.2],
            ),
            ContextColumn(
                name="ordered_at",
                data_type="DATE",
                semantic_type="date",
                null_percentage=0,
                distinct_count=40,
                statistics={"min": "2026-01-03", "max": "2026-06-24"},
                representative_values=["2026-01-03"],
            ),
        ],
    )


def test_local_planner_builds_grouped_revenue_plan() -> None:
    result = asyncio.run(
        LocalAnalysisPlanProvider().create_plan("Total revenue by region", context())
    )
    assert result.plan.metrics[0].column == "revenue"
    assert result.plan.dimensions == ["region"]
    assert result.plan.suggested_chart == ChartType.BAR
    assert result.mode == "local_fallback"


def test_local_planner_asks_when_measure_is_missing() -> None:
    result = asyncio.run(LocalAnalysisPlanProvider().create_plan("How is performance?", context()))
    assert result.plan.clarification_needed is True
    assert result.plan.clarification_question
