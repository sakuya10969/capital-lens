from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import re
from typing import Any, Optional

import pandas as pd
import yfinance as yf


DATASOURCE_DIR = Path(__file__).resolve().parent
SOURCE_FILE = DATASOURCE_DIR / "data_j_service_companies.xlsx"
OUTPUT_FILE_PATH = DATASOURCE_DIR / "data_j_service_ai_consulting_candidates.xlsx"

TICKER_CODE_COLUMN = "コード"
COMPANY_NAME_COLUMN = "銘柄名"

AI_KEYWORDS = [
    "ai",
    "artificial intelligence",
    "machine learning",
    "deep learning",
    "generative ai",
    "analytics",
    "data analysis",
    "data analytics",
    "natural language",
    "computer vision",
]

CONSULTING_KEYWORDS = [
    "it consulting",
    "technology consulting",
    "digital consulting",
    "business consulting",
    "management consulting",
    "strategy consulting",
    "advisory",
    "consulting",
]

CONSULTING_NAME_KEYWORDS_JA = [
    "コンサルティング",
    "コンサル",
    "アドバイザリー",
    "総研",
]

IT_KEYWORDS = [
    "information technology",
    "digital",
    "dx",
    "transformation",
    "system",
    "systems",
    "software",
    "cloud",
    "data",
    "analytics",
    "platform",
    "cybersecurity",
    "security",
    "erp",
    "sap",
    "crm",
    "ai",
    "artificial intelligence",
    "machine learning",
]


def _to_yahoo_ticker(code: Any) -> str:
    """JPX銘柄コードをYahoo Finance形式（例: 1234.T）に変換する。"""
    code_str = str(code).strip()
    if not code_str or code_str.lower() in {"nan", "none"}:
        return ""
    # Excelで数値として読み込まれた場合 (例: 1234.0 → 1234)
    if re.match(r"^\d+\.0$", code_str):
        code_str = code_str[:-2]
    if code_str.upper().endswith(".T"):
        return code_str.upper()
    return f"{code_str}.T"


def load_service_companies() -> pd.DataFrame:
    if not SOURCE_FILE.exists():
        raise FileNotFoundError(f"Source file not found: {SOURCE_FILE}")
    df = pd.read_excel(SOURCE_FILE, engine="openpyxl")
    if TICKER_CODE_COLUMN not in df.columns:
        raise ValueError(
            f"Column '{TICKER_CODE_COLUMN}' not found. Available: {df.columns.tolist()}"
        )
    df = df.copy()
    df["yahoo_ticker"] = df[TICKER_CODE_COLUMN].map(_to_yahoo_ticker)
    df = df[df["yahoo_ticker"] != ""].copy()
    return df.reset_index(drop=True)


def fetch_company_profile(ticker: str) -> Optional[dict[str, Any]]:
    try:
        info = yf.Ticker(ticker).info
        if not info:
            return None
        return {
            "sector": info.get("sector") or "",
            "industry": info.get("industry") or "",
            "summary": info.get("longBusinessSummary") or "",
            "website": info.get("website") or "",
            "short_name": info.get("shortName") or "",
            "long_name": info.get("longName") or "",
        }
    except Exception:
        return None


def _contains_any(text: str, keywords: list[str]) -> bool:
    """Check if text contains any of the keywords (case-insensitive)."""
    lowered = text.lower()
    return any(kw in lowered for kw in keywords)


def _is_it_consulting_company(company_name: str, profile: dict[str, Any]) -> bool:
    """
    Determine if a company is an IT consulting company.
    
    Returns True only when:
    - consulting signal exists (in name, industry, or summary)
    - AND IT-related signal exists (in industry or summary)
    """
    industry = (profile.get("industry") or "")
    summary = (profile.get("summary") or "")

    # Check for consulting signal (case-insensitive)
    has_consulting_signal = (
        _contains_any(company_name, CONSULTING_NAME_KEYWORDS_JA) or
        _contains_any(industry.lower(), CONSULTING_KEYWORDS) or
        _contains_any(summary.lower(), CONSULTING_KEYWORDS)
    )

    if not has_consulting_signal:
        return False

    # Check for IT-related signal.
    # "IT" (acronym) is matched case-sensitively as a whole word to avoid
    # false positives from the English pronoun "it" / possessive "its".
    combined_original = f"{industry} {summary}"
    has_it_acronym = bool(re.search(r"\bIT\b", combined_original))
    has_it_signal = has_it_acronym or _contains_any(combined_original.lower(), IT_KEYWORDS)

    return has_it_signal


