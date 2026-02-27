from fastapi import APIRouter, Depends, HTTPException
import logging

from src.schemas.ipo import IpoLatestResponse, IpoSummaryResponse
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
    """最近上場した銘柄の軽量一覧を返す（PDF/LLM 呼び出しなし）"""
    try:
        return await service.get_latest_ipos()
    except Exception as exc:
        logger.error("Unhandled error in /api/ipo/latest: %s", exc)
        raise HTTPException(
            status_code=503,
            detail="IPOデータの取得に失敗しました。しばらくしてから再度お試しください。",
        ) from exc


@router.get("/{code}/summary", response_model=IpoSummaryResponse)
async def get_ipo_summary(
    code: str,
    service: IpoService = Depends(get_ipo_service),
) -> IpoSummaryResponse:
    """指定銘柄の企業概要を PDF → Azure OpenAI で要約して返す（サーバー 24h キャッシュ）"""
    try:
        return await service.get_ipo_summary(code)
    except Exception as exc:
        logger.error("Unhandled error in /api/ipo/%s/summary: %s", code, exc)
        raise HTTPException(
            status_code=503,
            detail=f"銘柄 {code} の要約取得に失敗しました。しばらくしてから再度お試しください。",
        ) from exc
