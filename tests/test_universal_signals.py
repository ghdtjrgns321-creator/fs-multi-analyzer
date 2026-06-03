import pandas as pd

from src.signals.universal import scan_cfs_ofs_gaps, scan_universal_signals


def frame() -> pd.DataFrame:
    rows = [
        {
            "year": 2024,
            "fs_div": "CFS",
            "sj_div": "BS",
            "account_id": "custom_big",
            "label": "확장중요계정",
            "canonical": "기타 중요 계정",
            "amount": 1_000_000_000_000.0,
        },
        {
            "year": 2025,
            "fs_div": "CFS",
            "sj_div": "BS",
            "account_id": "custom_big",
            "label": "확장중요계정",
            "canonical": "기타 중요 계정",
            "amount": 2_000_000_000_000.0,
        },
        {
            "year": 2025,
            "fs_div": "CFS",
            "sj_div": "BS",
            "account_id": "ifrs-full_Assets",
            "label": "자산총계",
            "canonical": "자산총계",
            "amount": 10_000_000_000_000.0,
        },
        {
            "year": 2025,
            "fs_div": "OFS",
            "sj_div": "BS",
            "account_id": "ifrs-full_Assets",
            "label": "자산총계",
            "canonical": "자산총계",
            "amount": 4_000_000_000_000.0,
        },
    ]
    return pd.DataFrame(rows)


def test_universal_scan_flags_unmapped_account_yoy() -> None:
    signals = scan_universal_signals(frame(), 2025)

    signal = next(item for item in signals if item.signal_type == "universal_yoy")
    assert signal.account == "확장중요계정"
    assert signal.metric_value == 100.0
    assert signal.evidence[0].locator == "custom_big|확장중요계정"


def test_cfs_ofs_gap_flags_consolidation_difference() -> None:
    signals = scan_cfs_ofs_gaps(frame(), 2025)

    signal = next(item for item in signals if item.signal_type == "cfs_ofs_gap")
    assert signal.account == "자산총계"
    assert signal.metric_value == 60.0
