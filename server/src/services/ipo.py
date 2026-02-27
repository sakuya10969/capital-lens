import io
import logging
import re
from datetime import date, datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple

import httpx
import pdfplumber
from bs4 import BeautifulSoup, NavigableString, Tag
from openai import AsyncAzureOpenAI

from src.core.config import settings
from src.core.exceptions import DataParsingError, ExternalAPIError
from src.schemas.ipo import IpoItem, IpoLatestResponse, IpoSummaryResponse

logger = logging.getLogger(__name__)

# JPXの日本語IPOページ
JPX_IPO_URL = "https://www.jpx.co.jp/listing/stocks/new/index.html"
JPX_BASE_URL = "https://www.jpx.co.jp"

# サーバーサイドキャッシュ（プロセス内メモリ、24h TTL）
_SUMMARY_CACHE: Dict[str, Tuple[IpoSummaryResponse, datetime]] = {}
_CACHE_TTL = timedelta(hours=24)


class IpoService:
    """JPXから最新のIPO上場情報を取得してパース。
    重い処理（PDF取得・LLM要約）は get_ipo_summary にのみ集約する。
    """

    # Public API                                                           #
    async def get_latest_ipos(self) -> IpoLatestResponse:
        """軽量な IPO 一覧を返す（PDF/LLM 呼び出しなし）"""
        timeout = float(settings.JPX_TIMEOUT)

        try:
            items = await self._fetch_and_parse(JPX_IPO_URL, timeout)
            if items:
                return IpoLatestResponse(
                    items=items,
                    total_count=len(items),
                    generated_at=datetime.utcnow(),
                )
        except (ExternalAPIError, DataParsingError) as exc:
            logger.error("Failed to fetch from %s: %s", JPX_IPO_URL, exc)

        return IpoLatestResponse(
            items=[],
            total_count=0,
            generated_at=datetime.utcnow(),
        )

    async def get_ipo_summary(self, code: str) -> IpoSummaryResponse:
        """指定コードの IPO 企業概要を PDF → LLM で要約して返す。
        24h サーバーキャッシュあり。
        """
        now = datetime.now(tz=timezone.utc)

        # キャッシュヒット
        if code in _SUMMARY_CACHE:
            cached_resp, cached_at = _SUMMARY_CACHE[code]
            if now - cached_at < _CACHE_TTL:
                logger.info("Cache hit for summary: %s", code)
                return IpoSummaryResponse(
                    code=cached_resp.code,
                    bullets=cached_resp.bullets,
                    cached=True,
                    generated_at=cached_resp.generated_at,
                )

        # PDF URL を一覧ページから探す
        pdf_url = await self._find_pdf_url_for_code(code)

        # PDF テキスト抽出
        text = ""
        if pdf_url:
            try:
                text = await self._extract_pdf_text(pdf_url)
            except Exception as exc:
                logger.warning("PDF extraction failed for %s (%s): %s", code, pdf_url, exc)

        # Azure OpenAI で要約
        bullets = await self._summarize_with_llm(code, text)

        resp = IpoSummaryResponse(
            code=code,
            bullets=bullets,
            cached=False,
            generated_at=now,
        )
        _SUMMARY_CACHE[code] = (resp, now)
        return resp

    # PDF 取得・テキスト抽出                                               #
    async def _find_pdf_url_for_code(self, code: str) -> Optional[str]:
        """JPX一覧ページをスクレイピングして指定コードの企業概要 PDF URL を返す"""
        timeout = float(settings.JPX_TIMEOUT)
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.get(JPX_IPO_URL)
                response.raise_for_status()
        except Exception as exc:
            logger.warning("Could not fetch JPX page for PDF URL lookup: %s", exc)
            return None

        soup = BeautifulSoup(response.text, "lxml")

        # コードが含まれる <tr> 内の PDF リンクを探す
        for row in soup.find_all("tr"):
            if not isinstance(row, Tag):
                continue
            row_text = row.get_text()
            if code not in row_text:
                continue
            a_tag = row.find("a", href=re.compile(r"\.pdf", re.IGNORECASE))
            if a_tag and isinstance(a_tag, Tag):
                href = str(a_tag.get("href", ""))
                if href:
                    return _resolve_url(JPX_BASE_URL, href)

        return None

    async def _extract_pdf_text(self, pdf_url: str, max_pages: int = 5) -> str:
        """PDF をダウンロードして pdfplumber でテキスト抽出する（先頭 max_pages ページ）"""
        timeout = float(settings.JPX_TIMEOUT) * 2
        async with httpx.AsyncClient(
            timeout=timeout, follow_redirects=True
        ) as client:
            resp = await client.get(pdf_url)
            resp.raise_for_status()

        buf = io.BytesIO(resp.content)
        texts: List[str] = []
        with pdfplumber.open(buf) as pdf:
            for page in pdf.pages[:max_pages]:
                page_text = page.extract_text() or ""
                texts.append(page_text)
        return "\n".join(texts)

    # Azure OpenAI 要約                                                   #
    async def _summarize_with_llm(self, code: str, text: str) -> List[str]:
        """Azure OpenAI を使って会社概要を 4〜8 箇条書きに要約する"""
        if not settings.AZ_OPENAI_ENDPOINT or not settings.AZ_OPENAI_API_KEY:
            logger.warning(
                "Azure OpenAI not configured. Set AZ_OPENAI_ENDPOINT and "
                "AZ_OPENAI_API_KEY to enable summaries."
            )
            return [
                f"銘柄コード {code} の要約を生成するには Azure OpenAI の設定が必要です。"
                "（AZ_OPENAI_ENDPOINT / AZ_OPENAI_API_KEY を設定してください）"
            ]

        client = AsyncAzureOpenAI(
            azure_endpoint=settings.AZ_OPENAI_ENDPOINT,
            api_key=settings.AZ_OPENAI_API_KEY,
            api_version=settings.AZ_OPENAI_API_VERSION,
        )

        system_prompt = (
            "あなたはIPO企業の事業概要をまとめる専門家です。"
            "提供された会社概要テキストを日本語で4〜8項目の箇条書きにまとめてください。"
            "各項目は「・」で始め、1行で完結させてください。"
            "テキストが不十分な場合は入手できた情報の範囲でまとめてください。"
        )
        user_content = (
            text.strip()
            if text.strip()
            else f"銘柄コード {code} の会社概要テキストを取得できませんでした。"
            "入手可能な情報の範囲で概要をまとめてください。"
        )

        response = await client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content[:8000]},
            ],
            max_completion_tokens=16384,
            model=settings.AZ_OPENAI_DEPLOYMENT,
        )

        content = response.choices[0].message.content or ""
        bullets = [
            line.lstrip("・•-").strip()
            for line in content.splitlines()
            if line.strip()
            and (
                line.strip().startswith("・")
                or line.strip().startswith("•")
                or line.strip().startswith("-")
            )
        ]
        return bullets if bullets else [content.strip()]

    # HTML 取得・パース（一覧用）                                          #
    async def _fetch_and_parse(self, url: str, timeout: float) -> List[IpoItem]:
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
            company_name = self._extract_company_name(cols1[1])
            company_name = self._normalize_company_name(company_name)
            ticker = cols1[2].get_text(strip=True)
            offering_price_raw = cols1[6].get_text(strip=True)

            # 1行目のセルから PDF リンクを探す
            outline_pdf_url: Optional[str] = _find_pdf_in_cols(cols1)

            # 次の行は市場区分を含む
            market = ""
            if i + 1 < len(rows):
                row2 = rows[i + 1]
                cols2 = row2.find_all("td") if isinstance(row2, Tag) else []
                if cols2:
                    market = cols2[0].get_text(strip=True)
                    # 2行目でも PDF リンクを探す（1行目で見つからなかった場合）
                    if outline_pdf_url is None:
                        outline_pdf_url = _find_pdf_in_cols(cols2)
                i += 2
            else:
                i += 1

            # 必須データがないエントリーをスキップ
            if not company_name or not ticker:
                continue

            listing_date = self._parse_date(raw_date)
            offering_price = self._parse_price_text(offering_price_raw)

            items.append(
                IpoItem(
                    company_name=company_name,
                    ticker=ticker,
                    market=market,
                    listing_date=listing_date,
                    offering_price=offering_price,
                    outline_pdf_url=outline_pdf_url,
                    generated_at=datetime.utcnow(),
                )
            )

        return items

    # パース用ユーティリティ                                               #
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
    def _extract_company_name(cell: Tag) -> str:
        """会社名セルの先頭テキスト要素のみを会社名として抽出する"""
        for node in cell.descendants:
            if isinstance(node, NavigableString):
                text = str(node).strip()
                if text:
                    return text
        return ""

    @staticmethod
    def _normalize_company_name(name: str) -> str:
        """会社名表記を統一する"""
        normalized = name.strip()
        normalized = normalized.replace("（株）", "株式会社")
        normalized = normalized.replace("(株)", "株式会社")
        normalized = normalized.replace("㈱", "株式会社")
        return normalized


# モジュールレベルユーティリティ                                       #
def _resolve_url(base: str, href: str) -> str:
    """相対 URL を絶対 URL に変換する"""
    if href.startswith("http"):
        return href
    if href.startswith("/"):
        return base.rstrip("/") + href
    return base.rstrip("/") + "/" + href


def _find_pdf_in_cols(cols: List[Tag]) -> Optional[str]:
    """テーブルセルのリストから最初の PDF リンクを抽出して絶対 URL を返す"""
    for col in cols:
        a_tag = col.find("a", href=re.compile(r"\.pdf", re.IGNORECASE))
        if a_tag and isinstance(a_tag, Tag):
            href = str(a_tag.get("href", ""))
            if href:
                return _resolve_url(JPX_BASE_URL, href)
    return None