def _matched_ai_keywords(summary: str) -> list[str]:
    lowered = summary.lower()
    return [kw for kw in AI_KEYWORDS if kw in lowered]


def extract_ai_consulting_companies(output_file: Path = OUTPUT_FILE_PATH) -> pd.DataFrame:
    source_df = load_service_companies()
    print(f"Loaded {len(source_df)} service companies from {SOURCE_FILE.name}")

    tickers = source_df["yahoo_ticker"].tolist()
    print(f"Fetching yfinance profiles for {len(tickers)} companies...")

    with ThreadPoolExecutor(max_workers=20) as executor:
        profiles = list(executor.map(fetch_company_profile, tickers))

    profile_cache: dict[str, Optional[dict[str, Any]]] = dict(zip(tickers, profiles))
    fetched = sum(1 for p in profiles if p is not None)
    print(f"  Fetched: {fetched}/{len(tickers)}")

    screened_rows: list[dict[str, Any]] = []

    for record in source_df.to_dict("records"):
        ticker = str(record.get("yahoo_ticker", ""))
        company_name = str(record.get(COMPANY_NAME_COLUMN, "") or "")

        profile = profile_cache.get(ticker)
        if not profile:
            continue

        if not _is_it_consulting_company(company_name, profile):
            continue

        summary = profile.get("summary") or ""
        matched = _matched_ai_keywords(summary)
        if not matched:
            continue

        screened_rows.append({
            "company_name": company_name,
            "yahoo_ticker": ticker,
            "website": profile.get("website", ""),
            "sector": profile.get("sector", ""),
            "industry": profile.get("industry", ""),
            "summary": summary,
            "matched_ai_keywords": ", ".join(matched),
        })

    result_df = pd.DataFrame(screened_rows)
    if not result_df.empty:
        result_df = result_df.reset_index(drop=True)

    output_file.parent.mkdir(parents=True, exist_ok=True)
    result_df.to_excel(output_file, index=False)

    return result_df


def load_ai_consulting_tickers() -> list[dict[str, str]]:
    """AIコンサル候補銘柄一覧をExcelから読み込み {"name": ..., "symbol": ...} のリストで返す。

    Raises:
        FileNotFoundError: Excelファイルが存在しない場合
        ValueError: 必要カラムがない・データが空の場合
    """
    if not OUTPUT_FILE_PATH.exists():
        raise FileNotFoundError(
            f"AIコンサル候補銘柄ファイルが見つかりません: {OUTPUT_FILE_PATH}\n"
            "screen_ai_consulting_service_companies.py を先に実行してください。"
        )

    try:
        df = pd.read_excel(OUTPUT_FILE_PATH, engine="openpyxl")
    except Exception as exc:
        raise RuntimeError(
            f"Excelファイルの読み込みに失敗しました: {OUTPUT_FILE_PATH}\n原因: {exc}"
        ) from exc

    required_cols = {"company_name", "yahoo_ticker"}
    missing = required_cols - set(df.columns)
    if missing:
        raise ValueError(
            f"必要なカラムがありません: {missing}. 実際のカラム: {df.columns.tolist()}"
        )

    if df.empty:
        raise ValueError(f"AIコンサル候補銘柄ファイルが空です: {OUTPUT_FILE_PATH}")

    tickers = [
        {"name": str(row["company_name"]).strip(), "symbol": str(row["yahoo_ticker"]).strip()}
        for row in df.to_dict("records")
        if str(row.get("company_name", "")).strip() and str(row.get("yahoo_ticker", "")).strip()
    ]

    if not tickers:
        raise ValueError(
            f"有効な銘柄データが取得できませんでした: {OUTPUT_FILE_PATH}"
        )

    return tickers


def screen_ai_consulting_companies(output_file: Path = OUTPUT_FILE_PATH) -> pd.DataFrame:
    return extract_ai_consulting_companies(output_file=output_file)


if __name__ == "__main__":
    result = extract_ai_consulting_companies()
    print(f"screened rows: {len(result)}")
    print(f"saved to: {OUTPUT_FILE_PATH}")
