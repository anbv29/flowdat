import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, Response, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.core.errors import AppError
from app.models import Dataset, DatasetColumn
from app.schemas.datasets import DatasetDetail, DatasetListResponse, DatasetSummary
from app.services.files import clean_display_name, store_upload
from app.services.profiling import profile_dataset

router = APIRouter(prefix="/datasets", tags=["datasets"])


@router.post("", response_model=DatasetDetail, status_code=status.HTTP_201_CREATED)
async def upload_dataset(
    file: UploadFile = File(...),
    name: str | None = Form(default=None, max_length=255),
    description: str | None = Form(default=None, max_length=2000),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> DatasetDetail:
    stored = await store_upload(file, settings.upload_dir, settings.max_upload_bytes)
    try:
        profile = profile_dataset(stored.path)
        dataset = Dataset(
            name=(name or clean_display_name(stored.original_filename)).strip(),
            description=description.strip() if description else None,
            original_filename=stored.original_filename,
            storage_key=stored.storage_key,
            media_type=stored.media_type,
            size_bytes=stored.size_bytes,
            row_count=profile["row_count"],
            column_count=profile["column_count"],
            profile_status="ready",
            profile={"preview": profile["preview"], "duckdb_path": profile["duckdb_path"]},
        )
        dataset.columns = [DatasetColumn(**column) for column in profile["columns"]]
        db.add(dataset)
        db.commit()
        db.refresh(dataset)
    except Exception:
        db.rollback()
        stored.path.unlink(missing_ok=True)
        stored.path.with_suffix(".duckdb").unlink(missing_ok=True)
        raise
    return _detail(dataset)


@router.get("", response_model=DatasetListResponse)
def list_datasets(db: Session = Depends(get_db)) -> DatasetListResponse:
    items = db.scalars(select(Dataset).order_by(Dataset.updated_at.desc())).all()
    total = db.scalar(select(func.count()).select_from(Dataset)) or 0
    return DatasetListResponse(items=[DatasetSummary.model_validate(item) for item in items], total=total)


@router.get("/{dataset_id}", response_model=DatasetDetail)
def get_dataset(dataset_id: uuid.UUID, db: Session = Depends(get_db)) -> DatasetDetail:
    dataset = db.scalar(
        select(Dataset).options(selectinload(Dataset.columns)).where(Dataset.id == dataset_id)
    )
    if not dataset:
        raise AppError("dataset_not_found", "That dataset is no longer available.", status_code=404)
    return _detail(dataset)


@router.delete("/{dataset_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_dataset(
    dataset_id: uuid.UUID,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> Response:
    dataset = db.get(Dataset, dataset_id)
    if not dataset:
        raise AppError("dataset_not_found", "That dataset is no longer available.", status_code=404)

    upload_root = settings.upload_dir.resolve()
    raw_path = (upload_root / dataset.storage_key).resolve()
    if upload_root in raw_path.parents:
        raw_path.unlink(missing_ok=True)
        raw_path.with_suffix(".duckdb").unlink(missing_ok=True)
    db.delete(dataset)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def _detail(dataset: Dataset) -> DatasetDetail:
    summary = DatasetSummary.model_validate(dataset).model_dump()
    return DatasetDetail(
        **summary,
        columns=[column for column in dataset.columns],
        preview=dataset.profile.get("preview", []),
    )
