import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    """Application settings loaded from environment variables."""

    FRED_API_KEY: str = os.getenv("FRED_API_KEY", "")

    # Timeout settings (seconds)
    YFINANCE_TIMEOUT: int = int(os.getenv("YFINANCE_TIMEOUT", "15"))
    FRED_TIMEOUT: int = int(os.getenv("FRED_TIMEOUT", "10"))
    JPX_TIMEOUT: int = int(os.getenv("JPX_TIMEOUT", "15"))


settings = Settings()
