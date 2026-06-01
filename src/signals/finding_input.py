"""Build grounded inputs for the first numeric analyst Finding."""

from __future__ import annotations

from src.signals.red_flags import RedFlagSignal


def select_2023_numeric_signal(signals: list[RedFlagSignal]) -> list[RedFlagSignal]:
    """Keep 2023 signals centered on the revenue/receivables/operating-CF chain."""

    preferred = [
        signal
        for signal in signals
        if signal.year == 2023 and signal.account in {"매출채권", "영업활동현금흐름"}
    ]
    return preferred or [signal for signal in signals if signal.year == 2023]


def signals_to_prompt_payload(signals: list[RedFlagSignal]) -> dict[str, object]:
    """Serialize only deterministic signal data for the LLM."""

    return {
        "scope": "삼성전자 2023 CFS MVP1 numeric signals only",
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
