import uuid

import pytest
from pydantic import ValidationError

from app.core.errors import AppError
from app.models import Dataset, DatasetColumn
from app.schemas.analysis import AnalysisPlan
from app.services.analysis_validation import validate_plan_for_dataset


def valid_plan(dataset_id: uuid.UUID) -> dict:
    return {
        "restated_question": "Compare total revenue by region.",
        "intent": "comparison",
        "selected_dataset": str(dataset_id),
        "metrics": [{"column": "revenue", "aggregation": "sum", "alias": "total_revenue"}],
        "dimensions": ["region"],
        "filters": [],
        "time_column": None,
        "time_granularity": None,
        "required_joins": [],
        "assumptions": ["Revenue means the revenue column."],
        "clarification_needed": False,
        "clarification_question": None,
        "suggested_chart": "bar",
        "approach": "Sum revenue and group the result by region.",
    }


def dataset_with_columns(dataset_id: uuid.UUID) -> Dataset:
    dataset = Dataset(
        id=dataset_id,
        name="Orders",
        original_filename="orders.csv",
        storage_key="orders.csv",
        media_type="text/csv",
        size_bytes=100,
        row_count=2,
        column_count=2,
        profile_status="ready",
        profile={},
    )
    dataset.columns = [
        DatasetColumn(
            name="region",
            position=0,
            data_type="VARCHAR",
            semantic_type="category",
            nullable=False,
            null_count=0,
            distinct_count=2,
            statistics={},
            sample_values=["North", "South"],
        ),
        DatasetColumn(
            name="revenue",
            position=1,
            data_type="DOUBLE",
            semantic_type="measure",
            nullable=False,
            null_count=0,
            distinct_count=2,
            statistics={"min": 10, "max": 20},
            sample_values=[10, 20],
        ),
    ]
    return dataset


def test_clarification_requires_a_question() -> None:
    payload = valid_plan(uuid.uuid4())
    payload["clarification_needed"] = True
    with pytest.raises(ValidationError, match="clarification_question"):
        AnalysisPlan.model_validate(payload)


def test_rejects_unknown_columns() -> None:
    dataset_id = uuid.uuid4()
    dataset = dataset_with_columns(dataset_id)
    payload = valid_plan(dataset_id)
    payload["dimensions"] = ["country"]
    with pytest.raises(AppError) as error:
        validate_plan_for_dataset(AnalysisPlan.model_validate(payload), dataset)
    assert error.value.code == "unknown_plan_columns"


def test_accepts_a_plan_grounded_in_the_dataset() -> None:
    dataset_id = uuid.uuid4()
    dataset = dataset_with_columns(dataset_id)
    plan = AnalysisPlan.model_validate(valid_plan(dataset_id))
    assert validate_plan_for_dataset(plan, dataset) == plan
