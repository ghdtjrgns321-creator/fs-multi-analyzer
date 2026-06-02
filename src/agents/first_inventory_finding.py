"""Run first inventory Finding with D82638 note enrichment."""

from __future__ import annotations

import asyncio
import json

from src.agents.account_finding import run_account_finding


async def run_first_inventory_finding() -> dict[str, object]:
    return await run_account_finding("재고자산", 2024)


def main() -> None:
    result = asyncio.run(run_first_inventory_finding())
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
