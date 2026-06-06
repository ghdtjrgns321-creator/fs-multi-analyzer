"""Run the L2 MVP1 deterministic signal spike."""

from __future__ import annotations

from src.analysis_tools import load_normalized_financials
from src.signals.mvp1 import build_mvp1_signal_report

DEFAULT_CORP_CODE = "00126380"
DEFAULT_YEARS = [2022, 2023, 2024, 2025]


def run_signal_spike(
    corp_code: str = DEFAULT_CORP_CODE,
    years: list[int] | None = None,
) -> dict[str, object]:
    """Load normalized data and build L2 signal tables."""

    target_years = years or DEFAULT_YEARS
    frame = load_normalized_financials(corp_code, target_years)
    return build_mvp1_signal_report(frame, years=target_years)


def main() -> None:
    report = run_signal_spike()
    for key in ("growth_divergences", "direction_checks", "primary_yoy", "reference_yoy"):
        print(f"\n{key.upper()}")
        print(report[key].to_string(index=False))
    print("\nDEFERRED_RATIOS")
    for item in report["deferred_ratios"]:
        print(f"- {item['name']}: {item['reason']}")


if __name__ == "__main__":
    main()
