import uuid

from app.api.evaluations import build_report
from app.models import EvaluationCase, EvaluationRun


def test_report_aggregates_rates_and_failures() -> None:
    case_id = uuid.uuid4()
    case = EvaluationCase(
        id=case_id,
        name="total",
        question="Total?",
        category="simple",
        expected={"outcome": "success"},
        active=True,
    )
    run = EvaluationRun(
        id=uuid.uuid4(),
        evaluation_case_id=case_id,
        status="failed",
        scores={
            "sql_validity": 1,
            "execution_success": 1,
            "result_correctness": 0,
            "clarification_quality": 0,
            "unsafe_query_rejection": 0,
            "actual_outcome": "success",
            "question": "Total?",
            "category": "simple",
            "expected": {"outcome": "success"},
        },
        latency_ms=25,
        estimated_cost_usd=0.001,
        failure_reason="Wrong result",
    )
    report = build_report([case], [run])
    assert report.summary.sql_validity_rate == 100
    assert report.summary.passed_cases == 0
    assert report.failures[0].case_name == "total"
