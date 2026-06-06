"""Two-track signal ranking by account magnitude."""

from __future__ import annotations

from typing import Any


def track_for_amount(
    amount: float | int | None,
    asset_total: float | int | None,
    thresholds: dict[str, Any],
) -> tuple[str | None, float | None]:
    """Classify a signal into magnitude track A/B without changing raw metrics."""

    if amount is None or asset_total in (None, 0):
        return None, None
    ratio = abs(float(amount)) / abs(float(asset_total))
    split = float(thresholds.get("track_split_pct_of_assets", 5.0)) / 100
    return ("A" if ratio >= split else "B"), ratio


def apply_track_quota(signals: list[Any], thresholds: dict[str, Any], score_fn: Any) -> list[Any]:
    """Return track A and B leaders while preserving each signal's track label."""

    quota_a = int(thresholds.get("track_a_quota", 6))
    quota_b = int(thresholds.get("track_b_quota", 6))
    track_a = [signal for signal in signals if getattr(signal, "track", None) == "A"]
    track_b = [signal for signal in signals if getattr(signal, "track", None) == "B"]
    other = [signal for signal in signals if getattr(signal, "track", None) not in {"A", "B"}]
    ranked_a = sorted(track_a, key=score_fn, reverse=True)[:quota_a]
    ranked_b = sorted(track_b, key=score_fn, reverse=True)[:quota_b]
    return [*ranked_a, *ranked_b, *sorted(other, key=score_fn, reverse=True)]
