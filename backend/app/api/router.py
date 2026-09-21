from fastapi import APIRouter

from app.api.conversations import router as conversations_router
from app.api.datasets import router as datasets_router
from app.api.query_runs import router as query_runs_router

router = APIRouter()
router.include_router(conversations_router)
router.include_router(datasets_router)
router.include_router(query_runs_router)


@router.get("/health", tags=["system"])
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}
