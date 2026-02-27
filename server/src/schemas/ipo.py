from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel


class IpoItem(BaseModel):
    """個別のIPO上場エントリー（軽量一覧用）"""

    company_name: str
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

    bullets: Azure OpenAI が生成した 4〜8 箇条書き要約
    cached:  True の場合はサーバーキャッシュから返却（再生成なし）
    """

    code: str
    bullets: List[str]
    cached: bool
    generated_at: datetime
