import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

import yfinance as yf

from src.core.config import settings
from src.schemas.market import MarketItem, MarketOverviewResponse

logger = logging.getLogger(__name__)

MARKET_SYMBOLS: Dict[str, List[Dict[str, Any]]] = {
    "indices": [
        {"name": "日経平均", "ticker": "^N225"},
        {"name": "TOPIX", "ticker": "^TPX"},
        {"name": "S&P 500", "ticker": "^GSPC"},
        {"name": "NASDAQ", "ticker": "^IXIC"},
        {"name": "ダウ平均", "ticker": "^DJI"},
    ],
    "bonds": [
        {"name": "米10年国債利回り", "ticker": "^TNX"},
    ],
    "fx": [
        {"name": "USD/JPY", "ticker": "USDJPY=X"},
    ],
    "commodities": [
        {"name": "WTI原油", "ticker": "CL=F"},
        {"name": "金", "ticker": "GC=F"},
    ],
}


def _fetch_yfinance_item(name: str, ticker: str) -> Optional[MarketItem]:
    """yfinanceから単一のマーケットアイテムを取得

    一つのティッカーのエラーでレスポンス全体が壊れないように、失敗時には ``None`` を返却
    """
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


class MarketService:
    """yfinanceを介した市場データの取得をオーケストレーション"""

    async def get_market_overview(self) -> MarketOverviewResponse:
        """統合された市場の概要を返却

        すべてのアイテムは、アイテムごとのタイムアウト付きで並行して取得
        """

        async def _fetch_with_timeout(
            name: str, ticker: str, timeout: float
        ) -> Optional[MarketItem]:
            try:
                return await asyncio.wait_for(
                    asyncio.to_thread(_fetch_yfinance_item, name, ticker),
                    timeout=timeout,
                )
            except asyncio.TimeoutError:
                logger.warning("Timeout fetching %s (%s)", name, ticker)
                return None

        yf_timeout = float(settings.YFINANCE_TIMEOUT)
        category_order = ["indices", "bonds", "fx", "commodities"]
        tasks: List = []
        category_sizes: Dict[str, int] = {}

        for cat in category_order:
            items = MARKET_SYMBOLS[cat]
            category_sizes[cat] = len(items)
            for item in items:
                tasks.append(
                    _fetch_with_timeout(item["name"], item["ticker"], yf_timeout)
                )

        results = await asyncio.gather(*tasks)

        offset = 0
        categorised: Dict[str, List[MarketItem]] = {}
        for cat in category_order:
            size = category_sizes[cat]
            categorised[cat] = [
                r for r in results[offset : offset + size] if r is not None
            ]
            offset += size

        return MarketOverviewResponse(
            indices=categorised["indices"],
            bonds=categorised["bonds"],
            fx=categorised["fx"],
            commodities=categorised["commodities"],
            generated_at=datetime.utcnow(),
        )
