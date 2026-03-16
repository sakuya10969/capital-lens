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
from typing import Any, Dict, List, Optional

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
    stmt: Optional[Dict[str, Any]] = None
    equity: Optional[float] = None
    try:
        summary_resp = jquants_client.get("/fins/summary", code=jq_code)
        summary_list = _extract_data_records(summary_resp, "/fins/summary", jq_code)
        stmt = _select_fy_statement(summary_list)

        if stmt:
            logger.debug(
                "J-Quants /fins/summary %s: CurPerType=%s, DiscDate=%s",
                jq_code, stmt.get("CurPerType"), stmt.get("DiscDate"),
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

    # ---- 4. 企業価値（EV） -------------------------------------------------
    # 有利子負債の明細は無料プランでは取得不可のため、以下の概算式を使用:
    #   EV = 時価総額 + 負債合計（TA - Eq）- 現金及び現金同等物（CashEq）
    # 負債合計には有利子負債以外（買掛金等）も含まれるため過大評価になりやすい点に注意。
    enterprise_value: Optional[float] = None
    if stmt:
        total_assets = _safe_num(stmt.get("TA"))
        cash_eq = _safe_num(stmt.get("CashEq"))
        # equity は上記ブロックで取得済み
        if market_cap is not None and total_assets is not None and equity is not None:
            total_debt = total_assets - equity  # 負債合計（概算）
            ev = market_cap + total_debt - (cash_eq or 0.0)
            if ev > 0:
                enterprise_value = round(ev, 0)

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
