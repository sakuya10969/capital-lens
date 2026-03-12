from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel


class IpoItem(BaseModel):
    """個別のIPO上場エントリー（軽量一覧用）"""
    company_name: str
    company_url: Optional[str] = None
    ticker: str
    market: str
    listing_date: date
    offering_price: Optional[float] = None
    outline_pdf_url: Optional[str] = None
    generated_at: datetime


class IpoLatestResponse(BaseModel):
    """/api/ipo/latest エンドポイントのラッパーレスポンス"""
    items: List[IpoItem]
    total_count: int
    generated_at: datetime


class IpoSummaryResponse(BaseModel):
    """/api/ipo/{code}/summary エンドポイントのレスポンス

    summary: Azure OpenAI が生成した日本語約200文字の短文要約
    cached:  True の場合はサーバーキャッシュから返却（再生成なし）
    """
    code: str
    summary: str
    cached: bool
    generated_at: datetime
