from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel


class IpoItem(BaseModel):
    """Individual IPO listing entry."""

    company_name: str
    ticker: str
    market: str
    listing_date: date
    offering_price: Optional[float] = None
    summary: str
    generated_at: datetime


class IpoLatestResponse(BaseModel):
    """Wrapper response for the /api/ipo/latest endpoint."""

    items: List[IpoItem]
    total_count: int
    generated_at: datetime
