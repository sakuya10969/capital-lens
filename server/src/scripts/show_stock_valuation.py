import argparse
import sys
from pathlib import Path
from typing import Iterable


SERVER_ROOT = Path(__file__).resolve().parents[2]
if str(SERVER_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVER_ROOT))

from src.schemas.ai_consulting import StockRecord
from src.utils.yfinance import fetch_stock_record


def _format_amount(value: float | None) -> str:
    if value is None:
        return "N/A"

    abs_value = abs(value)
    if abs_value >= 1_0000_0000_0000:
        return f"{value / 1_0000_0000_0000:.2f}兆"
    if abs_value >= 1_0000_0000:
        return f"{value / 1_0000_0000:.2f}億"
    if abs_value >= 1_0000:
        return f"{value / 1_0000:.2f}万"
    return f"{value:,.0f}"


def _print_record(record: StockRecord) -> None:
    print(f"銘柄コード: {record.code}")
    print(f"シンボル: {record.symbol}")
    print(f"企業名: {record.name or 'N/A'}")
    print(f"企業価値 (EV): {record.enterprise_value:,.0f}" if record.enterprise_value is not None else "企業価値 (EV): N/A")
    print(f"企業価値 (概算): {_format_amount(record.enterprise_value)}")
    print(f"時価総額: {record.market_cap:,.0f}" if record.market_cap is not None else "時価総額: N/A")
    print(f"時価総額 (概算): {_format_amount(record.market_cap)}")
    if record.updated_at is not None:
        print(f"取得時刻: {record.updated_at.isoformat()}")


def _iter_codes(values: Iterable[str]) -> Iterable[str]:
    for value in values:
        code = value.strip()
        if code:
            yield code


def main() -> int:
    parser = argparse.ArgumentParser(
        description="銘柄コードから企業価値と時価総額を取得して表示します。"
    )
    parser.add_argument(
        "codes",
        nargs="+",
        help="銘柄コードまたはシンボル。4桁コードには自動で .T を付与します。",
    )
    args = parser.parse_args()

    codes = list(_iter_codes(args.codes))
    if not codes:
        parser.error("少なくとも1つの銘柄コードを指定してください。")

    for index, code in enumerate(codes):
        if index > 0:
            print()
            print("-" * 40)
        _print_record(fetch_stock_record(code))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
