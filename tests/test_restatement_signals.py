import pandas as pd

from src.report.materials import change_material
from src.signals.restatement import scan_restatement_signals


def test_restatement_scan_compares_reported_prior_to_original_prior_year_amount() -> None:
    frame = pd.DataFrame(
        [
            {
                "year": 2023,
                "fs_div": "CFS",
                "sj_div": "SCE",
                "canonical": "기타 중요 계정",
                "account_id": "ext_RetainedEarnings",
                "label": "이익잉여금변동",
                "amount": 20_000_000_000.0,
                "prior_amount": None,
                "mapping_status": "unmapped_extension_account",
            },
            {
                "year": 2024,
                "fs_div": "CFS",
                "sj_div": "SCE",
                "canonical": "기타 중요 계정",
                "account_id": "ext_RetainedEarnings",
                "label": "이익잉여금변동",
                "amount": 30_000_000_000.0,
                "prior_amount": 15_000_000_000.0,
                "mapping_status": "unmapped_extension_account",
            },
        ]
    )

    signals = scan_restatement_signals(frame, 2024)

    assert len(signals) == 1
    signal = signals[0]
    assert signal.signal_type == "restatement"
    assert signal.year == 2024
    assert signal.account == "이익잉여금변동"
    assert signal.metric_value == -5_000_000_000.0
    assert signal.evidence[0].year == "2024"
    assert "prior_amount 15,000,000,000" in str(signal.evidence[0].value)
    assert signal.evidence[1].year == "2023"
    assert "amount 20,000,000,000" in str(signal.evidence[1].value)


def test_restatement_scan_applies_absolute_and_relative_thresholds() -> None:
    frame = pd.DataFrame(
        [
            {
                "year": 2023,
                "fs_div": "CFS",
                "sj_div": "BS",
                "canonical": "재고자산",
                "account_id": "ifrs-full_Inventories",
                "label": "재고자산",
                "amount": 20_000_000_000.0,
                "prior_amount": None,
                "mapping_status": "exact_taxonomy_match",
            },
            {
                "year": 2024,
                "fs_div": "CFS",
                "sj_div": "BS",
                "canonical": "재고자산",
                "account_id": "ifrs-full_Inventories",
                "label": "재고자산",
                "amount": 30_000_000_000.0,
                "prior_amount": 19_900_000_000.0,
                "mapping_status": "exact_taxonomy_match",
            },
        ]
    )

    assert scan_restatement_signals(frame, 2024) == []


def test_restatement_scan_excludes_subtotal_accounts() -> None:
    frame = pd.DataFrame(
        [
            {
                "year": 2023,
                "fs_div": "CFS",
                "sj_div": "BS",
                "canonical": "자산총계",
                "account_id": "ifrs-full_Assets",
                "label": "자산총계",
                "amount": 500_000_000_000.0,
                "prior_amount": None,
            },
            {
                "year": 2024,
                "fs_div": "CFS",
                "sj_div": "BS",
                "canonical": "자산총계",
                "account_id": "ifrs-full_Assets",
                "label": "자산총계",
                "amount": 600_000_000_000.0,
                "prior_amount": 400_000_000_000.0,
            },
        ]
    )

    assert scan_restatement_signals(frame, 2024) == []


def test_restatement_scan_excludes_implausible_scale_or_unit_mismatch() -> None:
    frame = pd.DataFrame(
        [
            {
                "year": 2023,
                "fs_div": "CFS",
                "sj_div": "BS",
                "canonical": "매출채권",
                "account_id": "ifrs-full_TradeAndOtherCurrentReceivables",
                "label": "매출채권",
                "amount": 510_000_000_000.0,
                "prior_amount": None,
            },
            {
                "year": 2024,
                "fs_div": "CFS",
                "sj_div": "BS",
                "canonical": "매출채권",
                "account_id": "ifrs-full_TradeAndOtherCurrentReceivables",
                "label": "매출채권",
                "amount": 520_000_000_000.0,
                "prior_amount": 45_800_000_000_000.0,
            },
        ]
    )

    assert scan_restatement_signals(frame, 2024) == []


def test_restatement_scan_requires_asset_relative_floor_when_assets_are_available() -> None:
    frame = pd.DataFrame(
        [
            {
                "year": 2023,
                "fs_div": "CFS",
                "sj_div": "BS",
                "canonical": "자산총계",
                "account_id": "ifrs-full_Assets",
                "label": "자산총계",
                "amount": 10_000_000_000_000.0,
                "prior_amount": None,
            },
            {
                "year": 2024,
                "fs_div": "CFS",
                "sj_div": "BS",
                "canonical": "자산총계",
                "account_id": "ifrs-full_Assets",
                "label": "자산총계",
                "amount": 10_000_000_000_000.0,
                "prior_amount": 10_000_000_000_000.0,
            },
            {
                "year": 2023,
                "fs_div": "CFS",
                "sj_div": "BS",
                "canonical": "재고자산",
                "account_id": "ifrs-full_Inventories",
                "label": "재고자산",
                "amount": 20_000_000_000.0,
                "prior_amount": None,
            },
            {
                "year": 2024,
                "fs_div": "CFS",
                "sj_div": "BS",
                "canonical": "재고자산",
                "account_id": "ifrs-full_Inventories",
                "label": "재고자산",
                "amount": 25_000_000_000.0,
                "prior_amount": 19_000_000_000.0,
            },
        ]
    )

    assert scan_restatement_signals(frame, 2024) == []


def test_restatement_scan_dedupes_same_account_year_and_diff() -> None:
    frame = pd.DataFrame(
        [
            {
                "year": 2023,
                "fs_div": "CFS",
                "sj_div": "BS",
                "canonical": "재고자산",
                "account_id": "ifrs-full_Inventories",
                "label": "재고자산",
                "amount": 20_000_000_000.0,
                "prior_amount": None,
            },
            {
                "year": 2024,
                "fs_div": "CFS",
                "sj_div": "BS",
                "canonical": "재고자산",
                "account_id": "ifrs-full_Inventories",
                "label": "재고자산",
                "amount": 30_000_000_000.0,
                "prior_amount": 15_000_000_000.0,
            },
            {
                "year": 2023,
                "fs_div": "CFS",
                "sj_div": "BS",
                "canonical": "재고자산",
                "account_id": "ifrs-full_Inventories",
                "label": "재고자산",
                "amount": 20_000_000_000.0,
                "prior_amount": None,
            },
            {
                "year": 2024,
                "fs_div": "CFS",
                "sj_div": "BS",
                "canonical": "재고자산",
                "account_id": "ifrs-full_Inventories",
                "label": "재고자산",
                "amount": 30_000_000_000.0,
                "prior_amount": 15_000_000_000.0,
            },
        ]
    )

    assert len(scan_restatement_signals(frame, 2024)) == 1


def test_change_material_exposes_restatement_signals() -> None:
    material = change_material(
        {
            "review_queue": [],
            "latest_signal_snapshot": {
                "restatements": [
                    {
                        "account": "재고자산",
                        "signal_type": "restatement",
                        "metric_value": -68_400_000_000.0,
                    }
                ]
            },
            "account_level_series": [],
            "ratio_time_series": [],
            "target_year": 2024,
        }
    )

    assert material["restatement_signals"][0]["account"] == "재고자산"
