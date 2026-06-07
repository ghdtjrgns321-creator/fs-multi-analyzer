"""L1.5 note indexer for account-linked OpenDART note HTML."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml
from bs4 import BeautifulSoup

DEFAULT_MAPPING = Path("config/playbooks/note_mappings.yaml")


@dataclass(frozen=True)
class NoteSection:
    corp_code: str
    year: int
    fs_div: str
    note_code: str
    note_name: str
    section_id: int
    title: str
    text: str
    matched_keywords: list[str] = field(default_factory=list)

    @property
    def locator(self) -> str:
        return f"note:{self.note_code}:{self.fs_div}:{self.year}:{self.section_id}"

    @property
    def current_year(self) -> str:
        return str(self.year)

    @property
    def prior_year(self) -> str:
        return str(self.year - 1)


def parse_note_html(
    html: str,
    corp_code: str,
    year: int,
    fs_div: str,
    note_code: str,
    note_name: str,
) -> list[NoteSection]:
    """Split OpenDART note HTML into coarse text sections."""

    lines = [
        line.strip()
        for line in BeautifulSoup(html, "html.parser").get_text("\n", strip=True).splitlines()
        if line.strip()
    ]
    sections: list[tuple[str, list[str]]] = []
    title = f"[{note_code}] {note_name}"
    body: list[str] = []
    for line in lines:
        if body and _looks_like_title(line):
            sections.append((title, body))
            title = line
            body = []
        else:
            body.append(line)
    if body:
        sections.append((title, body))

    return [
        NoteSection(
            corp_code=corp_code,
            year=year,
            fs_div=fs_div,
            note_code=note_code,
            note_name=note_name,
            section_id=index,
            title=section_title,
            text="\n".join(section_body),
        )
        for index, (section_title, section_body) in enumerate(sections)
    ]


def find_account_note_sections(
    account: str,
    notes_root: Path,
    corp_code: str,
    year: int,
    fs_div: str,
    mapping_path: Path = DEFAULT_MAPPING,
) -> list[NoteSection]:
    account_notes = yaml.safe_load(mapping_path.read_text(encoding="utf-8"))["account_notes"]
    # 주석 매핑이 없는 계정(무형자산 등)은 KeyError 대신 섹션 없음으로 degrade한다.
    if account not in account_notes:
        return []
    mapping = account_notes[account]
    path = notes_root / fs_div / f"{mapping['note_code']}.html"
    # 주석 미수집(finstate만 받은 회사 등)이면 해당 계정 섹션 없음으로 degrade한다.
    if not path.exists():
        return []
    sections = parse_note_html(
        path.read_text(encoding="utf-8"),
        corp_code=corp_code,
        year=year,
        fs_div=fs_div,
        note_code=mapping["note_code"],
        note_name=mapping["note_name"],
    )
    keywords = list(mapping.get("keywords", []))
    matched = []
    for section in sections:
        hits = [
            keyword for keyword in keywords if keyword in section.text or keyword in section.title
        ]
        if hits:
            matched.append(NoteSection(**{**section.__dict__, "matched_keywords": hits}))
    return matched or sections[:1]


def load_account_note_mappings(
    mapping_path: Path = DEFAULT_MAPPING,
) -> dict[str, dict[str, object]]:
    """Load account-to-note mappings from YAML."""

    payload = yaml.safe_load(mapping_path.read_text(encoding="utf-8")) or {}
    return dict(payload.get("account_notes", {}))


def _looks_like_title(line: str) -> bool:
    return line.startswith("[") or "[개요]" in line or "문장영역" in line
