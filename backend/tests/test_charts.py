import uuid

from app.schemas.analysis import AnalysisPlan
from app.schemas.results import ChartConfig
from app.services.answers import choose_chart


def make_plan(intent: str, suggested: str) -> AnalysisPlan:
    return AnalysisPlan.model_validate(
        {
            "restated_question": "Inspect the result.",
            "intent": intent,
            "selected_dataset": uuid.uuid4(),
            "metrics": [{"column": "revenue", "aggregation": "sum", "alias": "total"}],
            "dimensions": ["region"],
            "filters": [],
            "time_column": None,
            "time_granularity": None,
            "required_joins": [],
            "assumptions": [],
            "clarification_needed": False,
            "clarification_question": None,
            "suggested_chart": suggested,
            "approach": "Return the requested result.",
        }
    )


def test_single_value_uses_kpi() -> None:
    chart = choose_chart(make_plan("aggregation", "bar"), ["total"], [{"total": 42}])
    assert chart.type == "kpi"


def test_relationship_uses_scatter() -> None:
    chart: ChartConfig = choose_chart(
        make_plan("relationship", "bar"), ["quantity", "revenue"], [{"quantity": 1, "revenue": 20}]
    )
    assert chart.type == "scatter"


def test_large_part_to_whole_falls_back_to_bar() -> None:
    rows = [{"region": str(index), "total": index} for index in range(12)]
    chart = choose_chart(make_plan("comparison", "donut"), ["region", "total"], rows)
    assert chart.type == "bar"
