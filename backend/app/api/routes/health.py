from fastapi import APIRouter
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()


@router.get("/health")
def health_check() -> dict:
    logger.info("Health check requested")
    return {"status": "ok"}