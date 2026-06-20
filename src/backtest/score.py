"""Strict deterministic scoring for Stage1 backtests."""

from __future__ import annotations

import pandas as pd

from config.settings import settings
from src.normalize.config import load_canonical_accounts, normalize_label
from src.signals.config import load_l2_config
from src.signals.red_flags import RedFlagSignal
from src.signals.universal import account_above_floor

EXCLUDED_TYPES = {"cfs_ofs_gap"}
DETERMINISTIC_SCORE_STATEMENTS = {"BS", "IS"}
ACCOUNT_EQUIV = {
    "수익": "매출",
    "공사매출": "매출",
    "공사진행률": "매출",
    "개발비": "무형자산",
    "재고자산평가손실": "재고자산",
}


def score_case(
    label: dict[str, str],
    years: list[int],
    signals: list[RedFlagSignal],
    frame: pd.DataFrame,
    available_years: list[int] | None = None,
    legacy_signals: list[RedFlagSignal] | None = None,
) -> dict[str, object]:
    # ② 채점/랭킹(strict top10·track quota) 제거: 분식계정이 신호에 떴는지(발굴 recall)만 본다.
    # Phase2 LLM은 채점 결과를 권위로 소비하지 않으므로 순위·할당 채점을 두지 않는다.
    # legacy_signals 인자는 하위호환용 무시.
    fraud_accounts = _split_accounts(label.get("accounts", ""))
    mapped = [_map_account(account, frame) for account in fraud_accounts]
    fired = [_signal_row(signal) for signal in signals]
    scored = [row for row in fired if not row["excluded_from_scoring"]]
    ranked = _dedupe_by_account(scored)
    account_scores = [
        _account_score(item, ranked, frame, available_years or years) for item in mapped
    ]
    discovered = any(_is_discovered(score) for score in account_scores)
    miss_reason = None
    if not discovered:
        miss_reason = (
            "해당없음"
            if not fraud_accounts
            else _miss_reason(available_years or years, mapped, account_scores)
        )
    return {
        "corp_code": label["corp_code"],
        "company": label["company"],
        "label": label["label"],
        "window": years,
        "available_years": available_years or years,
        "fraud_accounts": fraud_accounts,
        "mapped": mapped,
        "fired_signals": fired,
        "false_positive_profile": ranked if label["label"] == "clean" else [],
        "account_scores": account_scores,
        "discovered": discovered,
        "miss_reason": miss_reason,
    }


def _dedupe_by_account(signals: list[dict[str, object]]) -> list[dict[str, object]]:
    best: dict[str, dict[str, object]] = {}
    for signal in sorted(
        signals,
        key=lambda row: row["normalized_strength"] or 0,
        reverse=True,
    ):
        key = normalize_label(str(signal["account"]))
        best.setdefault(key, signal)
    return list(best.values())


def false_positive_count(result: dict[str, object]) -> int:
    profile = result.get("false_positive_profile", [])
    return len(profile) if result["label"] == "clean" and isinstance(profile, list) else 0


def positive_discovery_rate(results: list[dict[str, object]]) -> tuple[int, int]:
    positives = [row for row in results if row["label"] == "positive"]
    return sum(1 for row in positives if row.get("discovered")), len(positives)


def _is_discovered(score: dict[str, object]) -> bool:
    return score.get("status") == "발굴"


def _split_accounts(value: str) -> list[str]:
    return [item.strip() for item in str(value or "").split(";") if item.strip()]


def _map_account(account: str, frame: pd.DataFrame) -> dict[str, object]:
    target = ACCOUNT_EQUIV.get(account, account)
    canonical, ids = _canonical_match(target)
    raw = _raw_matches(target, frame)
    status = "canonical" if canonical else "raw_label" if raw else "unmapped"
    return {
        "source": account,
        "canonical": canonical,
        "account_ids": ids,
        "raw_matches": raw,
        "status": status,
    }


def _canonical_match(account: str) -> tuple[str | None, list[str]]:
    normalized = normalize_label(account)
    lookup = _canonical_lookup()
    if normalized in lookup:
        return lookup[normalized]
    for key, value in lookup.items():
        if key and (key in normalized or normalized in key):
            return value
    return None, []


def _canonical_lookup() -> dict[str, tuple[str, list[str]]]:
    rows = {}
    for account in load_canonical_accounts(settings.config_dir / "canonical_accounts.yaml"):
        value = (account.name, list(account.account_ids))
        rows[normalize_label(account.name)] = value
        for alias in account.aliases:
            rows[normalize_label(alias)] = value
    return rows


