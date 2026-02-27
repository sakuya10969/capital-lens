import os

from dotenv import load_dotenv

load_dotenv()


class Settings:
    """環境変数から読み込まれるアプリケーション設定。"""

    YFINANCE_TIMEOUT: int = int(os.getenv("YFINANCE_TIMEOUT", "15"))
    JPX_TIMEOUT: int = int(os.getenv("JPX_TIMEOUT", "15"))


settings = Settings()
