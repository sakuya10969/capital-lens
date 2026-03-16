# Capital Lens

日本および海外の資本市場の概況を一画面で把握するためのマーケットインテリジェンスプラットフォームです。

主要指数・為替・コモディティのリアルタイムスナップショット、直近の新規上場(IPO)情報、AI×コンサルティング銘柄のセクター分析を提供します。

## 技術スタック

| レイヤー | 技術 |
|---------|------|
| フロントエンド | Next.js 16 / React 19 / TypeScript 5 / Tailwind CSS 4 |
| バックエンド | FastAPI / Python 3.12+ / Pydantic |
| データソース | Yahoo Finance (yfinance) / JPX (スクレイピング) / Azure OpenAI |
| パッケージ管理 | pnpm (client) / uv (server) |

## 前提条件

- Node.js 20+
- Python 3.12+
- [pnpm](https://pnpm.io/)
- [uv](https://docs.astral.sh/uv/)

## セットアップ

```bash
# 依存関係の一括インストール
make install
```

### 環境変数

`server/.env` に以下を設定してください。

```env
AZ_OPENAI_ENDPOINT=https://your-endpoint.cognitiveservices.azure.com/
AZ_OPENAI_API_KEY=your-api-key
AZ_OPENAI_DEPLOYMENT=your-deployment-name
AZ_OPENAI_API_VERSION=2025-04-01-preview
```

`client/.env` はデフォルトで `http://localhost:8000` を参照します。変更が必要な場合のみ編集してください。

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## 開発

```bash
# フロントエンド + バックエンドを同時起動
make dev

# 個別に起動する場合
make dev-client   # Next.js (port 3000)
make dev-server   # FastAPI  (port 8000)
```

## ビルド

```bash
make build
```

- フロントエンド: `client/out/` に静的ファイルを出力
- バックエンド: `python -c "import src.main"` でインポートチェック

## API エンドポイント

| メソッド | パス | 説明 |
|---------|------|------|
| GET | `/api/market/overview` | 主要指数・債券・為替・コモディティの概況 |
| GET | `/api/ipo/latest` | 直近の新規上場銘柄一覧 |
| GET | `/api/ipo/{code}/summary` | 指定銘柄の目論見書 AI 要約 |
| GET | `/api/ai-consulting/stocks` | AI×コンサル銘柄一覧 |
| POST | `/api/ai-consulting/stocks` | 銘柄追加 |
| DELETE | `/api/ai-consulting/stocks/{code}` | 銘柄削除 |
| POST | `/api/ai-consulting/stocks/{code}/refresh` | 銘柄データ再取得 |
| POST | `/api/ai-consulting/stocks/refresh-all` | 全銘柄データ再取得 |
| GET | `/api/ai-consulting/per` | PER 一覧 |
| GET | `/api/ai-consulting/earnings` | 決算期銘柄の解説 |
| POST | `/api/ai-consulting/report` | 統合レポート生成 |
| GET | `/health` | ヘルスチェック |

## プロジェクト構成

```
capital-lens/
├── client/                # Next.js フロントエンド
│   └── src/
│       ├── app/           # App Router (ページ・レイアウト)
│       ├── components/    # React コンポーネント (機能別)
│       ├── lib/           # API クライアント・ユーティリティ
│       └── types/         # TypeScript 型定義
├── server/                # FastAPI バックエンド
│   └── src/
│       ├── routers/       # API ルートハンドラ
│       ├── services/      # ビジネスロジック
│       ├── schemas/       # Pydantic スキーマ
│       ├── utils/         # 共通ユーティリティ
│       └── core/          # 設定・例外定義
└── Makefile               # 開発コマンド
```

## デプロイ

バックエンドは Docker コンテナとしてデプロイできます。

```bash
cd server
docker build -t capital-lens-api .
docker run -p 8000:8000 --env-file .env capital-lens-api
```

フロントエンドは `pnpm build` で生成される `client/out/` を任意の静的ホスティングに配置してください。
