"""Run first 2023 numeric Finding from L2 red flags."""

from __future__ import annotations

import argparse
import asyncio
import json

from src.agents.numeric_analyst import create_numeric_finding
from src.signals.finding_input import select_account_signals, signals_to_prompt_payload
from src.signals.red_flags import extract_red_flags
from src.signals.spike import run_signal_spike


async def run_first_finding(
    corp_code: str = "00126380",
    year: int = 2023,
    account: str = "매출채권",
) -> dict[str, object]:
    """Build demo signals and request one grounded AccountFinding."""

    report = run_signal_spike(corp_code=corp_code)
    signals = select_account_signals(
        extract_red_flags(report, year),
        account=account,
        year=year,
        include_accounts={"영업활동현금흐름"},
        fallback_to_year=True,
    )
    payload = signals_to_prompt_payload(
        signals,
        scope=f"{corp_code} {year} deterministic numeric signals only",
    )
    finding = await create_numeric_finding(payload)
    return {"signals": payload["signals"], "finding": finding.model_dump(mode="json")}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--corp-code", default="00126380")
    parser.add_argument("--year", type=int, default=2023)
    parser.add_argument("--account", default="매출채권")
    args = parser.parse_args()
    result = asyncio.run(run_first_finding(args.corp_code, args.year, args.account))
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
