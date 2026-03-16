"""
yfinance 共通ヘルパー。

外部 API 呼び出しは含まない。
市場データ取得 → utils/market_data.py
銘柄財務データ取得 → utils/stock_data.py
"""

import re
from typing import Any, Optional


def safe_float(val: Any) -> Optional[float]:
    """NaN を None に変換しつつ float 化する"""
    try:
        v = float(val)
        return None if (v != v) else v  # NaN check
    except (TypeError, ValueError):
        return None


def normalize_symbol(code: str) -> str:
    """日本株コードを yfinance 形式に正規化する。

    - "7203"   → "7203.T"   (4桁数字)
    - "277A"   → "277A.T"   (英字付き日本株コード、グロース市場等)
    - "7203.T" → "7203.T"   (既に取引所サフィックスあり)
    - "AAPL"   → "AAPL"     (上記以外はそのまま大文字化)
    """
    code = code.strip().upper()
    if "." in code:
        return code
    # 4桁数字 または 3桁数字+英字1文字（例: 277A, 143A）
    if re.fullmatch(r"\d{4}|\d{3}[A-Z]", code):
        return f"{code}.T"
    return code


def codes_match(a: str, b: str) -> bool:
    """銘柄コードの同一性判定（.T サフィックスありなしを吸収する）。

    例: "7203" と "7203.T"、"277A" と "277A.T" を同一と判定する。
    """
    def _base(c: str) -> str:
        c = c.strip().upper()
        return c[:-2] if c.endswith(".T") else c

    return _base(a) == _base(b)


# ==============================================================================
# J-Quants API ベースの実装への移行は一時中断（2026-03）。
# J-Quants 実装は infrastructure/jquants/ に退避済み。
# J-Quants に再移行する場合は services/stocks.py のインポートを以下に変更:
#   from src.infrastructure.jquants.fetcher import (
#       codes_match,
#       fetch_stock_record_jquants as fetch_stock_record,
#       normalize_code_jquants as normalize_symbol,
#   )
# ==============================================================================
