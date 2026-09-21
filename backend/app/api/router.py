from fastapi import APIRouter

from app.api.datasets import router as datasets_router

router = APIRouter()
router.include_router(datasets_router)


@router.get("/health", tags=["system"])
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}
