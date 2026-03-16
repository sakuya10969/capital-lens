import logging

from fastapi import APIRouter, Depends, HTTPException, Query

from src.schemas.ai_consulting import (
    AddStockRequest,
    EarningsResponse,
    PerResponse,
    ReportResponse,
    StocksResponse,
)
from src.services.ai_consulting import AiConsultingService, StocksService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ai-consulting", tags=["AI Consulting"])


def get_service() -> AiConsultingService:
    return AiConsultingService()


def get_stocks_service() -> StocksService:
    return StocksService()


# ── GUI管理銘柄 (stocks) ──────────────────────────────────────────────────────


@router.get("/stocks", response_model=StocksResponse)
def list_stocks(
    service: StocksService = Depends(get_stocks_service),
) -> StocksResponse:
    """JSON保存済みの銘柄一覧を返す"""
    return service.list_stocks()


@router.post("/stocks", response_model=StocksResponse)
async def add_stock(
    body: AddStockRequest,
    service: StocksService = Depends(get_stocks_service),
) -> StocksResponse:
    """銘柄コードを追加し、yfinanceからデータを取得して保存する"""
    try:
        return await service.add_stock(body.code)
    except Exception as exc:
        logger.error("add_stock error: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.delete("/stocks/{code}", response_model=StocksResponse)
async def delete_stock(
    code: str,
    service: StocksService = Depends(get_stocks_service),
) -> StocksResponse:
    """銘柄を削除してJSONを更新する"""
    return await service.delete_stock(code)


@router.post("/stocks/{code}/refresh", response_model=StocksResponse)
async def refresh_stock(
    code: str,
    service: StocksService = Depends(get_stocks_service),
) -> StocksResponse:
    """指定銘柄のデータをyfinanceから再取得して更新する"""
    try:
        return await service.refresh_stock(code)
    except Exception as exc:
        logger.error("refresh_stock error %s: %s", code, exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/stocks/refresh-all", response_model=StocksResponse)
async def refresh_all_stocks(
    service: StocksService = Depends(get_stocks_service),
) -> StocksResponse:
    """全銘柄のデータをyfinanceから再取得して更新する"""
    try:
        return await service.refresh_all()
    except Exception as exc:
        logger.error("refresh_all error: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


# ── 既存エンドポイント (後方互換) ─────────────────────────────────────────────


@router.get("/per", response_model=PerResponse)
async def get_per(
    service: AiConsultingService = Depends(get_service),
) -> PerResponse:
    """AI×コンサル銘柄のPER一覧を返します。"""
    return await service.get_per()


@router.get("/earnings", response_model=EarningsResponse)
async def get_earnings(
    window_days: int = Query(default=7, ge=1, le=30),
    service: AiConsultingService = Depends(get_service),
) -> EarningsResponse:
    """決算期（今日±window_days日）を迎える銘柄の簡易解説を返します。"""
    return await service.get_earnings(window_days)


@router.post("/report", response_model=ReportResponse)
async def get_report(
    window_days: int = Query(default=7, ge=1, le=30),
    service: AiConsultingService = Depends(get_service),
) -> ReportResponse:
    """PER + 決算期 + テキストレポートをまとめて返します。"""
    return await service.get_report(window_days)
