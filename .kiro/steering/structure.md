---
inclusion: always
---

# Capital Lens — リポジトリ構成

## 全体レイアウト

```
capital-lens/
├── client/          # Next.js フロントエンド
├── server/          # FastAPI バックエンド
├── .github/         # GitHub Actions ワークフロー
└── .kiro/           # Kiro ステアリングドキュメント
```

フロントエンドとバックエンドが明確に分離されたモノレポ構成です。それぞれ独自の依存関係、ビルドプロセス、デプロイ戦略を持ちます。

## フロントエンド構成 (`client/`)

```
client/
├── src/
│   ├── app/                 # Next.js App Router
│   │   ├── layout.tsx       # ルートレイアウト
│   │   ├── page.tsx         # ホームページ（ダッシュボード）
│   │   └── globals.css      # グローバルスタイル
│   ├── components/          # Reactコンポーネント
│   │   ├── market-overview.tsx
│   │   ├── ipo-table.tsx
│   │   ├── ai-consulting.tsx
│   │   └── ui/              # 再利用可能なUIプリミティブ
│   ├── lib/
│   │   ├── api/             # APIクライアント関数
│   │   ├── http/            # HTTPクライアント抽象化
│   │   ├── formatters/      # データフォーマットユーティリティ
│   │   └── utils.ts         # 汎用ユーティリティ
│   └── types/               # TypeScript型定義
├── public/                  # 静的アセット
├── package.json
├── next.config.ts
└── tsconfig.json
```

### フロントエンドの規約

- コンポーネントは機能別に整理（market, ipo, ai-consulting）
- UIプリミティブは `components/ui/` に配置
- API呼び出しは `lib/api/` に抽象化（機能ごとに1ファイル）
- 型定義はバックエンドのスキーマと対応（`types/`）
- デフォルトはサーバーコンポーネント、クライアントコンポーネントは `"use client"` を明記

### フロントエンド機能の追加先

- 新しいダッシュボードセクション → `src/components/` に新コンポーネント
- 新しいAPIエンドポイント → `src/lib/api/` に新関数
- 新しいデータ型 → `src/types/` に新ファイル
- 新しいページ → `src/app/` に新ルート

## バックエンド構成 (`server/`)

```
server/
├── src/
│   ├── main.py              # FastAPIアプリのエントリーポイント
│   ├── core/
│   │   ├── config.py        # 設定（環境変数、タイムアウト）
│   │   └── exceptions.py    # カスタム例外クラス
│   ├── routers/             # APIルートハンドラー
│   │   ├── market.py        # GET /api/market/overview
│   │   ├── ipo.py           # GET /api/ipo/latest, /api/ipo/summary/{code}
│   │   └── ai_consulting.py # GET /api/ai-consulting/*
│   ├── services/            # ビジネスロジック層
│   │   ├── market.py
│   │   ├── ipo.py
│   │   └── ai_consulting.py
│   ├── schemas/             # Pydanticモデル（リクエスト/レスポンス）
│   │   ├── market.py
│   │   ├── ipo.py
│   │   └── ai_consulting.py
│   └── utils/               # 共有ユーティリティ
│       ├── yfinance.py      # Yahoo Financeヘルパー
│       ├── jpx_parser.py    # JPX HTMLパーシング
│       ├── pdf.py           # PDFテキスト抽出
│       └── llm.py           # Azure OpenAI連携
├── config/
│   └── ai_consulting_tickers.json  # キュレーション済みティッカーリスト
├── docs/
│   └── implementation_plan.md      # 設計ドキュメント
├── pyproject.toml
├── Dockerfile
└── deploy.sh
```

### バックエンドの規約

- RoutersはHTTP関連の処理（リクエスト/レスポンス）を担当
- Servicesはビジネスロジック（データ取得、変換）を含む
- Schemasはデータ契約を定義（Pydanticモデル）
- Utilsは再利用可能なステートレス関数
- データベース層なし（インメモリのみ）

### 依存性注入

FastAPIの `Depends()` を使用してサービスをルーターに注入:

```python
@router.get("/api/market/overview")
async def get_market_overview(service: MarketService = Depends()):
    return await service.get_market_overview()
```

ルーターを薄く保ち、サービスをテスト可能にします。

### バックエンド機能の追加先

- 新しいAPIエンドポイント → `src/routers/` に新ルーター
- 新しいデータソース → `src/services/` に新サービス
- 新しい外部API連携 → `src/utils/` に新ユーティリティ
- 新しいレスポンス形式 → `src/schemas/` に新スキーマ
- 新しい設定 → `src/core/config.py` に追加

## 共通コンセプト

### 型の整合性

フロントエンドの型（`client/src/types/`）はバックエンドのスキーマ（`server/src/schemas/`）と対応させます。新しいAPIエンドポイントを追加する際:

1. バックエンドでPydanticスキーマを定義
2. フロントエンドで対応するTypeScriptインターフェースを作成
3. APIクライアント関数でそのインターフェースを使用

### エラーハンドリング

- バックエンドはカスタム例外を送出（`ExternalAPIError`, `DataParsingError`）
- グローバル例外ハンドラーが構造化JSONに変換
- フロントエンドはレスポンスステータスを確認し、ユーザーフレンドリーなメッセージを表示

### 設定

- バックエンド: `server/` の `.env` ファイル（APIキー、タイムアウト）
- フロントエンド: `client/` の `.env.local`（APIベースURL）
- ティッカーリスト: `server/config/ai_consulting_tickers.json`

## テスト戦略（将来）

現時点ではテスト未実装。テスト追加時:

- フロントエンド: Jest + React Testing Library（`client/src/__tests__/`）
- バックエンド: pytest（`server/tests/`）
- E2E: Playwright（`tests/e2e/`）

## ドキュメント

- 実装計画: `server/docs/implementation_plan.md`
- ステアリングドキュメント: `.kiro/steering/`
- READMEファイル: `client/` と `server/`（現時点では最小限）

## デプロイ成果物

- フロントエンド: `client/out/`（静的エクスポート）
- バックエンド: `server/Dockerfile` からビルドされるDockerイメージ
- デプロイスクリプト: `server/deploy.sh`（バックエンドのみ）

## 全般的なガイドライン

- フロントエンドとバックエンドは疎結合に保つ（REST APIで通信）
- フロントエンドとバックエンド間でロジックを重複させない
- 型安全性のためにTypeScript/Pydanticを使用
- I/O操作にはasync/awaitを優先
- すべてのレイヤーでエラーをグレースフルに処理
- 複雑なロジックにはインラインコメントで文書化
- 設定は環境変数に保持し、ハードコードしない
