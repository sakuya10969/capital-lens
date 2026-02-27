class ExternalAPIError(Exception):
    """Raised when an external API call fails (yfinance, FRED, JPX, etc.)."""

    def __init__(self, source: str, detail: str = ""):
        self.source = source
        self.detail = detail
        super().__init__(f"External API error from {source}: {detail}")


class DataParsingError(Exception):
    """Raised when response data cannot be parsed correctly."""

    def __init__(self, source: str, detail: str = ""):
        self.source = source
        self.detail = detail
        super().__init__(f"Data parsing error from {source}: {detail}")
