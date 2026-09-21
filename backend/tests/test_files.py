from pathlib import Path

import pytest
from fastapi import UploadFile

from app.core.errors import AppError
from app.services.files import store_upload


@pytest.mark.asyncio
async def test_rejects_an_unsupported_extension(tmp_path: Path) -> None:
    upload = UploadFile(filename="notes.txt", file=__import__("io").BytesIO(b"hello"))
    with pytest.raises(AppError, match="CSV or Parquet"):
        await store_upload(upload, tmp_path, 1024)


@pytest.mark.asyncio
async def test_stores_under_generated_name(tmp_path: Path) -> None:
    upload = UploadFile(filename="../../orders.csv", file=__import__("io").BytesIO(b"id,total\n1,25\n"), headers={"content-type": "text/csv"})
    stored = await store_upload(upload, tmp_path, 1024)
    assert stored.path.parent == tmp_path.resolve()
    assert stored.path.name != "orders.csv"
    assert stored.path.suffix == ".csv"
