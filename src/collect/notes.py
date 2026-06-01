"""OpenDART note-view raw collection.

OpenDartReader does not wrap the financial statement note viewer endpoints. This module only
downloads raw public HTML/TXT from OpenDART pages for L0 observation.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://opendart.fss.or.kr"
NON_FINANCIAL_INDUSTRY = "XBR103"
TOCS = {"CFS": "0", "OFS": "5"}


@dataclass(frozen=True)
class NoteCategory:
    """OpenDART note category metadata."""

    code: str
    name: str
    description: str


class NoteCollector:
    """Collect raw note category list and detail pages."""

    def __init__(self) -> None:
        self._session = requests.Session()

    def categories(self, industry_code: str = NON_FINANCIAL_INDUSTRY) -> list[NoteCategory]:
        response = self._session.post(
            f"{BASE_URL}/disclosureinfo/fnltt/singlnote/searchAccountGubun.do",
            data={"indCd": industry_code},
            timeout=20,
        )
        response.raise_for_status()
        items = response.json().get("finStmtCmtList", [])
        return [
            NoteCategory(
                code=str(item.get("code", "")),
                name=str(item.get("codeNm", "")),
                description=str(item.get("codeDc", "")),
            )
            for item in items
            if item.get("code")
        ]

    def detail_html(self, corp_code: str, year: int, toc: str, category_code: str) -> str:
        response = self._session.get(
            f"{BASE_URL}/disclosureinfo/fnltt/singlnote/listDetail.do",
            params={
                "cik": corp_code,
                "stlmYr": str(year),
                "stlmTp": "11011",
                "selectToc": toc,
                "accountGubun": category_code,
            },
            timeout=30,
        )
        response.raise_for_status()
        return response.text


def write_note_detail(html: str, path: Path) -> dict[str, int]:
    """Persist raw note HTML and extracted text for observation."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.with_suffix(".html").write_text(html, encoding="utf-8")
    text = BeautifulSoup(html, "html.parser").get_text("\n", strip=True)
    path.with_suffix(".txt").write_text(text, encoding="utf-8")
    return {
        "html_bytes": len(html.encode("utf-8")),
        "text_chars": len(text),
        "table_count": html.count("<table"),
    }
