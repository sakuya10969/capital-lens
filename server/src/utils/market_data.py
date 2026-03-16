"""
yfinance を使った市場データ取得。

services/market.py から利用する。
"""

import logging
from typing import Optional

import yfinance as yf

from src.schemas.market import MarketItem

logger = logging.getLogger(__name__)


def fetch_market_item(name: str, ticker: str) -> Optional[MarketItem]:
    try:
        t = yf.Ticker(ticker)
        hist = t.history(period="5d")

        if hist.empty:
            logger.warning("No history data for %s (%s)", name, ticker)
            return None

        latest = hist.iloc[-1]
        prev = hist.iloc[-2] if len(hist) > 1 else latest

        curr_price = float(latest["Close"])
        prev_price = float(prev["Close"])
        change = curr_price - prev_price
        change_pct = (change / prev_price * 100) if prev_price != 0 else 0.0

        return MarketItem(
            name=name,
            current_price=round(curr_price, 4),
            change=round(change, 4),
            change_percent=round(change_pct, 4),
        )
    except Exception as exc:
        logger.error("yfinance error for %s (%s): %s", name, ticker, exc)
        return None
