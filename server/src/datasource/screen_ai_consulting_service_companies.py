from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import re
import time
from typing import Any, Optional

import diskcache
import pandas as pd
import yfinance as yf

DATASOURCE_DIR = Path(__file__).resolve().parent
SOURCE_FILE = DATASOURCE_DIR / "data_j_service_companies.xlsx"
OUTPUT_FILE_PATH = DATASOURCE_DIR / "data_j_service_ai_consulting_candidates.xlsx"
CACHE_DIR = DATASOURCE_DIR / "yfinance_cache"

# yfinance へのリクエストをバッチ処理してレート制限エラーを回避する
FETCH_MAX_WORKERS = 5  # 同時リクエスト数
FETCH_BATCH_SIZE = 50  # 1バッチあたりの銘柄数
FETCH_BATCH_SLEEP = 1.5  # バッチ間のスリープ秒数（未キャッシュ時のみ有効）
CACHE_EXPIRE_SECONDS = 86400  # キャッシュ有効期間（24時間）

TICKER_CODE_COLUMN = "コード"
COMPANY_NAME_COLUMN = "銘柄名"

AI_KEYWORDS = [
    "ai",
    "artificial intelligence",
    "machine learning",
    "deep learning",
    "generative ai",
    "natural language processing",
    "nlp",
    "computer vision",
    "neural network",
    "llm",
    "large language model",
]

STRONG_AI_KEYWORDS = [
    "artificial intelligence",
    "machine learning",
    "deep learning",
    "generative ai",
    "natural language processing",
    "nlp",
    "computer vision",
    "neural network",
    "llm",
    "large language model",
]

CONSULTING_KEYWORDS = [
    "it consulting",
    "technology consulting",
    "digital consulting",
    "business consulting",
    "strategy consulting",
    "consulting",
    "advisory",
]

CONSULTING_NAME_KEYWORDS_JA = [
    "コンサルティング",
    "コンサル",
    "アドバイザリー",
]

# より具体的なIT/デジタル関連キーワード（汎用的すぎるものを除外）
IT_DIGITAL_KEYWORDS = [
    "information technology",
    "digital transformation",
    "dx",
    "software development",
    "software engineering",
    "cloud computing",
    "cloud services",
    "saas",
    "platform",
    "cybersecurity",
    "data analytics",
    "business intelligence",
    "erp",
    "crm",
    "enterprise software",
]

# 日本企業の yfinance サマリーは短く AI 用語の出現数が少ないため
# "ai" の頭字語 1 件 + コンサル・IT シグナルそれぞれ 1 件を最低条件とする
MIN_AI_MATCH_COUNT = 1
MIN_CONSULTING_MATCH_COUNT = 1
MIN_IT_MATCH_COUNT = 1


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


def fetch_company_profile(
    ticker: str,
    cache: Optional[diskcache.Cache] = None,
) -> Optional[dict[str, Any]]:
    """yfinance から企業プロフィールを取得する。cache を渡すとディスクキャッシュを利用する。"""
    if cache is not None:
        cached = cache.get(ticker)
        if cached is not None:
            return cached  # type: ignore[return-value]

    try:
        info = yf.Ticker(ticker).info
        if not info:
            result = None
        else:
            result = {
                "sector": info.get("sector") or "",
                "industry": info.get("industry") or "",
                "summary": info.get("longBusinessSummary") or "",
                "website": info.get("website") or "",
                "short_name": info.get("shortName") or "",
                "long_name": info.get("longName") or "",
            }
    except Exception:
        result = None

    if cache is not None:
        cache.set(ticker, result, expire=CACHE_EXPIRE_SECONDS)

    return result


def _find_matched_keywords(text: str, keywords: list[str]) -> list[str]:
    lowered = text.lower()
    matched: list[str] = []
    for kw in keywords:
        kw_lower = kw.lower()
        if len(kw_lower) <= 3 and re.fullmatch(r"[a-z0-9]+", kw_lower):
            pattern = rf"\b{re.escape(kw_lower)}\b"
            if re.search(pattern, lowered):
                matched.append(kw)
        elif kw_lower in lowered:
            matched.append(kw)
    return matched


