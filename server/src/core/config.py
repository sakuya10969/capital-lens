import os

from dotenv import load_dotenv

load_dotenv()


class Settings:
    """Application settings loaded from environment variables."""

    YFINANCE_TIMEOUT: int = int(os.getenv("YFINANCE_TIMEOUT", "15"))
    JPX_TIMEOUT: int = int(os.getenv("JPX_TIMEOUT", "15"))


settings = Settings()
