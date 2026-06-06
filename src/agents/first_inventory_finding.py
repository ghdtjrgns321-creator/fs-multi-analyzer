"""Run first inventory Finding with D82638 note enrichment."""

from __future__ import annotations

import argparse
import asyncio
import json

from src.agents.account_finding import run_account_finding


async def run_first_inventory_finding(
    corp_code: str = "00126380",
    year: int = 2025,
) -> dict[str, object]:
    return await run_account_finding("재고자산", year, corp_code=corp_code)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--corp-code", default="00126380")
    parser.add_argument("--year", type=int, default=2025)
    args = parser.parse_args()
    result = asyncio.run(run_first_inventory_finding(args.corp_code, args.year))
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
