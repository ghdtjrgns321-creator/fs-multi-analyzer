"""Material board helpers for independent L4 perspectives."""

from __future__ import annotations

from pathlib import Path

from src.notes.indexer import find_account_note_sections


def numeric_material(report: dict[str, object]) -> dict[str, object]:
    """Inputs for numeric perspective only."""

    return {
        "review_queue": report["review_queue"][:10],
        "ratio_summary": report["ratio_summary"],
        "scope": "numeric perspective only",
    }


def note_material(
    corp_code: str = "00126380",
    year: int = 2024,
    fs_div: str = "CFS",
) -> dict[str, object]:
    """Inputs for note perspective only."""

    notes_root = Path("data/companies") / corp_code / str(year) / "raw" / "notes"
    sections = []
    for account in ("매출채권", "재고자산"):
        for section in find_account_note_sections(account, notes_root, corp_code, year, fs_div):
            sections.append(
                {
                    "account": account,
                    "locator": section.locator,
                    "title": section.title,
                    "matched_keywords": section.matched_keywords,
                    "excerpt": section.text[:700],
                }
            )
    return {"note_sections": sections, "scope": "note perspective only"}
