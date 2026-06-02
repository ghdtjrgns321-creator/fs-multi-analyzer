"""Run first receivables Finding with D82242 note enrichment."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

from src.agents.first_finding import run_first_finding
from src.agents.note_analyst import create_note_enriched_finding
from src.notes.indexer import find_account_note_sections
from src.schemas.findings import AccountFinding


async def run_first_note_finding() -> dict[str, object]:
    numeric_result = await run_first_finding()
    finding = AccountFinding.model_validate(numeric_result["finding"])
    sections = find_account_note_sections(
        "매출채권",
        notes_root=Path("data/companies/00126380/2023/raw/notes"),
        corp_code="00126380",
        year=2023,
        fs_div="CFS",
    )
    enriched = await create_note_enriched_finding(finding, sections)
    return {
        "note_sections": [
            {
                "locator": section.locator,
                "title": section.title,
                "matched_keywords": section.matched_keywords,
                "snippet": section.text[:300],
            }
            for section in sections
        ],
        "finding": enriched.model_dump(mode="json"),
    }


def main() -> None:
    result = asyncio.run(run_first_note_finding())
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
