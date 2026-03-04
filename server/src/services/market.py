import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from src.utils.yfinance import fetch_market_item

from src.core.config import settings
from src.schemas.market import MarketItem, MarketOverviewResponse

logger = logging.getLogger(__name__)

MARKET_SYMBOLS: Dict[str, List[Dict[str, Any]]] = {
    "indices": [
        {"name": "日経平均", "ticker": "^N225"},
        {"name": "TOPIX", "ticker": "1306.T"},
        {"name": "東証グロース250", "ticker": "2516.T"},
        {"name": "S&P 500", "ticker": "^GSPC"},
        {"name": "NASDAQ", "ticker": "^IXIC"},
        {"name": "ダウ平均", "ticker": "^DJI"},
        {"name": "SOX指数", "ticker": "^SOX"},
    ],
    "risk_indicators": [
        {"name": "VIX恐怖指数", "ticker": "^VIX"},
        {"name": "ビットコイン", "ticker": "BTC-USD"},
    ],
    "bonds": [
        {"name": "米2年国債利回り", "ticker": "^IRX"},
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
                    asyncio.to_thread(fetch_market_item, name, ticker),
                    timeout=timeout,
                )
            except asyncio.TimeoutError:
                logger.warning("Timeout fetching %s (%s)", name, ticker)
                return None

        yf_timeout = float(settings.YFINANCE_TIMEOUT)
        category_order = [
            "indices",
            "risk_indicators",
            "bonds",
            "fx",
            "commodities",
        ]
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
            risk_indicators=categorised["risk_indicators"],
            bonds=categorised["bonds"],
            fx=categorised["fx"],
            commodities=categorised["commodities"],
            generated_at=datetime.utcnow(),
        )
