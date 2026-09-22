import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.core.errors import AppError
from app.models import Dataset, EvaluationCase, EvaluationRun
from app.schemas.evaluations import EvaluationFailure, EvaluationReport, EvaluationSummary
from app.services.evaluations import evaluate_case

router = APIRouter(prefix="/evaluations", tags=["evaluations"])


@router.post("/run", response_model=EvaluationReport)
async def run_evaluations(
    dataset_id: uuid.UUID = Query(...),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> EvaluationReport:
    dataset = db.scalar(
        select(Dataset).options(selectinload(Dataset.columns)).where(Dataset.id == dataset_id)
    )
    if not dataset:
        raise AppError("dataset_not_found", "Choose an available dataset.", status_code=404)
    cases = list(
        db.scalars(
            select(EvaluationCase)
            .where(EvaluationCase.active.is_(True))
            .order_by(EvaluationCase.name)
        ).all()
    )
    if not cases:
        raise AppError("evaluation_cases_missing", "Seed the evaluation benchmark first.")
    runs: list[EvaluationRun] = []
    for case in cases:
        outcome = await evaluate_case(case, dataset, settings)
        run = EvaluationRun(
            evaluation_case_id=case.id,
            status=outcome.status,
            scores=outcome.scores,
            latency_ms=outcome.latency_ms,
            estimated_cost_usd=outcome.estimated_cost_usd,
            failure_reason=outcome.failure_reason,
        )
        db.add(run)
        runs.append(run)
    db.commit()
    for run in runs:
        db.refresh(run)
    return build_report(cases, runs)


@router.get("/summary", response_model=EvaluationReport)
def evaluation_summary(db: Session = Depends(get_db)) -> EvaluationReport:
    cases = {item.id: item for item in db.scalars(select(EvaluationCase)).all()}
    latest: dict[uuid.UUID, EvaluationRun] = {}
    for run in db.scalars(select(EvaluationRun).order_by(EvaluationRun.created_at.desc())).all():
        latest.setdefault(run.evaluation_case_id, run)
    selected_cases = [cases[case_id] for case_id in latest if case_id in cases]
    return build_report(selected_cases, [latest[case.id] for case in selected_cases])


def build_report(cases: list[EvaluationCase], runs: list[EvaluationRun]) -> EvaluationReport:
    total = len(runs)

    def metric(name: str) -> float:
        if not total:
            return 0.0
        return round(sum(float(run.scores.get(name, 0)) for run in runs) / total * 100, 1)

    case_by_id = {case.id: case for case in cases}
    failures = [
        EvaluationFailure(
            id=run.id,
            case_name=case_by_id[run.evaluation_case_id].name,
            question=run.scores.get("question", ""),
            category=run.scores.get("category", "unknown"),
            actual_outcome=run.scores.get("actual_outcome", "unknown"),
            expected=run.scores.get("expected", {}),
            failure_reason=run.failure_reason,
        )
        for run in runs
        if run.status != "passed" and run.evaluation_case_id in case_by_id
    ]
    return EvaluationReport(
        summary=EvaluationSummary(
            total_cases=total,
            passed_cases=sum(run.status == "passed" for run in runs),
            sql_validity_rate=metric("sql_validity"),
            execution_success_rate=metric("execution_success"),
            result_correctness_rate=metric("result_correctness"),
            clarification_quality_rate=metric("clarification_quality"),
            unsafe_rejection_rate=metric("unsafe_query_rejection"),
            average_latency_ms=round(sum(run.latency_ms or 0 for run in runs) / total, 1)
            if total
            else 0,
            estimated_model_cost_usd=round(sum(run.estimated_cost_usd or 0 for run in runs), 6),
        ),
        failures=failures,
    )
