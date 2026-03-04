import logging

from fastapi import APIRouter, Depends, Query

from src.schemas.ai_consulting import EarningsResponse, PerResponse, ReportResponse
from src.services.ai_consulting import AiConsultingService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ai-consulting", tags=["AI Consulting"])


def get_service() -> AiConsultingService:
    return AiConsultingService()


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
