"""Build grounded inputs for the first numeric analyst Finding."""

from __future__ import annotations

from src.signals.red_flags import RedFlagSignal


def select_2023_numeric_signal(signals: list[RedFlagSignal]) -> list[RedFlagSignal]:
    """Keep 2023 signals centered on the revenue/receivables/operating-CF chain."""

    return select_account_signals(
        signals,
        account="매출채권",
        year=2023,
        include_accounts={"영업활동현금흐름"},
        fallback_to_year=True,
    )


def select_account_signals(
    signals: list[RedFlagSignal],
    account: str,
    year: int,
    include_accounts: set[str] | None = None,
    fallback_to_year: bool = False,
) -> list[RedFlagSignal]:
    """Keep signals for one account and optional chain-neighbor accounts."""

    accounts = {account, *(include_accounts or set())}
    preferred = [signal for signal in signals if signal.year == year and signal.account in accounts]
    if preferred or not fallback_to_year:
        return preferred
    return [signal for signal in signals if signal.year == year]


def signals_to_prompt_payload(
    signals: list[RedFlagSignal],
    scope: str = "deterministic numeric signals only",
) -> dict[str, object]:
    """Serialize only deterministic signal data for the LLM."""

    return {
        "scope": scope,
        "rules": [
            "외부 사실, 뉴스, 업황, 특정 사건을 단정하지 않는다.",
            "normal_explanation은 일반적 가능성으로만 표현한다.",
            "모든 수치 주장은 numeric_evidence 또는 flow_evidence 값만 사용한다.",
        ],
        "signals": [_serialize_signal(signal) for signal in signals],
    }


def _serialize_signal(signal: RedFlagSignal) -> dict[str, object]:
    return {
        "id": signal.id,
        "year": signal.year,
        "account": signal.account,
        "signal_type": signal.signal_type,
        "description": signal.description,
        "metric_value": signal.metric_value,
        "evidence": [item.model_dump(mode="json") for item in signal.evidence],
    }
