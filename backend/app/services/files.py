import re
import uuid
from dataclasses import dataclass
from pathlib import Path

from fastapi import UploadFile

from app.core.errors import AppError

ALLOWED_TYPES = {
    ".csv": {"text/csv", "application/csv", "application/vnd.ms-excel", "application/octet-stream"},
    ".parquet": {"application/vnd.apache.parquet", "application/octet-stream"},
}
CHUNK_SIZE = 1024 * 1024


@dataclass(frozen=True)
class StoredUpload:
    original_filename: str
    storage_key: str
    path: Path
    media_type: str
    size_bytes: int


def clean_display_name(filename: str) -> str:
    stem = Path(filename).stem
    cleaned = re.sub(r"[_-]+", " ", stem).strip()
    return cleaned[:255] or "Untitled dataset"


async def store_upload(upload: UploadFile, upload_dir: Path, max_bytes: int) -> StoredUpload:
    original_name = Path(upload.filename or "").name
    extension = Path(original_name).suffix.lower()
    if extension not in ALLOWED_TYPES:
        raise AppError("unsupported_file_type", "Choose a CSV or Parquet file.")

    media_type = (upload.content_type or "application/octet-stream").lower()
    if media_type not in ALLOWED_TYPES[extension]:
        raise AppError(
            "invalid_media_type",
            "The file type does not match its extension.",
            details={"received": media_type},
        )

    upload_dir.mkdir(parents=True, exist_ok=True)
    storage_key = f"{uuid.uuid4().hex}{extension}"
    destination = (upload_dir / storage_key).resolve()
    root = upload_dir.resolve()
    if root not in destination.parents:
        raise AppError(
            "invalid_storage_path", "The upload could not be stored safely.", status_code=500
        )

    size = 0
    try:
        with destination.open("xb") as target:
            while chunk := await upload.read(CHUNK_SIZE):
                size += len(chunk)
                if size > max_bytes:
                    raise AppError(
                        "file_too_large",
                        f"This file exceeds the {max_bytes // 1024 // 1024} MB upload limit.",
                        status_code=413,
                    )
                target.write(chunk)
    except Exception:
        destination.unlink(missing_ok=True)
        raise
    finally:
        await upload.close()

    if size == 0:
        destination.unlink(missing_ok=True)
        raise AppError("empty_file", "The selected file is empty.")

    return StoredUpload(original_name, storage_key, destination, media_type, size)
