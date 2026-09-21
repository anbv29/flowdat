import uuid
from datetime import UTC, datetime

from app.schemas.datasets import DatasetSummary


def test_dataset_summary_serializes_public_fields() -> None:
    now = datetime.now(UTC)
    summary = DatasetSummary(
        id=uuid.uuid4(),
        name="Orders",
        description=None,
        original_filename="orders.csv",
        media_type="text/csv",
        size_bytes=128,
        row_count=2,
        column_count=3,
        profile_status="ready",
        created_at=now,
        updated_at=now,
    )

    assert summary.name == "Orders"
    assert "storage_key" not in summary.model_dump()
