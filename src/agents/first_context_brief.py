"""Run first Finding and append a separate external ContextBrief."""

from __future__ import annotations

import argparse
import asyncio
import json

from src.agents.context_brief import create_context_brief
from src.agents.first_finding import run_first_finding
from src.schemas.findings import AccountFinding


async def run_first_context_brief(
    corp_code: str = "00126380",
    company_name: str | None = None,
    year: int = 2023,
    account: str = "매출채권",
) -> dict[str, object]:
    result = await run_first_finding(corp_code=corp_code, year=year, account=account)
    finding = AccountFinding.model_validate(result["finding"])
    brief = await create_context_brief(finding, company_name=company_name or corp_code, year=year)
    return {
        "signals": result["signals"],
        "finding": finding.model_dump(mode="json"),
        "context_brief": brief.model_dump(mode="json"),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--corp-code", default="00126380")
    parser.add_argument("--company-name")
    parser.add_argument("--year", type=int, default=2023)
    parser.add_argument("--account", default="매출채권")
    args = parser.parse_args()
    result = asyncio.run(
        run_first_context_brief(args.corp_code, args.company_name, args.year, args.account)
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
