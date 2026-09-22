import uuid
from typing import Any

from app.schemas.analysis import StrictModel


class EvaluationSummary(StrictModel):
    total_cases: int
    passed_cases: int
    sql_validity_rate: float
    execution_success_rate: float
    result_correctness_rate: float
    clarification_quality_rate: float
    unsafe_rejection_rate: float
    average_latency_ms: float
    estimated_model_cost_usd: float


class EvaluationFailure(StrictModel):
    id: uuid.UUID
    case_name: str
    question: str
    category: str
    actual_outcome: str
    expected: dict[str, Any]
    failure_reason: str | None


class EvaluationReport(StrictModel):
    summary: EvaluationSummary
    failures: list[EvaluationFailure]
