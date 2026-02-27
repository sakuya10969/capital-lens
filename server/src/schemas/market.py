from datetime import datetime
from typing import List
from pydantic import BaseModel

class MarketItem(BaseModel):
    name: str
    current_price: float
    change: float
    change_percent: float

class MarketOverviewResponse(BaseModel):
    indices: List[MarketItem]
    risk_indicators: List[MarketItem]
    bonds: List[MarketItem]
    fx: List[MarketItem]
    commodities: List[MarketItem]
    generated_at: datetime
