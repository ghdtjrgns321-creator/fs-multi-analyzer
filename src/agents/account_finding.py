"""Generic account Finding pipeline: L2 signals -> numeric analyst -> note analyst."""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
from typing import Any

from src.agents.note_analyst import create_note_enriched_finding
from src.agents.numeric_analyst import create_numeric_finding
from src.notes.indexer import find_account_note_sections
from src.signals.finding_input import select_account_signals, signals_to_prompt_payload
from src.signals.red_flags import extract_red_flags
from src.signals.spike import run_signal_spike


async def run_account_finding(
    account: str,
    year: int,
    corp_code: str = "00126380",
    fs_div: str = "CFS",
    notes_root: Path | None = None,
    numeric_agent_factory: Any = None,
    note_agent_factory: Any = None,
) -> dict[str, object]:
    report = run_signal_spike(corp_code=corp_code)
    signals = select_account_signals(extract_red_flags(report, year), account=account, year=year)
    payload = signals_to_prompt_payload(signals)
    if not signals:
        return {"signals": [], "note_sections": [], "finding": None}

    numeric_kwargs = {}
    if numeric_agent_factory is not None:
        numeric_kwargs["agent_factory"] = numeric_agent_factory
    finding = await create_numeric_finding(payload, **numeric_kwargs)

    root = notes_root or Path(f"data/companies/{corp_code}/{year}/raw/notes")
    sections = find_account_note_sections(account, root, corp_code, year, fs_div)
    note_kwargs = {}
    if note_agent_factory is not None:
        note_kwargs["agent_factory"] = note_agent_factory
    enriched = await create_note_enriched_finding(finding, sections, **note_kwargs)
    return {
        "signals": payload["signals"],
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
    parser = argparse.ArgumentParser()
    parser.add_argument("--account", required=True)
    parser.add_argument("--year", required=True, type=int)
    parser.add_argument("--corp-code", default="00126380")
    parser.add_argument("--fs-div", default="CFS")
    args = parser.parse_args()
    result = asyncio.run(
        run_account_finding(args.account, args.year, corp_code=args.corp_code, fs_div=args.fs_div)
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
