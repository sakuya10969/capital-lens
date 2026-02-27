from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel


class IpoItem(BaseModel):
    """個別のIPO上場エントリー"""

    company_name: str
    ticker: str
    market: str
    listing_date: date
    offering_price: Optional[float] = None
    summary: str
    generated_at: datetime


class IpoLatestResponse(BaseModel):
    """/api/ipo/latest エンドポイントのラッパーレスポンス"""

    items: List[IpoItem]
    total_count: int
    generated_at: datetime