def _raw_matches(account: str, frame: pd.DataFrame) -> list[str]:
    needle = normalize_label(account)
    matches = set()
    if frame.empty:
        return []
    for row in frame.itertuples():
        locator = f"{row.account_id}|{row.label}"
        if needle and needle in normalize_label(locator):
            matches.add(locator)
    return sorted(matches)[:5]


def _signal_row(signal: RedFlagSignal) -> dict[str, object]:
    threshold = _threshold_for(signal.signal_type)
    strength = _strength(signal.signal_type, signal.metric_value, threshold)
    excluded = signal.signal_type in EXCLUDED_TYPES or _excluded_statement(signal)
    return {
        "account": signal.account,
        "type": signal.signal_type,
        "value": signal.metric_value,
        "threshold": threshold,
        "normalized_strength": strength,
        "year": signal.year,
        "excluded_from_scoring": excluded,
        "sj_div": signal.sj_div,
        "track": signal.track,
        "magnitude_ratio": signal.magnitude_ratio,
        "current_amount": signal.current_amount,
    }


def _excluded_statement(signal: RedFlagSignal) -> bool:
    if signal.sj_div is None:
        return False
    return signal.sj_div not in DETERMINISTIC_SCORE_STATEMENTS


def _threshold_for(signal_type: str) -> object:
    thresholds = load_l2_config()["signal_thresholds"]
    return {
        "single_account_yoy": thresholds.get("yoy_pct_abs"),
        "universal_yoy": thresholds.get("yoy_pct_abs"),
        "growth_divergence": thresholds.get("divergence_pp_abs"),
        "universal_mix_shift": thresholds.get("mix_shift_pp_abs"),
        "universal_z_score": thresholds.get("z_score_abs"),
        "cfs_ofs_gap": thresholds.get("cfs_ofs_gap_pct_abs"),
        "direction_mismatch": "direction_rule",
    }.get(signal_type)


def _strength(signal_type: str, value: object, threshold: object) -> float | None:
    if threshold == "direction_rule":
        return 1.0
    if (
        not isinstance(value, int | float)
        or not isinstance(threshold, int | float)
        or threshold == 0
    ):
        return None
    strength = abs(float(value)) / float(threshold)
    if signal_type in _capped_strength_types():
        cap = float(load_l2_config()["signal_thresholds"].get("signal_strength_cap", 10))
        strength = min(strength, cap)
    return round(strength, 4)


def _capped_strength_types() -> set[str]:
    return {
        "single_account_yoy",
        "universal_yoy",
        "growth_divergence",
        "universal_mix_shift",
    }


def _account_score(
    mapped: dict[str, object],
    signals: list[dict[str, object]],
    frame: pd.DataFrame,
    years: list[int],
) -> dict[str, object]:
    candidates = _candidates(mapped)
    for rank, signal in enumerate(signals, start=1):
        haystack = normalize_label(str(signal["account"]))
        if any(normalize_label(item) and normalize_label(item) in haystack for item in candidates):
            # 순위·트랙 없이 '신호에 떴다=발굴'만 판정.
            return {
                "source": mapped["source"],
                "best_strength": signal["normalized_strength"],
                "rank": rank,
                "status": "발굴",
            }
    status = _pre_signal_status(mapped, frame, years)
    return {"source": mapped["source"], "best_strength": None, "rank": None, "status": status}


def _miss_reason(
    available_years: list[int],
    _mapped: list[dict[str, object]],
    account_scores: list[dict[str, object]],
) -> str:
    if len(available_years) < 2:
        return "데이터부족"
    priority = ["변동미미", "규모미달", "계정부재"]
    statuses = {str(score["status"]) for score in account_scores}
    return next((status for status in priority if status in statuses), "계정부재")


def _candidates(mapped: dict[str, object]) -> list[str]:
    values = [str(mapped.get("source") or ""), str(mapped.get("canonical") or "")]
    values.extend(str(item) for item in mapped.get("account_ids", []) or [])
    values.extend(str(item) for item in mapped.get("raw_matches", []) or [])
    return values


def _pre_signal_status(
    mapped: dict[str, object],
    frame: pd.DataFrame,
    years: list[int],
) -> str:
    if not _exists_in_frame(mapped, frame):
        return "계정부재"
    if any(
        account_above_floor(frame, item, year) for item in _candidates(mapped) for year in years
    ):
        return "변동미미"
    return "규모미달"


def _exists_in_frame(mapped: dict[str, object], frame: pd.DataFrame) -> bool:
    if frame.empty:
        return False
    haystack = " ".join(
        f"{row.canonical} {row.account_id} {row.label}" for row in frame.itertuples()
    )
    normalized = normalize_label(haystack)
    return any(
        normalize_label(item) and normalize_label(item) in normalized
        for item in _candidates(mapped)
    )
