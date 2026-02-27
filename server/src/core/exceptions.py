class ExternalAPIError(Exception):
    """外部API(yfinance, FRED, JPXなど)の呼び出しに失敗した際に発生"""

    def __init__(self, source: str, detail: str = ""):
        self.source = source
        self.detail = detail
        super().__init__(f"External API error from {source}: {detail}")


class DataParsingError(Exception):
    """レスポンスデータが正しくパースできない際に発生"""

    def __init__(self, source: str, detail: str = ""):
        self.source = source
        self.detail = detail
        super().__init__(f"Data parsing error from {source}: {detail}")
