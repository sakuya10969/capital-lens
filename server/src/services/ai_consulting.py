import asyncio
import json
import logging
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from src.utils.yfinance import fetch_earnings_item, fetch_per_item

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





# Service
class AiConsultingService:

    def _tickers(self) -> List[Dict[str, str]]:
        return _load_tickers()

    async def get_per(self) -> PerResponse:
        tickers = self._tickers()

        async def _fetch(name: str, symbol: str) -> PerItem:
            try:
                return await asyncio.wait_for(
                    asyncio.to_thread(fetch_per_item, name, symbol),
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
                    asyncio.to_thread(fetch_earnings_item, name, symbol, window_from, window_to),
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

        # text report
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
