from app.core.errors import AppError
from app.models import Dataset
from app.schemas.analysis import Aggregation, AnalysisPlan


def validate_plan_for_dataset(plan: AnalysisPlan, dataset: Dataset) -> AnalysisPlan:
    if plan.selected_dataset != dataset.id:
        raise AppError("dataset_mismatch", "The analysis plan targets a different dataset.")

    known_columns = {column.name for column in dataset.columns}
    referenced_columns = set(plan.dimensions)
    referenced_columns.update(item.column for item in plan.filters)
    if plan.time_column:
        referenced_columns.add(plan.time_column)
    referenced_columns.update(
        metric.column
        for metric in plan.metrics
        if metric.column is not None and metric.aggregation != Aggregation.COUNT
    )

    unknown_columns = sorted(referenced_columns - known_columns)
    if unknown_columns:
        raise AppError(
            "unknown_plan_columns",
            "The analysis plan refers to fields that are not in this dataset.",
            details={"columns": unknown_columns},
        )
    if plan.required_joins:
        raise AppError(
            "joins_not_available",
            "This workspace currently supports analysis within one dataset at a time.",
        )
    return plan
