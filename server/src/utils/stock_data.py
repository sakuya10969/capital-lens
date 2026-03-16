"""
yfinance を使った銘柄財務データ取得。

services/stocks.py および services/ai_consulting.py から利用する。
"""

import logging
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Tuple

import yfinance as yf

from src.schemas.ai_consulting import EarningsItem, PerItem, StockRecord
from src.utils.yfinance import normalize_symbol, safe_float

logger = logging.getLogger(__name__)


def fetch_stock_record(code: str) -> StockRecord:
    """銘柄コードをもとに yfinance から企業情報・財務指標を取得する。欠損は None で返す。"""
    fetched_at = datetime.utcnow()
    symbol = normalize_symbol(code)
    try:
        t = yf.Ticker(symbol)
        info: Dict[str, Any] = t.info or {}
    except Exception as exc:
        logger.warning("yfinance info error %s: %s", symbol, exc)
        return StockRecord(code=code, symbol=symbol, updated_at=fetched_at, fetched_at=fetched_at)

    name: Optional[str] = info.get("longName") or info.get("shortName") or None
    enterprise_value = safe_float(info.get("enterpriseValue"))
    market_cap = safe_float(info.get("marketCap"))
    per = safe_float(info.get("trailingPE"))
    revenue = safe_float(info.get("totalRevenue"))
    net_income = safe_float(info.get("netIncomeToCommon"))
    dividend_yield = safe_float(info.get("dividendYield"))
    roe = safe_float(info.get("returnOnEquity"))

    # 株価基準日時: regularMarketTime は Unix タイムスタンプ
    price_as_of: Optional[datetime] = None
    reg_market_time = info.get("regularMarketTime")
    if reg_market_time is not None:
        try:
            price_as_of = datetime.utcfromtimestamp(int(reg_market_time))
        except Exception as exc:
            logger.debug("price_as_of parse error %s: %s", symbol, exc)

    financials_as_of: Optional[date] = None

    # 営業利益: info に無い場合は income_stmt から補完
    operating_income: Optional[float] = safe_float(info.get("operatingIncome"))
    if operating_income is None:
        try:
            fin = t.income_stmt
            if fin is not None and not fin.empty:
                for key in ("Operating Income", "Total Operating Income As Reported"):
                    if key in fin.index:
                        operating_income = safe_float(fin.loc[key].iloc[0])
                        break
        except Exception as exc:
            logger.debug("income_stmt error %s: %s", symbol, exc)

    # 自己資本比率: balance_sheet から取得
    equity_ratio: Optional[float] = None
    try:
        bs = t.balance_sheet
        if bs is not None and not bs.empty:
            total_equity: Optional[float] = None
            total_assets: Optional[float] = None
            for key in (
                "Stockholders Equity",
                "Total Stockholder Equity",
                "Total Equity Gross Minority Interest",
                "Common Stock Equity",
            ):
                if key in bs.index:
                    total_equity = safe_float(bs.loc[key].iloc[0])
                    break
            for key in ("Total Assets",):
                if key in bs.index:
                    total_assets = safe_float(bs.loc[key].iloc[0])
                    break
            if total_equity is not None and total_assets and total_assets != 0:
                equity_ratio = round(total_equity / total_assets, 4)
            # 財務基準日: balance_sheet の最新列（期末日）
            if len(bs.columns) > 0:
                col = bs.columns[0]
                try:
                    financials_as_of = col.date() if hasattr(col, "date") else date.fromisoformat(str(col)[:10])
                except Exception as exc:
                    logger.debug("financials_as_of parse error %s: %s", symbol, exc)
    except Exception as exc:
        logger.debug("balance_sheet error %s: %s", symbol, exc)

    return StockRecord(
        code=code,
        symbol=symbol,
        name=name,
        enterprise_value=enterprise_value,
        market_cap=market_cap,
        per=per,
        revenue=revenue,
        operating_income=operating_income,
        net_income=net_income,
        dividend_yield=dividend_yield,
        roe=roe,
        equity_ratio=equity_ratio,
        updated_at=fetched_at,
        fetched_at=fetched_at,
        price_as_of=price_as_of,
        financials_as_of=financials_as_of,
    )


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
    website: Optional[str] = info.get("website") or None
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
        website=website,
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
    website: Optional[str] = None

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

        # website
        website = info.get("website") or None

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
        website=website,
        note="; ".join(notes) if notes else None,
    )

    if earnings_date is None:
        return item, False

    is_upcoming = window_from <= earnings_date <= window_to
    return item, is_upcoming
