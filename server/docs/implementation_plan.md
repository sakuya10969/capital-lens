# Implementation Plan — Capital Lens Backend APIs

## 1. 概要

`server/` ディレクトリ配下に FastAPI で以下2つのエンドポイントを実装する。

1. **`GET /api/market/overview`** — 直近の資本市場の状況（株価指数・債券・為替・商品）
2. **`GET /api/ipo/latest`** — 新規上場銘柄（IPO）の解説

## 2. ファイル構成

```text
server/
├── main.py                          # uvicorn 起動エントリーポイント
├── pyproject.toml                   # 依存パッケージ定義
├── .env                             # 環境変数 (FRED_API_KEY 等)
├── src/
│   ├── __init__.py
│   ├── main.py                      # FastAPI app 定義, ミドルウェア, 例外ハンドラー
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py                # Settings (環境変数, タイムアウト)
│   │   └── exceptions.py            # ExternalAPIError, DataParsingError
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── market.py                # GET /api/market/overview
│   │   └── ipo.py                   # GET /api/ipo/latest
│   ├── services/
│   │   ├── __init__.py
│   │   ├── market.py                # MarketService (yfinance + FRED)
│   │   └── ipo.py                   # IpoService (JPX スクレイピング)
│   └── schemas/
│       ├── __init__.py
│       ├── market.py                # MarketItem, MarketOverviewResponse
│       └── ipo.py                   # IpoItem, IpoLatestResponse
└── docs/
    └── implementation_plan.md       # 本ファイル
```

## 3. データフロー

### 3.1 `/api/market/overview`

```
Client
  → Router (routers/market.py)
    → MarketService.get_market_overview()
      ├── asyncio.gather (並行実行)
      │   ├── yfinance × 9 items (indices/bonds/fx/commodities)
      │   │   └── asyncio.to_thread + asyncio.wait_for (15秒タイムアウト)
      │   └── FRED US 10Y
      │       └── asyncio.to_thread + asyncio.wait_for (10秒タイムアウト)
      └── → MarketOverviewResponse (Pydantic)
  → JSON Response
```

### 3.2 `/api/ipo/latest`

```
Client
  → Router (routers/ipo.py)
    → IpoService.get_latest_ipos()
      ├── httpx.AsyncClient → JPX (EN) ← 15秒タイムアウト
      │   └── (失敗時) → JPX (JA) へフォールバック
      ├── BeautifulSoup でHTML解析
      ├── _parse_date() / _parse_price() / _generate_summary()
      └── → IpoLatestResponse (Pydantic)
  → JSON Response
```

## 4. 外部API利用箇所

| 外部API                                        | ライブラリ                 | サービス             | タイムアウト |
| ---------------------------------------------- | -------------------------- | -------------------- | ------------ |
| Yahoo Finance (株価指数・為替・商品・日本国債) | `yfinance`                 | `services/market.py` | 15秒         |
| FRED (米国10年国債利回り DGS10)                | `fredapi`                  | `services/market.py` | 10秒         |
| JPX 新規上場銘柄一覧                           | `httpx` + `beautifulsoup4` | `services/ipo.py`    | 15秒         |

## 5. 設計方針

- **ルーター / サービス / スキーマ の完全分離** — ルーターにビジネスロジックなし
- **Dependency Injection** — `Depends()` で MarketService / IpoService を注入
- **非同期ファースト** — ブロッキングI/Oは `asyncio.to_thread` で非同期化
- **タイムアウト** — 全ての外部API呼び出しに `asyncio.wait_for` / httpx timeout を設定
- **エラーハンドリング** — カスタム例外 (`ExternalAPIError`, `DataParsingError`) + グローバル例外ハンドラー
- **DB不要** — 現時点ではインメモリ。将来的にリポジトリ層を追加可能な構造
- **MVPレベル** — 過度な抽象化は避け、可読性・拡張性を重視

## 6. レスポンス形式

### MarketOverviewResponse

```json
{
  "indices": [{"name": "...", "current_price": 0.0, "change": 0.0, "change_percent": 0.0}],
  "bonds": [...],
  "fx": [...],
  "commodities": [...],
  "generated_at": "2026-02-27T02:00:00"
}
```

### IpoLatestResponse

```json
{
  "items": [
    {
      "company_name": "...",
      "ticker": "...",
      "market": "...",
      "listing_date": "2026-02-20",
      "offering_price": null,
      "summary": "...",
      "generated_at": "2026-02-27T02:00:00"
    }
  ],
  "total_count": 1,
  "generated_at": "2026-02-27T02:00:00"
}
```
