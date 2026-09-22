from typing import Any

from app.schemas.analysis import AnalysisPlan, ChartType
from app.schemas.results import AnalysisAnswer, ChartConfig


def build_answer(
    plan: AnalysisPlan,
    columns: list[str],
    rows: list[dict[str, Any]],
    sql: str,
    execution_time_ms: float,
    verification_warnings: list[str] | None = None,
) -> AnalysisAnswer:
    first = rows[0]
    if len(rows) == 1 and len(columns) == 1:
        direct = f"The result is {format_value(first[columns[0]])}."
    else:
        direct = (
            f"The analysis returned {len(rows):,} result rows for "
            f"{plan.restated_question.rstrip('.')}."
        )
    evidence = [
        f"{', '.join(f'{key}: {format_value(value)}' for key, value in row.items())}"
        for row in rows[:5]
    ]
    chart = choose_chart(plan, columns, rows)
    return AnalysisAnswer(
        direct_answer=direct,
        evidence=evidence,
        columns=columns,
        rows=rows,
        chart=chart,
        assumptions=plan.assumptions,
        limitations=[
            "This describes the returned data and does not establish causation.",
            *(verification_warnings or []),
        ],
        generated_sql=sql,
        row_count=len(rows),
        execution_time_ms=round(execution_time_ms, 2),
        suggested_follow_ups=[
            "Break this result down by another category",
            "Compare this with the previous period",
        ],
    )


def choose_chart(plan: AnalysisPlan, columns: list[str], rows: list[dict[str, Any]]) -> ChartConfig:
    if len(rows) == 1 and len(columns) == 1:
        return ChartConfig(type=ChartType.KPI, y_keys=[columns[0]])
    if len(columns) < 2 or plan.suggested_chart in {ChartType.NONE, ChartType.TABLE}:
        return ChartConfig(type=ChartType.TABLE)
    return ChartConfig(type=plan.suggested_chart, x_key=columns[0], y_keys=columns[1:3])


def format_value(value: Any) -> str:
    if isinstance(value, float):
        return f"{value:,.2f}"
    if isinstance(value, int):
        return f"{value:,}"
    return str(value)
