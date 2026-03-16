"""
J-Quants API V2 HTTPクライアント（インフラ層）。

V2 認証方式: ダッシュボードで発行した API キーを x-api-key ヘッダーで送信。
            トークン交換は不要。API キー自体に有効期限なし。

責務:
- x-api-key ヘッダーによる認証
- ステータスコードごとのエラーハンドリング（401/404/429など）
- レスポンスJSONのパース

ドメイン変換（StockRecord への変換）は上位層（infrastructure/jquants/fetcher.py）が行う。
"""

import logging
from typing import Any, Dict, Optional

import httpx

from src.core.config import settings
from src.core.exceptions import ExternalAPIError

logger = logging.getLogger(__name__)

_BASE_URL = "https://api.jquants.com/v2"


class JQuantsClient:
    """J-Quants API V2 の同期 HTTPクライアント。

    既存サービス層が asyncio.to_thread でスレッド実行するため、
    同期クライアント（httpx.Client）を使用する。
    """

    def __init__(self, timeout_seconds: float = 30.0) -> None:
        self._http = httpx.Client(
            base_url=_BASE_URL,
            timeout=httpx.Timeout(timeout_seconds),
        )

    def get(self, path: str, **params: Any) -> Dict[str, Any]:
        """認証済みGETリクエストを発行してJSONを返す。

        V2 認証: x-api-key ヘッダーに API キーをセット。

        Args:
            path: エンドポイントパス（例: "/equities/master"）
            **params: クエリパラメータ（None値は除外）

        Returns:
            パース済みのJSONレスポンス（dict）

        Raises:
            ExternalAPIError: 接続・認証・APIエラー時
        """
        api_key = settings.J_QUANTS_API_KEY
        if not api_key:
            raise ExternalAPIError(
                "jquants",
                "J_QUANTS_API_KEY が未設定です。.env を確認してください。",
            )

        headers = {"x-api-key": api_key}
        query = {k: v for k, v in params.items() if v is not None}

        try:
            resp = self._http.get(path, params=query, headers=headers)
        except httpx.RequestError as exc:
            raise ExternalAPIError(
                "jquants", f"ネットワークエラー ({path}): {exc}"
            ) from exc

        if resp.status_code == 401:
            raise ExternalAPIError(
                "jquants",
                f"APIキーが無効です (HTTP 401)。J-Quants ダッシュボードで再発行してください: {resp.text}",
            )
        if resp.status_code == 403:
            raise ExternalAPIError(
                "jquants",
                f"アクセス権限がありません (HTTP 403)。プランまたは API キーを確認してください: {resp.text}",
            )
        if resp.status_code == 404:
            raise ExternalAPIError(
                "jquants", f"データが見つかりません ({path}): {resp.text}"
            )
        if resp.status_code == 429:
            raise ExternalAPIError(
                "jquants",
                "レート制限に達しました (HTTP 429)。しばらく待ってから再試行してください。"
                "（Free: 5req/min, Light: 60req/min, Standard: 120req/min）",
            )
        if not resp.is_success:
            raise ExternalAPIError(
                "jquants",
                f"APIエラー (HTTP {resp.status_code}, {path}): {resp.text}",
            )

        try:
            return resp.json()  # type: ignore[no-any-return]
        except Exception as exc:
            raise ExternalAPIError(
                "jquants", f"JSONパースエラー ({path}): {exc}"
            ) from exc

    def close(self) -> None:
        self._http.close()


# アプリケーション全体で共有するシングルトンインスタンス
jquants_client = JQuantsClient(
    timeout_seconds=float(settings.J_QUANTS_TIMEOUT),
)
