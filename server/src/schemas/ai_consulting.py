from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel


# Stocks (GUI管理銘柄)
class StockRecord(BaseModel):
    code: str  # 入力コード (例: "7203" or "7203.T")
    symbol: str  # 正規化済みコード: J-Quants形式 (例: "7203") / 旧yfinance形式 (例: "7203.T")
    name: Optional[str] = None  # 企業名
    enterprise_value: Optional[float] = None  # 企業価値
    market_cap: Optional[float] = None  # 時価総額
    per: Optional[float] = None  # PER
    revenue: Optional[float] = None  # 売上
    operating_income: Optional[float] = None  # 営利
    net_income: Optional[float] = None  # 純利
    dividend_yield: Optional[float] = None  # 配当利回り
    roe: Optional[float] = None  # ROE
    equity_ratio: Optional[float] = None  # 自己資本比率
    updated_at: Optional[datetime] = None


class AddStockRequest(BaseModel):
    code: str


class StocksResponse(BaseModel):
    stocks: List[StockRecord]


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
