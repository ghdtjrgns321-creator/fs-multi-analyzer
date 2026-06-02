"""Run first Finding and append a separate external ContextBrief."""

from __future__ import annotations

import asyncio
import json

from src.agents.context_brief import create_context_brief
from src.agents.first_finding import run_first_finding
from src.schemas.findings import AccountFinding


async def run_first_context_brief() -> dict[str, object]:
    result = await run_first_finding()
    finding = AccountFinding.model_validate(result["finding"])
    brief = await create_context_brief(finding, company_name="삼성전자", year=2023)
    return {
        "signals": result["signals"],
        "finding": finding.model_dump(mode="json"),
        "context_brief": brief.model_dump(mode="json"),
    }


def main() -> None:
    result = asyncio.run(run_first_context_brief())
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
