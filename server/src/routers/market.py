from fastapi import APIRouter, Depends, HTTPException
import logging

from src.schemas.market import MarketOverviewResponse
from src.services.market import MarketService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/market", tags=["Market"])


def get_market_service() -> MarketService:
    """Dependency provider for MarketService."""
    return MarketService()


@router.get("/overview", response_model=MarketOverviewResponse)
async def get_market_overview(
    service: MarketService = Depends(get_market_service),
) -> MarketOverviewResponse:
    """Return a high-level snapshot of major market indices, bond yields,
    FX rates, and commodity prices.
    """
    try:
        return await service.get_market_overview()
    except Exception as exc:
        logger.error("Unhandled error in /api/market/overview: %s", exc)
        raise HTTPException(
            status_code=503,
            detail="市場データの取得に失敗しました。しばらくしてから再度お試しください。",
        ) from exc
