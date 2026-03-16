import asyncio
import json
import logging
from pathlib import Path
from typing import List

from src.schemas.ai_consulting import StockRecord, StocksResponse
from src.utils.stock_data import fetch_stock_record
from src.utils.yfinance import codes_match

logger = logging.getLogger(__name__)

_YFINANCE_TIMEOUT = 15.0

_STOCKS_JSON = Path(__file__).parent.parent / "datasource" / "stocks.json"


class StocksService:
    """GUI管理銘柄の CRUD + yfinance リフレッシュ"""

    def _load(self) -> List[StockRecord]:
        if not _STOCKS_JSON.exists():
            return []
        try:
            data = json.loads(_STOCKS_JSON.read_text(encoding="utf-8"))
            return [StockRecord(**item) for item in data.get("stocks", [])]
        except Exception as exc:
            logger.warning("stocks.json 読込失敗: %s", exc)
            return []

    def _save(self, stocks: List[StockRecord]) -> None:
        _STOCKS_JSON.parent.mkdir(parents=True, exist_ok=True)
        payload = {"stocks": [s.model_dump(mode="json") for s in stocks]}
        _STOCKS_JSON.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def list_stocks(self) -> StocksResponse:
        return StocksResponse(stocks=self._load())

    async def add_stock(self, code: str) -> StocksResponse:
        stocks = self._load()
        if any(
            codes_match(s.code, code) or codes_match(s.symbol, code) for s in stocks
        ):
            return StocksResponse(stocks=stocks)

        record = await asyncio.wait_for(
            asyncio.to_thread(fetch_stock_record, code),
            timeout=_YFINANCE_TIMEOUT,
        )
        stocks.append(record)
        self._save(stocks)
        return StocksResponse(stocks=stocks)

    async def delete_stock(self, code: str) -> StocksResponse:
        stocks = [
            s
            for s in self._load()
            if not codes_match(s.code, code) and not codes_match(s.symbol, code)
        ]
        self._save(stocks)
        return StocksResponse(stocks=stocks)

    async def refresh_stock(self, code: str) -> StocksResponse:
        stocks = self._load()
        record = await asyncio.wait_for(
            asyncio.to_thread(fetch_stock_record, code),
            timeout=_YFINANCE_TIMEOUT,
        )
        stocks = [
            record if (codes_match(s.code, code) or codes_match(s.symbol, code)) else s
            for s in stocks
        ]
        self._save(stocks)
        return StocksResponse(stocks=stocks)

    async def refresh_all(self) -> StocksResponse:
        stocks = self._load()
        if not stocks:
            return StocksResponse(stocks=[])

        updated: List[StockRecord] = await asyncio.gather(
            *[
                asyncio.wait_for(
                    asyncio.to_thread(fetch_stock_record, s.code),
                    timeout=_YFINANCE_TIMEOUT,
                )
                for s in stocks
            ],
            return_exceptions=True,
        )

        result: List[StockRecord] = []
        for original, record in zip(stocks, updated):
            if isinstance(record, StockRecord):
                result.append(record)
            else:
                logger.warning("refresh_all 失敗 %s: %s", original.code, record)
                result.append(original)

        self._save(result)
        return StocksResponse(stocks=result)
