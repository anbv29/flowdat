import uuid

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.errors import AppError
from app.models import QueryRun, SavedInsight
from app.schemas.insights import SavedInsightResponse, SaveInsightRequest

router = APIRouter(prefix="/insights", tags=["insights"])


@router.post("", response_model=SavedInsightResponse, status_code=status.HTTP_201_CREATED)
def save_insight(body: SaveInsightRequest, db: Session = Depends(get_db)) -> SavedInsight:
    query_run = db.get(QueryRun, body.query_run_id)
    if not query_run or query_run.execution_status != "completed":
        raise AppError(
            "query_run_not_complete",
            "Only a completed analysis can be saved as an insight.",
        )
    existing = db.scalar(select(SavedInsight).where(SavedInsight.query_run_id == query_run.id))
    if existing:
        existing.title = body.title.strip()
        existing.note = body.note.strip() if body.note else None
        db.commit()
        db.refresh(existing)
        return existing
    insight = SavedInsight(
        dataset_id=query_run.dataset_id,
        query_run_id=query_run.id,
        title=body.title.strip(),
        note=body.note.strip() if body.note else None,
    )
    db.add(insight)
    db.commit()
    db.refresh(insight)
    return insight


@router.get("", response_model=list[SavedInsightResponse])
def list_insights(db: Session = Depends(get_db)) -> list[SavedInsight]:
    return list(db.scalars(select(SavedInsight).order_by(SavedInsight.updated_at.desc())).all())


@router.delete("/{insight_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_insight(insight_id: uuid.UUID, db: Session = Depends(get_db)) -> Response:
    insight = db.get(SavedInsight, insight_id)
    if not insight:
        raise AppError(
            "insight_not_found", "That saved insight is no longer available.", status_code=404
        )
    db.delete(insight)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
