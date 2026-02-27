import logging
import re
from datetime import date, datetime
from typing import List, Optional

import httpx
from bs4 import BeautifulSoup, Tag

from src.core.config import settings
from src.core.exceptions import DataParsingError, ExternalAPIError
from src.schemas.ipo import IpoItem, IpoLatestResponse

logger = logging.getLogger(__name__)

# JPX English IPO page
JPX_IPO_URL = "https://www.jpx.co.jp/english/listing/stocks/new/index.html"

# Fallback: Japanese IPO page
JPX_IPO_URL_JA = "https://www.jpx.co.jp/listing/stocks/new/index.html"


class IpoService:
    """Fetches and parses the latest IPO listings from JPX."""

    async def get_latest_ipos(self) -> IpoLatestResponse:
        """Return structured IPO listing information.

        Attempts the English JPX page first, falls back to the Japanese page.
        """
        timeout = float(settings.JPX_TIMEOUT)

        for url in [JPX_IPO_URL, JPX_IPO_URL_JA]:
            try:
                items = await self._fetch_and_parse(url, timeout)
                if items:
                    now = datetime.utcnow()
                    return IpoLatestResponse(
                        items=items,
                        total_count=len(items),
                        generated_at=now,
                    )
            except (ExternalAPIError, DataParsingError) as exc:
                logger.warning("Failed to fetch from %s: %s", url, exc)
                continue

        # If all attempts fail, return an empty result
        logger.error("All JPX IPO fetch attempts failed.")
        return IpoLatestResponse(
            items=[],
            total_count=0,
            generated_at=datetime.utcnow(),
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _fetch_and_parse(
        self, url: str, timeout: float
    ) -> List[IpoItem]:
        """Fetch HTML from *url* and parse the IPO table."""
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.get(url)
                response.raise_for_status()
        except httpx.TimeoutException as exc:
            raise ExternalAPIError("JPX", f"Timeout: {exc}") from exc
        except httpx.HTTPStatusError as exc:
            raise ExternalAPIError(
                "JPX", f"HTTP {exc.response.status_code}"
            ) from exc
        except httpx.RequestError as exc:
            raise ExternalAPIError("JPX", str(exc)) from exc

        return self._parse_html(response.text)

    def _parse_html(self, html: str) -> List[IpoItem]:
        """Extract IPO entries from JPX HTML.

        JPX uses a 2-row-per-entry format:
          Row 1 (8 cols): Date(rowspan=2) | Company(rowspan=2) | Ticker | ... | OfferingPrice | Unit
          Row 2 (6 cols): Market | ...
        We pair consecutive rows to build each IpoItem.
        """
        soup = BeautifulSoup(html, "lxml")

        table = (
            soup.find("table", class_=re.compile(r"component.*table"))
            or soup.find("table")
        )
        if table is None:
            raise DataParsingError("JPX", "No table element found on page.")

        tbody = table.find("tbody") if isinstance(table, Tag) else None
        rows = tbody.find_all("tr") if tbody else table.find_all("tr")  # type: ignore[union-attr]

        items: List[IpoItem] = []
        i = 0

        while i < len(rows):
            row1 = rows[i]
            cols1 = row1.find_all("td") if isinstance(row1, Tag) else []

            # Primary row has 8 columns (with rowspan=2 on date & company)
            if len(cols1) < 8:
                i += 1
                continue

            raw_date = cols1[0].get_text(strip=True)
            company_name = cols1[1].get_text(strip=True)
            ticker = cols1[2].get_text(strip=True)
            offering_price_raw = cols1[6].get_text(strip=True)

            # Next row contains the market segment
            market = ""
            if i + 1 < len(rows):
                row2 = rows[i + 1]
                cols2 = row2.find_all("td") if isinstance(row2, Tag) else []
                if cols2:
                    market = cols2[0].get_text(strip=True)
                i += 2  # Skip both rows
            else:
                i += 1

            # Skip entries without essential data
            if not company_name or not ticker:
                continue

            listing_date = self._parse_date(raw_date)
            offering_price = self._parse_price_text(offering_price_raw)
            summary = self._generate_summary(company_name, market, listing_date)

            items.append(
                IpoItem(
                    company_name=company_name,
                    ticker=ticker,
                    market=market,
                    listing_date=listing_date,
                    offering_price=offering_price,
                    summary=summary,
                    generated_at=datetime.utcnow(),
                )
            )

        return items

    # ------------------------------------------------------------------
    # Parsing utilities
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_date(raw: str) -> date:
        """Best-effort date parsing for various JPX date formats.

        JPX English format examples:
          - "Apr. 02, 2026(Feb. 26, 2026)"  — listing date (application date)
          - "Mar. 27, 2026(Feb. 20, 2026)"
        We extract the first date (listing date).
        """
        # Strip parenthesised content (application date)
        clean = re.sub(r"\(.*?\)", "", raw).strip()

        for fmt in (
            "%b. %d, %Y",   # "Apr. 02, 2026"
            "%b %d, %Y",    # "Apr 02, 2026"
            "%Y/%m/%d",     # "2026/02/20"
            "%Y年%m月%d日",  # "2026年02月20日"
        ):
            try:
                return datetime.strptime(clean, fmt).date()
            except ValueError:
                continue

        # Fallback: extract digits
        digits = re.findall(r"\d+", clean)
        if len(digits) >= 3:
            try:
                return date(int(digits[0]), int(digits[1]), int(digits[2]))
            except (ValueError, IndexError):
                pass

        logger.warning("Unparseable date '%s', falling back to today.", raw)
        return date.today()

    @staticmethod
    def _parse_price_text(text: str) -> Optional[float]:
        """Extract a numeric offering price from text like '3,720' or '1,339.3'."""
        cleaned = text.replace(",", "").strip()
        digits = re.sub(r"[^\d.]", "", cleaned)
        if digits:
            try:
                return float(digits)
            except ValueError:
                pass
        return None

    @staticmethod
    def _generate_summary(
        company_name: str, market: str, listing_date: date
    ) -> str:
        """Generate a simple text summary for an IPO listing.

        This is a lightweight, deterministic summariser — no LLM calls.
        """
        market_label = f" {market}" if market else ""
        return (
            f"{company_name} は {listing_date.isoformat()} に"
            f"{market_label} 市場へ新規上場予定です。"
            "詳細な財務情報・事業戦略については、今後の開示資料をご参照ください。"
        )
