from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel


# PER
class PerItem(BaseModel):
    name: str
    symbol: str
    price: Optional[float] = None
    currency: Optional[str] = None
    trailing_pe: Optional[float] = None
    forward_pe: Optional[float] = None
    trailing_eps: Optional[float] = None
    computed_pe: Optional[float] = None
    pe_used: Optional[str] = None  # "trailing" | "forward" | "computed" | None
    website: Optional[str] = None
    note: Optional[str] = None


class PerResponse(BaseModel):
    as_of: datetime
    items: List[PerItem]


# Earnings
class EarningsItem(BaseModel):
    name: str
    symbol: str
    earnings_date: Optional[date] = None
    price_change_5d: Optional[float] = None
    price_change_1m: Optional[float] = None
    trailing_pe: Optional[float] = None
    summary: Optional[str] = None
    website: Optional[str] = None
    note: Optional[str] = None


class EarningsWindow(BaseModel):
    from_date: date
    to_date: date
    days: int


class EarningsResponse(BaseModel):
    as_of: datetime
    window: EarningsWindow
    upcoming: List[EarningsItem]
    unknown: List[EarningsItem]


# Report
class ReportResponse(BaseModel):
    as_of: datetime
    per: PerResponse
    earnings: EarningsResponse
    text_report: str
