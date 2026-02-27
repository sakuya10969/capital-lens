from fastapi import APIRouter, Depends, HTTPException
import logging

from src.schemas.market import MarketOverviewResponse
from src.services.market import MarketService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/market", tags=["Market"])


def get_market_service() -> MarketService:
    """MarketServiceの依存性プロバイダ。"""
    return MarketService()


@router.get("/overview", response_model=MarketOverviewResponse)
async def get_market_overview(
    service: MarketService = Depends(get_market_service),
) -> MarketOverviewResponse:
    """主要な市場指数、国債利回り、為替レート、および商品価格の高レベルなスナップショットを返します。
    """
    try:
        return await service.get_market_overview()
    except Exception as exc:
        logger.error("Unhandled error in /api/market/overview: %s", exc)
        raise HTTPException(
            status_code=503,
            detail="市場データの取得に失敗しました。しばらくしてから再度お試しください。",
        ) from exc