def _is_it_consulting_company(company_name: str, profile: dict[str, Any]) -> bool:
    """
    Determine if a company is an IT consulting company.

    Returns True only when:
    - consulting signal exists (in name, industry, or summary)
    - AND IT-related signal exists (in industry or summary)
    - AND AI-related signal exists (in summary)

    This triple requirement significantly narrows down to AI × IT consulting companies.
    """
    industry = profile.get("industry") or ""
    summary = profile.get("summary") or ""

    combined = f"{company_name} {industry} {summary}"

    consulting_matches = _find_matched_keywords(combined, CONSULTING_KEYWORDS)
    consulting_name_matches = _find_matched_keywords(
        company_name, CONSULTING_NAME_KEYWORDS_JA
    )
    consulting_score = len(set(consulting_matches + consulting_name_matches))
    if consulting_score < MIN_CONSULTING_MATCH_COUNT:
        return False

    it_matches = _find_matched_keywords(f"{industry} {summary}", IT_DIGITAL_KEYWORDS)
    has_it_acronym = bool(re.search(r"\bIT\b", f"{industry} {summary}"))
    it_score = len(set(it_matches)) + (1 if has_it_acronym else 0)
    if it_score < MIN_IT_MATCH_COUNT:
        return False

    ai_matches = _find_matched_keywords(summary, AI_KEYWORDS)
    if len(set(ai_matches)) < MIN_AI_MATCH_COUNT:
        return False

    return True


def _matched_ai_keywords(summary: str) -> list[str]:
    return _find_matched_keywords(summary, AI_KEYWORDS)


def extract_ai_consulting_companies(
    output_file: Path = OUTPUT_FILE_PATH,
) -> pd.DataFrame:
    source_df = load_service_companies()
    print(f"Loaded {len(source_df)} service companies from {SOURCE_FILE.name}")

    tickers = source_df["yahoo_ticker"].tolist()
    print(f"Fetching yfinance profiles for {len(tickers)} companies...")

    profiles: list[Optional[dict[str, Any]]] = []
    total_batches = (len(tickers) + FETCH_BATCH_SIZE - 1) // FETCH_BATCH_SIZE

    with diskcache.Cache(str(CACHE_DIR)) as cache:

        def _fetch(ticker: str) -> Optional[dict[str, Any]]:
            return fetch_company_profile(ticker, cache=cache)

        for batch_idx in range(total_batches):
            batch = tickers[
                batch_idx * FETCH_BATCH_SIZE : (batch_idx + 1) * FETCH_BATCH_SIZE
            ]
            uncached = [t for t in batch if cache.get(t) is None]

            with ThreadPoolExecutor(max_workers=FETCH_MAX_WORKERS) as executor:
                profiles.extend(executor.map(_fetch, batch))

            print(
                f"  batch {batch_idx + 1}/{total_batches} done "
                f"({len(profiles)}/{len(tickers)}, uncached={len(uncached)})"
            )

            # 未キャッシュの銘柄があった場合のみバッチ間でスリープしてレート制限を回避
            if uncached and batch_idx < total_batches - 1:
                time.sleep(FETCH_BATCH_SLEEP)

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
        # AI keywords are already checked in _is_it_consulting_company,
        # but we still collect them for display purposes
        if not matched:
            continue

        screened_rows.append(
            {
                "company_name": company_name,
                "yahoo_ticker": ticker,
                "website": profile.get("website", ""),
                "sector": profile.get("sector", ""),
                "industry": profile.get("industry", ""),
                "summary": summary,
                "matched_ai_keywords": ", ".join(matched),
            }
        )

    _COLUMNS = [
        "company_name",
        "yahoo_ticker",
        "website",
        "sector",
        "industry",
        "summary",
        "matched_ai_keywords",
    ]
    result_df = (
        pd.DataFrame(screened_rows, columns=_COLUMNS).reset_index(drop=True)
        if screened_rows
        else pd.DataFrame(columns=_COLUMNS)
    )

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
        {
            "name": str(row["company_name"]).strip(),
            "symbol": str(row["yahoo_ticker"]).strip(),
        }
        for row in df.to_dict("records")
        if str(row.get("company_name", "")).strip()
        and str(row.get("yahoo_ticker", "")).strip()
    ]

    if not tickers:
        raise ValueError(f"有効な銘柄データが取得できませんでした: {OUTPUT_FILE_PATH}")

    return tickers


def screen_ai_consulting_companies(
    output_file: Path = OUTPUT_FILE_PATH,
) -> pd.DataFrame:
    return extract_ai_consulting_companies(output_file=output_file)


if __name__ == "__main__":
    result = extract_ai_consulting_companies()
    print(f"screened rows: {len(result)}")
    print(f"saved to: {OUTPUT_FILE_PATH}")
