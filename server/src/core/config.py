import os
from pathlib import Path

from dotenv import load_dotenv


def _load_env() -> None:
    """Load environment variables from server/.env regardless of cwd."""
    server_root = Path(__file__).resolve().parents[2]
    load_dotenv(server_root / ".env")
    load_dotenv()


def _getenv(*names: str, default: str = "") -> str:
    """Return the first non-empty environment variable among aliases."""
    for name in names:
        value = os.getenv(name)
        if value:
            return value
    return default


_load_env()


class Settings:
    """環境変数から読み込まれるアプリケーション設定。"""

    YFINANCE_TIMEOUT: int = int(os.getenv("YFINANCE_TIMEOUT", "15"))
    JPX_TIMEOUT: int = int(os.getenv("JPX_TIMEOUT", "15"))

    # Azure OpenAI（/api/ipo/{code}/summary の要約生成に使用）
    AZ_OPENAI_ENDPOINT: str = _getenv(
        "AZ_OPENAI_ENDPOINT",
        "AZURE_OPENAI_ENDPOINT",
    )
    AZ_OPENAI_API_KEY: str = _getenv(
        "AZ_OPENAI_API_KEY",
        "AZ_OPENAI_KEY",
        "AZURE_OPENAI_API_KEY",
    )
    AZ_OPENAI_DEPLOYMENT: str = _getenv(
        "AZ_OPENAI_DEPLOYMENT",
        "AZ_OPENAI_DEPLOYENT",
        "AZURE_OPENAI_DEPLOYMENT",
        default="gpt-4o",
    )
    AZ_OPENAI_API_VERSION: str = _getenv(
        "AZ_OPENAI_API_VERSION",
        "AZURE_OPENAI_API_VERSION",
        default="2024-10-21",
    )


settings = Settings()
