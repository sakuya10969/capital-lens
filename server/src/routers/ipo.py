from fastapi import APIRouter, Depends, HTTPException
import logging

from src.schemas.ipo import IpoLatestResponse
from src.services.ipo import IpoService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ipo", tags=["IPO"])


def get_ipo_service() -> IpoService:
    """Dependency provider for IpoService."""
    return IpoService()


@router.get("/latest", response_model=IpoLatestResponse)
async def get_latest_ipos(
    service: IpoService = Depends(get_ipo_service),
) -> IpoLatestResponse:
    """Return structured information about recently listed stocks
    (Japan-focused, sourced from JPX).
    """
    try:
        return await service.get_latest_ipos()
    except Exception as exc:
        logger.error("Unhandled error in /api/ipo/latest: %s", exc)
        raise HTTPException(
            status_code=503,
            detail="IPOデータの取得に失敗しました。しばらくしてから再度お試しください。",
        ) from exc
