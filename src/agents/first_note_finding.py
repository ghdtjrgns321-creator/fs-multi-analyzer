"""Run first receivables Finding with D82242 note enrichment."""

from __future__ import annotations

import asyncio
import json

from src.agents.account_finding import run_account_finding


async def run_first_note_finding() -> dict[str, object]:
    return await run_account_finding("매출채권", 2025)


def main() -> None:
    result = asyncio.run(run_first_note_finding())
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
