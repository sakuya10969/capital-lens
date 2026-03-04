import asyncio
import json
import logging
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yfinance as yf

from src.schemas.ai_consulting import (
    EarningsItem,
    EarningsResponse,
    EarningsWindow,
    PerItem,
    PerResponse,
    ReportResponse,
)

logger = logging.getLogger(__name__)

_TICKERS_PATH = Path(__file__).parent.parent.parent / "config" / "ai_consulting_tickers.json"
_YFINANCE_TIMEOUT = 15.0


def _load_tickers() -> List[Dict[str, str]]:
    with open(_TICKERS_PATH, encoding="utf-8") as f:
        return json.load(f)["items"]


# helpers

def _safe_float(val: Any) -> Optional[float]:
    try:
        v = float(val)
        return None if (v != v) else v  # NaN check
    except (TypeError, ValueError):
        return None


def _fetch_per_item(name: str, symbol: str) -> PerItem:
    notes: List[str] = []
    try:
        t = yf.Ticker(symbol)
        info: Dict[str, Any] = t.info or {}
    except Exception as exc:
        logger.warning("yfinance info error %s: %s", symbol, exc)
        return PerItem(name=name, symbol=symbol, note=f"yfinance取得失敗: {exc}")

    price = _safe_float(info.get("currentPrice") or info.get("regularMarketPrice"))
    currency = info.get("currency")
    trailing_pe = _safe_float(info.get("trailingPE"))
    forward_pe = _safe_float(info.get("forwardPE"))
    trailing_eps = _safe_float(info.get("trailingEps"))

    # PER決定ロジック
    computed_pe: Optional[float] = None
    if price is not None and trailing_eps and trailing_eps != 0:
        computed_pe = round(price / trailing_eps, 2)

    if trailing_pe is not None:
        pe_used = "trailing"
        pe_final = trailing_pe
    elif forward_pe is not None:
        pe_used = "forward"
        pe_final = forward_pe
    elif computed_pe is not None:
        pe_used = "computed"
        pe_final = computed_pe
    else:
        pe_used = None
        pe_final = None
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
        pe_used=pe_used,
        note="; ".join(notes) if notes else None,
    )


def _fetch_earnings_item(name: str, symbol: str, window_from: date, window_to: date) -> Tuple[EarningsItem, bool]:
    """Returns (item, is_upcoming). is_upcoming=False means unknown."""
    notes: List[str] = []
    earnings_date: Optional[date] = None
    price_change_5d: Optional[float] = None
    price_change_1m: Optional[float] = None
    trailing_pe: Optional[float] = None
    summary: Optional[str] = None

    try:
        t = yf.Ticker(symbol)
        info: Dict[str, Any] = t.info or {}

        # ---- earnings date ---- #
        cal = t.calendar
        if cal is not None:
            ed_val = None
            if isinstance(cal, dict):
                ed_val = cal.get("Earnings Date")
            else:
                # pandas DataFrame / Series
                try:
                    ed_val = cal.loc["Earnings Date"].iloc[0] if hasattr(cal, "loc") else None
                except Exception:
                    pass
            if ed_val is not None:
                # may be list
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
                        price_change_5d = round((latest - oldest_5d) / oldest_5d * 100, 2)
                else:
                    notes.append("5日分履歴不足")
            else:
                notes.append("株価履歴取得失敗")
        except Exception as exc:
            notes.append(f"株価変化算出失敗: {exc}")

        # trailing PE
        trailing_pe = _safe_float(info.get("trailingPE"))

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
    # unknown = not in window (treat out-of-window as unknown for this PoC)
    return item, is_upcoming


# Service

