import logging
from datetime import date
from typing import Any, Dict, List, Optional, Tuple

import yfinance as yf

from src.schemas.ai_consulting import EarningsItem, PerItem
from src.schemas.market import MarketItem

logger = logging.getLogger(__name__)


def safe_float(val: Any) -> Optional[float]:
    """NaN を None に変換しつつ float 化する"""
    try:
        v = float(val)
        return None if (v != v) else v  # NaN check
    except (TypeError, ValueError):
        return None


def fetch_per_item(name: str, symbol: str) -> PerItem:
    notes: List[str] = []
    try:
        t = yf.Ticker(symbol)
        info: Dict[str, Any] = t.info or {}
    except Exception as exc:
        logger.warning("yfinance info error %s: %s", symbol, exc)
        return PerItem(name=name, symbol=symbol, note=f"yfinance取得失敗: {exc}")

    price = safe_float(info.get("currentPrice") or info.get("regularMarketPrice"))
    currency = info.get("currency")
    trailing_pe = safe_float(info.get("trailingPE"))
    forward_pe = safe_float(info.get("forwardPE"))
    trailing_eps = safe_float(info.get("trailingEps"))

    # PER決定ロジック
    computed_pe: Optional[float] = None
    if price is not None and trailing_eps and trailing_eps != 0:
        computed_pe = round(price / trailing_eps, 2)

    pe_used: Optional[str] = None
    if trailing_pe is not None:
        pe_used = "trailing"
    elif forward_pe is not None:
        pe_used = "forward"
    elif computed_pe is not None:
        pe_used = "computed"
    else:
        notes.append("PER算出不可")

    if trailing_pe is None and forward_pe is None:
        notes.append("trailingPE/forwardPE欠損")

    return PerItem(
        name=name,
        symbol=symbol,
        price=price,
        currency=str(currency) if currency else None,
        trailing_pe=trailing_pe,
        forward_pe=forward_pe,
        trailing_eps=trailing_eps,
        computed_pe=computed_pe,
        pe_used=pe_used if pe_used else None,
        note="; ".join(notes) if notes else None,
    )


def fetch_earnings_item(
    name: str, symbol: str, window_from: date, window_to: date
) -> Tuple[EarningsItem, bool]:
    notes: List[str] = []
    earnings_date: Optional[date] = None
    price_change_5d: Optional[float] = None
    price_change_1m: Optional[float] = None
    trailing_pe: Optional[float] = None
    summary: Optional[str] = None

    try:
        t = yf.Ticker(symbol)
        info: Dict[str, Any] = t.info or {}

        # earnings date
        cal = t.calendar
        if cal is not None:
            ed_val = None
            if isinstance(cal, dict):
                ed_val = cal.get("Earnings Date")
            else:
                try:
                    ed_val = (
                        cal.loc["Earnings Date"].iloc[0]
                        if hasattr(cal, "loc")
                        else None
                    )
                except Exception:
                    pass
            if ed_val is not None:
                if isinstance(ed_val, list):
                    ed_val = ed_val[0] if ed_val else None
                if ed_val is not None:
                    try:
                        if hasattr(ed_val, "date"):
                            earnings_date = ed_val.date()
                        else:
                            earnings_date = date.fromisoformat(str(ed_val)[:10])
                    except Exception as exc:
                        notes.append(f"決算日パース失敗: {exc}")

        # price changes
        try:
            hist_1m = t.history(period="1mo")
            if not hist_1m.empty:
                latest = float(hist_1m["Close"].iloc[-1])
                oldest_1m = float(hist_1m["Close"].iloc[0])
                if oldest_1m != 0:
                    price_change_1m = round((latest - oldest_1m) / oldest_1m * 100, 2)
                if len(hist_1m) >= 5:
                    oldest_5d = float(hist_1m["Close"].iloc[-5])
                    if oldest_5d != 0:
                        price_change_5d = round(
                            (latest - oldest_5d) / oldest_5d * 100, 2
                        )
                else:
                    notes.append("5日分履歴不足")
            else:
                notes.append("株価履歴取得失敗")
        except Exception as exc:
            notes.append(f"株価変化算出失敗: {exc}")

        # trailing PE
        trailing_pe = safe_float(info.get("trailingPE"))

        # summary
        raw_summary: Optional[str] = info.get("longBusinessSummary")
        if raw_summary:
            summary = raw_summary[:300]

    except Exception as exc:
        logger.warning("yfinance error %s: %s", symbol, exc)
        notes.append(f"yfinance取得失敗: {exc}")

    item = EarningsItem(
        name=name,
        symbol=symbol,
        earnings_date=earnings_date,
        price_change_5d=price_change_5d,
        price_change_1m=price_change_1m,
        trailing_pe=trailing_pe,
        summary=summary,
        note="; ".join(notes) if notes else None,
    )

    if earnings_date is None:
        return item, False

    is_upcoming = window_from <= earnings_date <= window_to
    return item, is_upcoming


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
