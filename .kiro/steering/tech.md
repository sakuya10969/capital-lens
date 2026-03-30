---
inclusion: always
---

# Capital Lens — 技術スタック

## アーキテクチャ概要

Capital Lensはフロントエンドとバックエンドが明確に分離されたフルスタックアプリケーションです:
- フロントエンド: Next.js (React) + TypeScript
- バックエンド: FastAPI (Python) + async/await
- 通信: REST API over HTTP
- デプロイ: 静的エクスポート（フロントエンド）+ コンテナ化API（バックエンド）

## フロントエンドスタック

### コア技術
- Next.js 16 (App Router)
- React 19
- TypeScript 5
- Tailwind CSS 4

### 主要ライブラリ
- `lucide-react`: アイコン
- `clsx` + `tailwind-merge`: 条件付きスタイリング
- カスタムUIコンポーネント（card, table）

### レンダリング戦略
- サーバーサイドレンダリング（SSR）: マーケット概況
- クライアントサイドレンダリング: IPOテーブル、AIコンサルティング（インタラクティブ機能）
- 可能な箇所では静的生成

### API連携
- HTTPクライアントは `src/lib/http/client.ts` に抽象化
- API関数は `src/lib/api/`（market, ipo, ai-consulting）
- TypeScriptインターフェースによる型安全なレスポンス

### 開発環境
- パッケージマネージャー: pnpm
- 開発サーバー: `pnpm dev`（ポート3000）
- ビルド: `pnpm build`（`out/` への静的エクスポート）
- リンティング: ESLint + Next.js設定

## バックエンドスタック

### コア技術
- FastAPI（非同期Webフレームワーク）
- Python 3.12+
- Pydantic（データバリデーション）
- uvicorn（ASGIサーバー）

### 主要ライブラリ
- `yfinance`: 市場データ（Yahoo Finance）
- `httpx`: 非同期HTTPリクエスト
- `beautifulsoup4` + `lxml`: HTMLパーシング
- `pdfplumber`: PDFテキスト抽出
- `openai`: Azure OpenAI連携
- `pandas`: データ操作
- `apscheduler`: スケジュールタスク（将来用）

### API設計
- `/api/` 配下のRESTfulエンドポイント
- PydanticスキーマによるJSONレスポンス
- ローカル開発用にCORS有効化
- 外部APIエラー用のグローバル例外ハンドラー

### サービス層
- サービスがビジネスロジックをカプセル化
- `asyncio` による非同期ファーストの設計
- すべての外部呼び出しにタイムアウト保護
- 高コスト処理のインメモリキャッシュ（TTL 24時間）

### 開発環境
- パッケージマネージャー: uv (Python)
- 開発サーバー: `uvicorn src.main:app --reload`
- フォーマッター: black
- 環境設定: `.env` ファイルでAPIキー管理

## データソース

### 市場データ
- Yahoo Finance（yfinance経由）: 指数、債券、為替、コモディティ
- 無料枠、APIキー不要
- タイムアウト: リクエストあたり15秒
- `asyncio.gather` による並列フェッチ

### IPOデータ
- JPX（日本取引所グループ）ウェブサイト
- 公開HTMLテーブルのWebスクレイピング
- サマリー用の目論見書PDFダウンロード
- タイムアウト: HTML 15秒、PDF 30秒

### AIサマリー
- Azure OpenAI（GPT-4等）
- `AZURE_OPENAI_ENDPOINT` と `AZURE_OPENAI_API_KEY` が必要
- IPO目論見書の要約に使用
- コスト削減のため24時間キャッシュ

### AI・コンサルティングティッカー
- 静的JSON設定: `server/config/ai_consulting_tickers.json`
- 手動キュレーションされた企業名・ティッカーシンボルのリスト
- yfinance経由でPER・決算データを取得

## スケジューリングのコンセプト

現在の実装はオンデマンド（ユーザーがダッシュボードにアクセスした際にデータ取得）です。

週次自動化に向けて:
- `apscheduler` は依存関係に含まれている
- 毎週金曜日にデータをプリフェッチ・キャッシュするタスクをスケジュール可能
- レポート生成・保存のトリガーも可能
- 未実装 — システムはサポートできる設計

## 開発環境

### 前提条件
- Node.js 20+（フロントエンド）
- Python 3.12+（バックエンド）
- pnpm（フロントエンドパッケージマネージャー）
- uv（Pythonパッケージマネージャー）

### ローカルセットアップ
1. バックエンド: `cd server && uv sync && uvicorn src.main:app --reload`
2. フロントエンド: `cd client && pnpm install && pnpm dev`
3. 環境変数: 両ディレクトリの `.env` ファイル

### 必要なAPIキー
- Azure OpenAI: `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_DEPLOYMENT`
- yfinanceやJPXスクレイピングにはキー不要

## デプロイ

### バックエンド
- `server/` にDockerfileを提供
- デプロイスクリプト: `server/deploy.sh`
- コンテナ化サービスとして実行
- 環境変数はランタイムに注入

### フロントエンド
- 静的エクスポート: `pnpm build` で `out/` ディレクトリを生成
- 任意の静的ファイルサーバーでホスト可能
- 環境変数: `NEXT_PUBLIC_API_BASE_URL` でバックエンドを指定

## エラーハンドリング

- カスタム例外: `ExternalAPIError`, `DataParsingError`
- グローバル例外ハンドラーが構造化JSONエラーを返却
- フロントエンドはユーザーフレンドリーなエラーメッセージを表示
- グレースフルデグラデーション: 1つのデータソースが失敗しても他は正常にレンダリング

## パフォーマンスの考慮事項

- 並列データフェッチによるレイテンシ削減
- タイムアウトによるリクエストのハング防止
- 高コスト処理のインメモリキャッシュ
- 可能な箇所での静的生成（フロントエンド）
- バックエンド全体での非同期I/O
