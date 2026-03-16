"""
J-Quants API V2 を使った銘柄情報取得ユーティリティ（ドメイン変換層）。

責務:
- 銘柄コードの正規化（J-Quants形式）
- J-Quants V2 レスポンスを StockRecord へ変換
- 取得できない項目は None で返す（API接続エラーは上位に伝播）

HTTPクライアントの実体は infrastructure/jquants_client.py に閉じ込める。

使用エンドポイント (V2):
- GET /v2/equities/master      → 企業基本情報（CoName）
- GET /v2/equities/bars/daily  → 株価四本値（AdjC）
- GET /v2/fins/summary         → 財務情報サマリ（Sales/OP/NP/EPS/EqAR/ShOutFY…）
- GET /v2/fins/details         → 財務諸表明細（BS の現金・有利子負債 → EV 計算用）

EV 計算式:
  EV = 時価総額 + 有利子負債合計 - 現金及び現金等価物
  会計基準（IFRS / J-GAAP / US GAAP）ごとに使用するフィールド名が異なる。

データマッピング (/fins/summary V2 フィールド名):
  CoName   → 企業名
  AdjC     → 株価（調整済み終値）
  AdjC × (ShOutFY - TrShFY) → 時価総額
  AdjC ÷ EPS  → PER
  Sales    → 売上高
  OP       → 営業利益
  NP       → 当期純利益
  DivAnn   → 配当利回り計算用（年間配当実績）
  NP ÷ Eq  → ROE
  EqAR     → 自己資本比率
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from src.core.exceptions import ExternalAPIError
from src.infrastructure.jquants_client import jquants_client
from src.schemas.ai_consulting import StockRecord

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------
# コード正規化
# ------------------------------------------------------------------


def normalize_code_jquants(code: str) -> str:
    """J-Quants API 用に銘柄コードを正規化する。

    - "7203"   → "7203"   (4桁数字: そのまま)
    - "7203.T" → "7203"   (yfinance形式: .T を除去)
    - "72030"  → "72030"  (5桁コード: そのまま)
    - "277A"   → "277A"   (英字入りコード: そのまま)
    """
    code = code.strip()
    if code.upper().endswith(".T"):
        code = code[:-2]
    return code


def codes_match(a: str, b: str) -> bool:
    """銘柄コードの同一性判定（yfinance形式と J-Quants形式の両方に対応）。

    既存データに "7203.T" 形式が残っていても "7203" と同一と判定する。
    """
    return normalize_code_jquants(a).upper() == normalize_code_jquants(b).upper()


# ------------------------------------------------------------------
# 内部ヘルパー
# ------------------------------------------------------------------


def _safe_num(val: Any) -> Optional[float]:
    """None・空文字・NaN を None に変換して float を返す。"""
    if val is None or val == "":
        return None
    try:
        v = float(val)
        return None if (v != v) else v  # NaN check
    except (TypeError, ValueError):
        return None


def extract_data(payload: Dict[str, Any]) -> Any:
    """J-Quants v2 レスポンスからトップレベルの data を返す。"""
    if not isinstance(payload, dict):
        return None
    return payload.get("data")


def _extract_data_records(payload: Dict[str, Any], endpoint: str, code: str) -> List[Dict[str, Any]]:
    """J-Quants v2 の payload['data'] をレコード配列へ正規化する。"""
    data = extract_data(payload)

    if data is None:
        if not isinstance(payload, dict):
            logger.warning(
                "J-Quants %s: payload が dict ではありません code=%s type=%s",
                endpoint, code, type(payload).__name__,
            )
        else:
            logger.warning(
                "J-Quants %s: data キーがありません code=%s keys=%s",
                endpoint, code, list(payload.keys()),
            )
        return []

    if isinstance(data, list):
        if not data:
            logger.info("J-Quants %s: data は空リストです code=%s", endpoint, code)
            return []
        records = [item for item in data if isinstance(item, dict)]
        if not records:
            logger.warning(
                "J-Quants %s: data は list ですが dict 要素がありません code=%s",
                endpoint, code,
            )
        return records

    if isinstance(data, dict):
        if not data:
            logger.info("J-Quants %s: data は空オブジェクトです code=%s", endpoint, code)
            return []
        return [data]

    logger.warning(
        "J-Quants %s: data の型が想定外です code=%s type=%s",
        endpoint, code, type(data).__name__,
    )
    return []


def _select_fy_statement(statements: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """最新の通期（FY）決算レコードを返す。

    V2 フィールド: CurPerType（値: FY/1Q/2Q/3Q/4Q/5Q）, DiscDate
    """
    fy_records = [s for s in statements if s.get("CurPerType") == "FY"]
    target = fy_records if fy_records else statements
    if not target:
        return None
    target.sort(key=lambda s: s.get("DiscDate", ""), reverse=True)
    return target[0]


# ------------------------------------------------------------------
# EV 計算用フィールドマッピング（会計基準別）
# ------------------------------------------------------------------

# 現金及び現金等価物フィールド（各基準で試す候補）
_CASH_KEYS: Dict[str, List[str]] = {
    "IFRS": [
        "Cash and cash equivalents (IFRS)",
    ],
    "JP": [
        # 連結J-GAAP: 実際のAPIレスポンスで確認すること
        "Cash and deposits (Japan GAAP)",
        "Cash and cash equivalents (Japan GAAP)",
        "Cash and cash equivalents, at carrying value (Japan GAAP)",
    ],
    "US": [
        "Cash and cash equivalents (US GAAP)",
    ],
}

# 有利子負債フィールド（各基準で合算する候補。存在するものだけ加算）
_DEBT_KEYS: Dict[str, List[str]] = {
    "IFRS": [
        "Bonds and borrowings - CL (IFRS)",   # 流動: 社債・借入金
        "Bonds and borrowings - NCL (IFRS)",  # 非流動: 社債・借入金
    ],
    "JP": [
        # 連結J-GAAP: 実際のAPIレスポンスで確認すること
        "Short-term borrowings (Japan GAAP)",
        "Short-term loans payable (Japan GAAP)",
        "Current portion of bonds payable (Japan GAAP)",
        "Current portion of long-term loans payable (Japan GAAP)",
        "Current portion of long-term borrowings (Japan GAAP)",
        "Bonds payable (Japan GAAP)",
        "Long-term borrowings (Japan GAAP)",
        "Long-term loans payable (Japan GAAP)",
    ],
    "US": [
        "Short-term debt (US GAAP)",
        "Current maturities of long-term debt (US GAAP)",
        "Long-term debt (US GAAP)",
    ],
}


def _detect_accounting_standard(doc_type: str) -> str:
    """DocType から会計基準を判定する。"""
    if "IFRS" in doc_type:
        return "IFRS"
    if doc_type.endswith("_JP") or "_JP_" in doc_type:
        return "JP"
    if "_US" in doc_type:
        return "US"
    return "UNKNOWN"


def _extract_cash_and_debt(
    fs: Dict[str, Any], standard: str
) -> Tuple[Optional[float], Optional[float]]:
    """FS辞書から現金・有利子負債合計を抽出する。

    Args:
        fs: fins/details の FS フィールド（会計帳票の生データ）
        standard: 会計基準 ("IFRS" / "JP" / "US")

    Returns:
        (cash, total_interest_bearing_debt) - 取得不能な場合は None
    """
    if standard not in _CASH_KEYS:
        logger.warning("EV計算: 未対応の会計基準 '%s'", standard)
        return None, None

    # 現金取得: 候補キーを順番に試す
    cash: Optional[float] = None
    for key in _CASH_KEYS[standard]:
        cash = _safe_num(fs.get(key))
        if cash is not None:
            logger.debug("EV: 現金フィールド '%s' = %s", key, cash)
            break

    # 有利子負債: 存在するフィールドを全て合算
    total_debt: float = 0.0
    debt_found = False
    for key in _DEBT_KEYS[standard]:
        val = _safe_num(fs.get(key))
        if val is not None and val > 0:
            logger.debug("EV: 負債フィールド '%s' = %s", key, val)
            total_debt += val
            debt_found = True

    return cash, (total_debt if debt_found else None)


# ------------------------------------------------------------------
# fins/details 取得
# ------------------------------------------------------------------


def _fetch_ev_from_details(
    jq_code: str, disc_date: str, market_cap: float
) -> Optional[float]:
    """fins/details から EV を計算する。

    fins/summary で選択した FY レコードの DiscDate を使い、
    同日の fins/details を取得して BS 情報から EV を算出する。

    EV = 時価総額 + 有利子負債合計 - 現金及び現金等価物

    Args:
        jq_code:    J-Quants 銘柄コード
        disc_date:  fins/summary で選んだ FY レコードの開示日（YYYY-MM-DD）
        market_cap: 算出済み時価総額

    Returns:
        EV (float) または None（取得不能・計算不能の場合）
    """
    try:
        # DiscDate を指定して対象日の開示のみ取得（データ量を絞る）
        resp = jquants_client.get("/fins/details", code=jq_code, date=disc_date)
        data_list = _extract_data_records(resp, "/fins/details", jq_code)
        if not data_list:
            logger.warning("J-Quants /fins/details: %s (%s) にデータなし", jq_code, disc_date)
            return None
    except ExternalAPIError:
        raise
    except Exception as exc:
        logger.warning("fins/details 取得エラー %s: %s", jq_code, exc)
        return None

    # 通期（DocType に "FY" 含む）+ 連結（"Consolidated" 含む）を優先
    def _priority(doc_type: str) -> int:
        fy = "FY" in doc_type
        cons = "Consolidated" in doc_type
        if fy and cons:
            return 0
        if fy:
            return 1
        return 2

    sorted_records = sorted(
        data_list,
        key=lambda r: (_priority(r.get("DocType", "")), r.get("DiscDate", "")),
    )
    record = sorted_records[0] if sorted_records else None
    if record is None:
        return None

    doc_type = record.get("DocType", "")
    fs: Dict[str, Any] = record.get("FS", {})
    standard = _detect_accounting_standard(doc_type)

    logger.debug(
        "fins/details %s: DocType=%s, standard=%s", jq_code, doc_type, standard
    )

    cash, total_debt = _extract_cash_and_debt(fs, standard)

    if cash is None or total_debt is None:
        logger.info(
            "EV計算不能 %s: cash=%s, debt=%s (標準=%s, DocType=%s)",
            jq_code, cash, total_debt, standard, doc_type,
        )
        return None

    ev = market_cap + total_debt - cash
    logger.debug(
        "EV %s: %s + %s - %s = %s", jq_code, market_cap, total_debt, cash, ev
    )
    return ev


# ------------------------------------------------------------------
# メイン取得関数
# ------------------------------------------------------------------


def fetch_stock_record_jquants(code: str) -> StockRecord:
    """J-Quants V2 API から銘柄情報・株価・財務指標を取得して StockRecord を返す。

    取得できない項目は None を返す。
    API接続・認証エラーは ExternalAPIError として上位に伝播させる。

    Args:
        code: 銘柄コード（例: "7203", "7203.T", "72030"）

    Returns:
        StockRecord（取得できないフィールドは None）

    Raises:
        ExternalAPIError: API接続・認証失敗時
    """
    jq_code = normalize_code_jquants(code)
    now = datetime.utcnow()

    # ---- 1. 企業基本情報 (/equities/master) --------------------------------
    # 旧: /v1/listed/info → 新: /v2/equities/master
    # V2 フィールド: CoName（旧: CompanyName）, CoNameEn（旧: CompanyNameEnglish）
    name: Optional[str] = None
    try:
        master_resp = jquants_client.get("/equities/master", code=jq_code)
        master_list = _extract_data_records(master_resp, "/equities/master", jq_code)
        if master_list:
            item = master_list[0]
            name = item.get("CoName") or item.get("CoNameEn") or None
            logger.debug("J-Quants /equities/master %s: name=%s", jq_code, name)
        else:
            logger.warning("J-Quants /equities/master: 銘柄 %s の情報なし", jq_code)
    except ExternalAPIError:
        raise
    except Exception as exc:
        logger.warning("J-Quants /equities/master パースエラー %s: %s", jq_code, exc)

    # ---- 2. 直近株価 (/equities/bars/daily) --------------------------------
    # 旧: /v1/prices/daily_quotes → 新: /v2/equities/bars/daily
    # V2 フィールド: AdjC（調整済み終値, 旧: AdjustmentClose）, C（調整前終値, 旧: Close）
    close_price: Optional[float] = None
    try:
        bars_resp = jquants_client.get("/equities/bars/daily", code=jq_code)
        bars_list = _extract_data_records(bars_resp, "/equities/bars/daily", jq_code)
        if bars_list:
            latest = max(bars_list, key=lambda q: q.get("Date", ""))
            adj_c = latest.get("AdjC")
            close_price = _safe_num(adj_c if adj_c is not None else latest.get("C"))
            logger.debug(
                "J-Quants /equities/bars/daily %s: date=%s, close=%s",
                jq_code, latest.get("Date"), close_price,
            )
        else:
            logger.warning(
                "J-Quants /equities/bars/daily: 銘柄 %s の株価データなし", jq_code
            )
    except ExternalAPIError:
        raise
    except Exception as exc:
        logger.warning(
            "J-Quants /equities/bars/daily パースエラー %s: %s", jq_code, exc
        )

    # ---- 3. 財務サマリ (/fins/summary) -------------------------------------
    # 旧: /v1/fins/statements → 新: /v2/fins/summary
    # V2 フィールド名はすべて短縮形（旧名 → 新名）:
    #   NetSales → Sales, OperatingProfit → OP, Profit → NP
    #   EarningsPerShare → EPS, Equity → Eq, EquityToAssetRatio → EqAR
    #   ShOutFY: 期末発行済株式数, TrShFY: 期末自己株式数
    #   DivAnn: 一株あたり配当実績合計, FDivAnn: 一株あたり配当予想合計
    market_cap: Optional[float] = None
    per: Optional[float] = None
    revenue: Optional[float] = None
    operating_income: Optional[float] = None
    net_income: Optional[float] = None
    dividend_yield: Optional[float] = None
    roe: Optional[float] = None
    equity_ratio: Optional[float] = None
    _disc_date_for_ev: Optional[str] = None  # EV計算用に fins/details へ渡す開示日

    try:
        summary_resp = jquants_client.get("/fins/summary", code=jq_code)
        summary_list = _extract_data_records(summary_resp, "/fins/summary", jq_code)
        stmt = _select_fy_statement(summary_list)

        if stmt:
            _disc_date_for_ev = stmt.get("DiscDate")
            logger.debug(
                "J-Quants /fins/summary %s: CurPerType=%s, DiscDate=%s",
                jq_code, stmt.get("CurPerType"), _disc_date_for_ev,
            )

            revenue = _safe_num(stmt.get("Sales"))
            operating_income = _safe_num(stmt.get("OP"))
            net_income = _safe_num(stmt.get("NP"))
            equity_ratio = _safe_num(stmt.get("EqAR"))

            # 時価総額: 調整済み株価 × (発行済株式数 - 自己株式数)
            shares_total = _safe_num(stmt.get("ShOutFY"))
            shares_treasury = _safe_num(stmt.get("TrShFY"))
            if shares_total is not None and close_price is not None:
                shares_outstanding = shares_total - (shares_treasury or 0.0)
                if shares_outstanding > 0:
                    market_cap = close_price * shares_outstanding

            # PER: 株価 ÷ EPS（EPS が正の場合のみ）
            eps = _safe_num(stmt.get("EPS"))
            if close_price is not None and eps is not None and eps > 0:
                per = round(close_price / eps, 2)

            # ROE: 当期純利益 ÷ 純資産
            equity = _safe_num(stmt.get("Eq"))
            if net_income is not None and equity is not None and equity != 0:
                roe = round(net_income / equity, 4)

            # 配当利回り: 年間配当実績 ÷ 株価 × 100（実績優先 → 予想）
            div_annual = _safe_num(stmt.get("DivAnn"))
            if div_annual is None:
                div_annual = _safe_num(stmt.get("FDivAnn"))
            if div_annual is not None and close_price is not None and close_price != 0:
                dividend_yield = round(div_annual / close_price * 100, 4)

        else:
            logger.warning(
                "J-Quants /fins/summary: 銘柄 %s の財務データなし", jq_code
            )

    except ExternalAPIError:
        raise
    except Exception as exc:
        logger.warning(
            "J-Quants /fins/summary パースエラー %s: %s", jq_code, exc
        )

    # ---- 4. 企業価値（EV）(/fins/details) ----------------------------------
    # EV = 時価総額 + 有利子負債合計 - 現金及び現金等価物
    # fins/details の BS データから算出。会計基準（IFRS/J-GAAP/US）別に対応。
    # market_cap または disc_date が取得できない場合は null。
    enterprise_value: Optional[float] = None
    if market_cap is not None and _disc_date_for_ev:
        try:
            enterprise_value = _fetch_ev_from_details(
                jq_code, _disc_date_for_ev, market_cap
            )
        except ExternalAPIError as exc:
            logger.warning(
                "fins/details 取得失敗 %s (EV は null): %s", jq_code, exc.detail
            )

    return StockRecord(
        code=code,
        symbol=jq_code,  # J-Quants 形式のコード（.T サフィックスなし）
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
        updated_at=now,
    )
