"""Run first 2023 numeric Finding from L2 red flags."""

from __future__ import annotations

import asyncio
import json

from src.agents.numeric_analyst import create_numeric_finding
from src.signals.finding_input import select_2023_numeric_signal, signals_to_prompt_payload
from src.signals.red_flags import extract_red_flags
from src.signals.spike import run_signal_spike


async def run_first_finding() -> dict[str, object]:
    """Build signals and request one grounded AccountFinding."""

    report = run_signal_spike()
    signals = select_2023_numeric_signal(extract_red_flags(report, 2023))
    payload = signals_to_prompt_payload(signals)
    finding = await create_numeric_finding(payload)
    return {"signals": payload["signals"], "finding": finding.model_dump(mode="json")}


def main() -> None:
    result = asyncio.run(run_first_finding())
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
