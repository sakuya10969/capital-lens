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

# JPXの日本語IPOページ
JPX_IPO_URL = "https://www.jpx.co.jp/listing/stocks/new/index.html"


class IpoService:
    """JPXから最新のIPO上場情報を取得してパース"""

    async def get_latest_ipos(self) -> IpoLatestResponse:
        """構造化されたIPO上場情報を返却
        """
        timeout = float(settings.JPX_TIMEOUT)

        try:
            items = await self._fetch_and_parse(JPX_IPO_URL, timeout)
            if items:
                now = datetime.utcnow()
                return IpoLatestResponse(
                    items=items,
                    total_count=len(items),
                    generated_at=now,
                )
        except (ExternalAPIError, DataParsingError) as exc:
            logger.error("Failed to fetch from %s: %s", JPX_IPO_URL, exc)

        # 取得に失敗した場合、空の結果を返す
        return IpoLatestResponse(
            items=[],
            total_count=0,
            generated_at=datetime.utcnow(),
        )

    # 内部ヘルパー

    async def _fetch_and_parse(
        self, url: str, timeout: float
    ) -> List[IpoItem]:
        """指定された *url* からHTMLを取得し、IPOテーブルをパース"""
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
        """JPXのHTMLからIPOエントリーを抽出

    JPXは1エントリーにつき2行を使用するフォーマット:
      1行目 (8列): 上場日(rowspan=2) | 会社名(rowspan=2) | コード | ... | 公開価格 | 売買単位
      2行目 (6列): 市場区分 | ...
    連続する行をペアにして各 IpoItem を構築
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

            # メインの行は8列（日付と会社名は rowspan=2）
            if len(cols1) < 8:
                i += 1
                continue

            raw_date = cols1[0].get_text(strip=True)
            company_name = cols1[1].get_text(strip=True)
            ticker = cols1[2].get_text(strip=True)
            offering_price_raw = cols1[6].get_text(strip=True)

            # 次の行は市場区分を含む
            market = ""
            if i + 1 < len(rows):
                row2 = rows[i + 1]
                cols2 = row2.find_all("td") if isinstance(row2, Tag) else []
                if cols2:
                    market = cols2[0].get_text(strip=True)
                i += 2  # 両方の行をスキップ
            else:
                i += 1

            # 必須データがないエントリーをスキップ
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

    # パース用ユーティリティ

    @staticmethod
    def _parse_date(raw: str) -> date:
        """様々なJPXの日付フォーマットに対するベストエフォートな日付パース

    JPXの英語フォーマットの例:
      - "Apr. 02, 2026(Feb. 26, 2026)"  — 上場日 (申込日)
      - "Mar. 27, 2026(Feb. 20, 2026)"
    最初の日付（上場日）を抽出
    """
        # 括弧内のコンテンツ（申込日）を削除
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

        # フォールバック: 数字を抽出
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
        """'3,720' や '1,339.3' のようなテキストから数値の公開価格を抽出"""
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
        """IPO上場情報のシンプルなテキストサマリーを生成

    これは軽量で決定論的なサマライザーであり、LLMの呼び出しは行わない
    """
        market_label = f" {market}" if market else ""
        return (
            f"{company_name} は {listing_date.isoformat()} に"
            f"{market_label} 市場へ新規上場予定です。"
            "詳細な財務情報・事業戦略については、今後の開示資料をご参照ください。"
        )