class AiConsultingService:

    def _tickers(self) -> List[Dict[str, str]]:
        return _load_tickers()

    async def get_per(self) -> PerResponse:
        tickers = self._tickers()

        async def _fetch(name: str, symbol: str) -> PerItem:
            try:
                return await asyncio.wait_for(
                    asyncio.to_thread(_fetch_per_item, name, symbol),
                    timeout=_YFINANCE_TIMEOUT,
                )
            except asyncio.TimeoutError:
                logger.warning("Timeout fetching PER for %s", symbol)
                return PerItem(name=name, symbol=symbol, note="タイムアウト")

        items = await asyncio.gather(*[_fetch(t["name"], t["symbol"]) for t in tickers])
        return PerResponse(as_of=datetime.utcnow(), items=list(items))

    async def get_earnings(self, window_days: int = 7) -> EarningsResponse:
        tickers = self._tickers()
        today = date.today()
        window_from = today - timedelta(days=window_days)
        window_to = today + timedelta(days=window_days)

        async def _fetch(name: str, symbol: str) -> Tuple[EarningsItem, bool]:
            try:
                return await asyncio.wait_for(
                    asyncio.to_thread(_fetch_earnings_item, name, symbol, window_from, window_to),
                    timeout=_YFINANCE_TIMEOUT,
                )
            except asyncio.TimeoutError:
                logger.warning("Timeout fetching earnings for %s", symbol)
                item = EarningsItem(name=name, symbol=symbol, note="タイムアウト")
                return item, False

        results = await asyncio.gather(*[_fetch(t["name"], t["symbol"]) for t in tickers])

        upcoming: List[EarningsItem] = []
        unknown: List[EarningsItem] = []
        for item, is_upcoming in results:
            if is_upcoming:
                upcoming.append(item)
            else:
                unknown.append(item)

        return EarningsResponse(
            as_of=datetime.utcnow(),
            window=EarningsWindow(from_date=window_from, to_date=window_to, days=window_days),
            upcoming=upcoming,
            unknown=unknown,
        )

    async def get_report(self, window_days: int = 7) -> ReportResponse:
        per_result, earnings_result = await asyncio.gather(
            self.get_per(),
            self.get_earnings(window_days),
        )

        # ---- text report ---- #
        lines: List[str] = ["【AI×コンサル銘柄分析レポート】\n"]

        # PER
        pe_items = [i for i in per_result.items if i.pe_used is not None]
        if pe_items:
            sorted_pe = sorted(pe_items, key=lambda x: (
                x.trailing_pe if x.pe_used == "trailing" else
                x.forward_pe if x.pe_used == "forward" else
                x.computed_pe or 0
            ))
            def _pe_val(item: PerItem) -> float:
                return (
                    item.trailing_pe if item.pe_used == "trailing" else
                    item.forward_pe if item.pe_used == "forward" else
                    item.computed_pe or 0
                )
            lowest = sorted_pe[0]
            highest = sorted_pe[-1]
            lines.append(f"■ PER（取得できた {len(pe_items)}/{len(per_result.items)} 銘柄）")
            lines.append(f"  最低PER: {lowest.name}（{lowest.symbol}）= {_pe_val(lowest):.1f}x [{lowest.pe_used}]")
            lines.append(f"  最高PER: {highest.name}（{highest.symbol}）= {_pe_val(highest):.1f}x [{highest.pe_used}]")
        else:
            lines.append("■ PER: 取得できた銘柄なし")

        lines.append("")

        # Earnings upcoming
        lines.append(f"■ 決算期（今日±{window_days}日: {earnings_result.window.from_date} 〜 {earnings_result.window.to_date}）")
        if earnings_result.upcoming:
            lines.append(f"  決算予定銘柄 ({len(earnings_result.upcoming)}件):")
            for item in earnings_result.upcoming:
                ed = item.earnings_date.isoformat() if item.earnings_date else "不明"
                lines.append(f"    - {item.name}（{item.symbol}）: {ed}")
        else:
            lines.append("  決算予定銘柄: なし")

        lines.append("")
        unknown_names = ", ".join(f"{i.name}（{i.symbol}）" for i in earnings_result.unknown)
        lines.append(f"■ 決算日未取得/範囲外: {len(earnings_result.unknown)}件")
        if earnings_result.unknown:
            lines.append(f"  対象: {unknown_names}")

        return ReportResponse(
            as_of=datetime.utcnow(),
            per=per_result,
            earnings=earnings_result,
            text_report="\n".join(lines),
        )
