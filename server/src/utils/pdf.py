import io
from typing import List

import httpx
import pdfplumber


async def extract_pdf_text_from_url(
    pdf_url: str, timeout: float, max_pages: int = 5
) -> str:
    """PDF をダウンロードして pdfplumber でテキスト抽出する（先頭 max_pages ページ）"""
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        resp = await client.get(pdf_url)
        resp.raise_for_status()

    buf = io.BytesIO(resp.content)
    texts: List[str] = []
    with pdfplumber.open(buf) as pdf:
        for page in pdf.pages[:max_pages]:
            page_text = page.extract_text() or ""
            texts.append(page_text)
    return "\n".join(texts)
