import io
import logging
import re
from datetime import date, datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple

import httpx
import httpx

from src.utils.jpx_parser import parse_jpx_ipo_html, find_pdf_url_for_code_in_html
from src.utils.pdf import extract_pdf_text_from_url
from src.utils.llm import summarize_ipo_with_llm

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

    # Public API
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
                    summary=cached_resp.summary,
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
                logger.warning(
                    "PDF extraction failed for %s (%s): %s", code, pdf_url, exc
                )

        # Azure OpenAI で要約
        summary = await summarize_ipo_with_llm(code, text)

        resp = IpoSummaryResponse(
            code=code,
            summary=summary,
            cached=False,
            generated_at=now,
        )
        _SUMMARY_CACHE[code] = (resp, now)
        return resp

    # PDF 取得・テキスト抽出
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

        return find_pdf_url_for_code_in_html(response.text, code)

    async def _extract_pdf_text(self, pdf_url: str, max_pages: int = 5) -> str:
        """PDF をダウンロードして pdfplumber でテキスト抽出する（先頭 max_pages ページ）"""
        timeout = float(settings.JPX_TIMEOUT) * 2
        return await extract_pdf_text_from_url(pdf_url, timeout, max_pages)

    # HTML 取得・パース（一覧用
    async def _fetch_and_parse(self, url: str, timeout: float) -> List[IpoItem]:
        """指定された *url* からHTMLを取得し、IPOテーブルをパース"""
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.get(url)
                response.raise_for_status()
        except httpx.TimeoutException as exc:
            raise ExternalAPIError("JPX", f"Timeout: {exc}") from exc
        except httpx.HTTPStatusError as exc:
            raise ExternalAPIError("JPX", f"HTTP {exc.response.status_code}") from exc
        except httpx.RequestError as exc:
            raise ExternalAPIError("JPX", str(exc)) from exc

        return parse_jpx_ipo_html(response.text)
