import re
from datetime import date, datetime
from typing import List, Optional

from bs4 import BeautifulSoup, NavigableString, Tag

from src.core.exceptions import DataParsingError
from src.schemas.ipo import IpoItem

JPX_BASE_URL = "https://www.jpx.co.jp"


def resolve_url(base: str, href: str) -> str:
    """相対 URL を絶対 URL に変換する"""
    if href.startswith("http"):
        return href
    if href.startswith("/"):
        return base.rstrip("/") + href
    return base.rstrip("/") + "/" + href


def find_pdf_in_cols(cols: List[Tag]) -> Optional[str]:
    """テーブルセルのリストから最初の PDF リンクを抽出して絶対 URL を返す"""
    for col in cols:
        a_tag = col.find("a", href=re.compile(r"\.pdf", re.IGNORECASE))
        if a_tag and isinstance(a_tag, Tag):
            href = str(a_tag.get("href", ""))
            if href:
                return resolve_url(JPX_BASE_URL, href)
    return None


def parse_date(raw: str) -> date:
    clean = re.sub(r"\(.*?\)", "", raw).strip()
    for fmt in (
        "%b. %d, %Y",
        "%b %d, %Y",
        "%Y/%m/%d",
        "%Y年%m月%d日",
    ):
        try:
            return datetime.strptime(clean, fmt).date()
        except ValueError:
            continue

    digits = re.findall(r"\d+", clean)
    if len(digits) >= 3:
        try:
            return date(int(digits[0]), int(digits[1]), int(digits[2]))
        except (ValueError, IndexError):
            pass

    return date.today()


def parse_price_text(text: str) -> Optional[float]:
    cleaned = text.replace(",", "").strip()
    digits = re.sub(r"[^\d.]", "", cleaned)
    if digits:
        try:
            return float(digits)
        except ValueError:
            pass
    return None


def extract_company_name(cell: Tag) -> str:
    for node in cell.descendants:
        if isinstance(node, NavigableString):
            text = str(node).strip()
            if text:
                return text
    return ""


def normalize_company_name(name: str) -> str:
    normalized = name.strip()
    normalized = normalized.replace("（株）", "株式会社")
    normalized = normalized.replace("(株)", "株式会社")
    normalized = normalized.replace("㈱", "株式会社")
    return normalized


def parse_jpx_ipo_html(html: str) -> List[IpoItem]:
    soup = BeautifulSoup(html, "lxml")

    table = soup.find("table", class_=re.compile(r"component.*table")) or soup.find(
        "table"
    )
    if table is None:
        raise DataParsingError("JPX", "No table element found on page.")

    tbody = table.find("tbody") if isinstance(table, Tag) else None
    rows = tbody.find_all("tr") if tbody else table.find_all("tr")

    items: List[IpoItem] = []
    i = 0

    while i < len(rows):
        row1 = rows[i]
        cols1 = row1.find_all("td") if isinstance(row1, Tag) else []

        if len(cols1) < 8:
            i += 1
            continue

        raw_date = cols1[0].get_text(strip=True)
        company_name = extract_company_name(cols1[1])
        company_name = normalize_company_name(company_name)
        ticker = cols1[2].get_text(strip=True)
        offering_price_raw = cols1[6].get_text(strip=True)

        outline_pdf_url: Optional[str] = find_pdf_in_cols(cols1)

        market = ""
        if i + 1 < len(rows):
            row2 = rows[i + 1]
            cols2 = row2.find_all("td") if isinstance(row2, Tag) else []
            if cols2:
                market = cols2[0].get_text(strip=True)
                if outline_pdf_url is None:
                    outline_pdf_url = find_pdf_in_cols(cols2)
            i += 2
        else:
            i += 1

        if not company_name or not ticker:
            continue

        listing_date = parse_date(raw_date)
        offering_price = parse_price_text(offering_price_raw)

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


def find_pdf_url_for_code_in_html(html: str, code: str) -> Optional[str]:
    soup = BeautifulSoup(html, "lxml")
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
                return resolve_url(JPX_BASE_URL, href)
    return None
