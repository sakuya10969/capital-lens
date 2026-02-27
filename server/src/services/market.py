import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

import yfinance as yf
from fredapi import Fred

from src.core.config import settings
from src.core.exceptions import ExternalAPIError
from src.schemas.market import MarketItem, MarketOverviewResponse

logger = logging.getLogger(__name__)

# Symbol definitions

MARKET_SYMBOLS: Dict[str, List[Dict[str, Any]]] = {
    "indices": [
        {"name": "日経平均", "ticker": "^N225"},
        {"name": "TOPIX", "ticker": "1306.T"},
        {"name": "S&P 500", "ticker": "^GSPC"},
        {"name": "NASDAQ", "ticker": "^IXIC"},
        {"name": "ダウ平均", "ticker": "^DJI"},
    ],
    "bonds": [
        {"name": "日本10年国債利回り", "ticker": "^TNX"},
    ],
    "fx": [
        {"name": "USD/JPY", "ticker": "JPY=X"},
    ],
    "commodities": [
        {"name": "WTI原油", "ticker": "CL=F"},
        {"name": "金", "ticker": "GC=F"},
    ],
}


# Individual fetcher functions (synchronous — run via asyncio.to_thread)


def _fetch_yfinance_item(name: str, ticker: str) -> Optional[MarketItem]:
    """Fetch a single market item from yfinance.

    Returns ``None`` if the data cannot be retrieved instead of raising,
    so that a single ticker failure doesn't break the whole response.
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
    except Exception as exc:  # noqa: BLE001
        logger.error("yfinance error for %s (%s): %s", name, ticker, exc)
        return None


def _fetch_fred_us10y() -> Optional[MarketItem]:
    """Fetch US 10-Year Treasury yield from FRED (series DGS10).

    Returns ``None`` when the API key is missing or the call fails.
    """
    if not settings.FRED_API_KEY:
        logger.warning("FRED_API_KEY is not set — skipping US 10Y Treasury yield.")
        return None

    try:
        fred = Fred(api_key=settings.FRED_API_KEY)
        series = fred.get_series("DGS10").dropna()

        if len(series) < 2:
            return None

        curr = float(series.iloc[-1])
        prev = float(series.iloc[-2])
        change = curr - prev
        change_pct = (change / prev * 100) if prev != 0 else 0.0

        return MarketItem(
            name="米国10年国債利回り",
            current_price=round(curr, 4),
            change=round(change, 4),
            change_percent=round(change_pct, 4),
        )
    except Exception as exc:  # noqa: BLE001
        logger.error("FRED fetch error: %s", exc)
        return None


# ---------------------------------------------------------------------------
# Service class
# ---------------------------------------------------------------------------


class MarketService:
    """Orchestrates market data retrieval from multiple sources."""

    async def get_market_overview(self) -> MarketOverviewResponse:
        """Return a consolidated market overview snapshot.

        All yfinance items are fetched concurrently with per-item timeout.
        FRED is fetched in parallel as well.
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
        fred_timeout = float(settings.FRED_TIMEOUT)

        # Build coroutine list for all yfinance items across categories
        category_order = ["indices", "bonds", "fx", "commodities"]
        yf_tasks: List[asyncio.Task] = []
        category_sizes: Dict[str, int] = {}

        for cat in category_order:
            items = MARKET_SYMBOLS[cat]
            category_sizes[cat] = len(items)
            for item in items:
                yf_tasks.append(
                    _fetch_with_timeout(item["name"], item["ticker"], yf_timeout)
                )

        # FRED task
        async def _fred_with_timeout() -> Optional[MarketItem]:
            try:
                return await asyncio.wait_for(
                    asyncio.to_thread(_fetch_fred_us10y),
                    timeout=fred_timeout,
                )
            except asyncio.TimeoutError:
                logger.warning("Timeout fetching FRED US 10Y")
                return None

        # Execute all concurrently
        all_results = await asyncio.gather(*yf_tasks, _fred_with_timeout())

        # Split yfinance results back into categories
        yf_results = list(all_results[:-1])
        fred_result = all_results[-1]

        offset = 0
        categorised: Dict[str, List[MarketItem]] = {}
        for cat in category_order:
            size = category_sizes[cat]
            items = [r for r in yf_results[offset : offset + size] if r is not None]
            categorised[cat] = items
            offset += size

        # Merge FRED bond into bonds list
        bonds = categorised["bonds"]
        if fred_result is not None:
            bonds.insert(0, fred_result)

        return MarketOverviewResponse(
            indices=categorised["indices"],
            bonds=bonds,
            fx=categorised["fx"],
            commodities=categorised["commodities"],
            generated_at=datetime.utcnow(),
        )
