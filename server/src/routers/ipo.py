from fastapi import APIRouter, Depends, HTTPException
import logging

from src.schemas.ipo import IpoLatestResponse
from src.services.ipo import IpoService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ipo", tags=["IPO"])


def get_ipo_service() -> IpoService:
    """IpoServiceの依存性プロバイダ"""
    return IpoService()


@router.get("/latest", response_model=IpoLatestResponse)
async def get_latest_ipos(
    service: IpoService = Depends(get_ipo_service),
) -> IpoLatestResponse:
    """最近上場した銘柄(日本市場向け、JPXから取得)に関する構造化された情報を返却
    """
    try:
        return await service.get_latest_ipos()
    except Exception as exc:
        logger.error("Unhandled error in /api/ipo/latest: %s", exc)
        raise HTTPException(
            status_code=503,
            detail="IPOデータの取得に失敗しました。しばらくしてから再度お試しください。",
        ) from exc
