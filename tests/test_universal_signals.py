import pandas as pd

from src.signals.universal import preferred_fs_div, scan_cfs_ofs_gaps, scan_universal_signals


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
            "year": 2024,
            "fs_div": "CFS",
            "sj_div": "BS",
            "account_id": "ifrs-full_Assets",
            "label": "자산총계",
            "canonical": "자산총계",
            "amount": 10_000_000_000_000.0,
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


def test_universal_scan_groups_changed_account_id_by_canonical() -> None:
    data = pd.DataFrame(
        [
            {
                "year": 2024,
                "fs_div": "CFS",
                "sj_div": "IS",
                "account_id": "old_Revenue",
                "label": "수익",
                "canonical": "매출",
                "amount": 100_000_000.0,
            },
            {
                "year": 2025,
                "fs_div": "CFS",
                "sj_div": "IS",
                "account_id": "new_Revenue",
                "label": "매출액",
                "canonical": "매출",
                "amount": 1_000_000_000.0,
            },
            {
                "year": 2024,
                "fs_div": "CFS",
                "sj_div": "BS",
                "account_id": "ifrs-full_Assets",
                "label": "자산총계",
                "canonical": "자산총계",
                "amount": 10_000_000_000.0,
            },
            {
                "year": 2025,
                "fs_div": "CFS",
                "sj_div": "BS",
                "account_id": "ifrs-full_Assets",
                "label": "자산총계",
                "canonical": "자산총계",
                "amount": 10_000_000_000.0,
            },
        ]
    )

    signal = next(item for item in scan_universal_signals(data, 2025) if item.account == "매출")

    assert signal.signal_type == "universal_yoy"
    assert signal.metric_value == 900.0
    assert signal.evidence[0].locator == "new_Revenue|매출액"


def test_universal_scan_excludes_configured_bs_subtotals() -> None:
    data = pd.DataFrame(
        [
            {
                "year": 2024,
                "fs_div": "CFS",
                "sj_div": "BS",
                "account_id": "ifrs-full_CurrentAssets",
                "label": "유동자산",
                "canonical": "유동자산",
                "amount": 1_000_000_000_000.0,
            },
            {
                "year": 2025,
                "fs_div": "CFS",
                "sj_div": "BS",
                "account_id": "ifrs-full_CurrentAssets",
                "label": "유동자산",
                "canonical": "유동자산",
                "amount": 2_000_000_000_000.0,
            },
            {
                "year": 2024,
                "fs_div": "CFS",
                "sj_div": "BS",
                "account_id": "ifrs-full_Assets",
                "label": "자산총계",
                "canonical": "자산총계",
                "amount": 10_000_000_000_000.0,
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
        ]
    )

    assert scan_universal_signals(data, 2025) == []


def test_universal_scan_uses_ofs_when_cfs_series_is_incomplete() -> None:
    data = pd.DataFrame(
        [
            {
                "year": 2024,
                "fs_div": "OFS",
                "sj_div": "BS",
                "account_id": "custom_cash",
                "label": "현금",
                "canonical": "기타 중요 계정",
                "amount": 100_000_000.0,
            },
            {
                "year": 2024,
                "fs_div": "OFS",
                "sj_div": "BS",
                "account_id": "ifrs-full_Assets",
                "label": "자산총계",
                "canonical": "자산총계",
                "amount": 10_000_000_000.0,
            },
            {
                "year": 2025,
                "fs_div": "OFS",
                "sj_div": "BS",
                "account_id": "custom_cash",
                "label": "현금",
                "canonical": "기타 중요 계정",
                "amount": 1_000_000_000.0,
            },
            {
                "year": 2025,
                "fs_div": "CFS",
                "sj_div": "BS",
                "account_id": "custom_cash",
                "label": "현금",
                "canonical": "기타 중요 계정",
                "amount": 100_000_000.0,
            },
            {
                "year": 2025,
                "fs_div": "OFS",
                "sj_div": "BS",
                "account_id": "ifrs-full_Assets",
                "label": "자산총계",
                "canonical": "자산총계",
                "amount": 10_000_000_000.0,
            },
        ]
    )

    signals = scan_universal_signals(data, 2025)

    assert preferred_fs_div(data, 2025) == "OFS"
    assert any(item.account == "현금" and item.metric_value == 900.0 for item in signals)


def test_universal_scan_includes_four_statements_excludes_sce_with_floor_guards() -> None:
    rows = []
    for year in [2024, 2025]:
        rows.append(
            {
                "year": year,
                "fs_div": "CFS",
                "sj_div": "BS",
                "account_id": "ifrs-full_Assets",
                "label": "자산총계",
                "canonical": "자산총계",
                "amount": 1_000_000_000_000.0,
            }
        )
    for sj_div, account in [
        ("CF", "영업활동현금흐름"),
        ("CIS", "총포괄손익"),
        ("SCE", "이익잉여금변동"),
    ]:
        for year, amount in [(2024, 20_000_000_000.0), (2025, 40_000_000_000.0)]:
            rows.append(
                {
                    "year": year,
                    "fs_div": "CFS",
                    "sj_div": sj_div,
                    "account_id": f"{sj_div}_{account}",
                    "label": account,
                    "canonical": account,
                    "amount": amount,
                }
            )
    for year, amount in [(2024, 10_000_000.0), (2025, 40_000_000_000.0)]:
        rows.append(
            {
                "year": year,
                "fs_div": "CFS",
                "sj_div": "CF",
                "account_id": "cf_small_base",
                "label": "작은기저CF",
                "canonical": "기타 중요 계정",
                "amount": amount,
            }
        )
    data = pd.DataFrame(rows)

    signals = scan_universal_signals(data, 2025, include_all=True)
    flagged = {(item.account, item.signal_type) for item in signals}

    assert ("영업활동현금흐름", "universal_yoy") in flagged
    assert ("총포괄손익", "universal_yoy") in flagged
    # SCE(2D 격자)는 평면 스캔에서 제외 — 메인 프레임에서 구성요소 열이 소실돼 합계·member 셀이
    # 뭉개지므로 거짓신호를 낸다. 전용 sce_components 테이블이 전담(phase3).
    assert not any(item.account == "이익잉여금변동" for item in signals)
    assert not any(item.account == "작은기저CF" for item in signals)


def test_universal_scan_skips_mapped_accounts_repeated_in_other_statement_tables() -> None:
    rows = []
    for year in [2024, 2025]:
        rows.extend(
            [
                {
                    "year": year,
                    "fs_div": "CFS",
                    "sj_div": "BS",
                    "account_id": "ifrs-full_Assets",
                    "label": "자산총계",
                    "canonical": "자산총계",
                    "amount": 1_000_000_000_000.0,
                },
                {
                    "year": year,
                    "fs_div": "CFS",
                    "sj_div": "CIS",
                    "account_id": "ifrs-full_ProfitLoss",
                    "label": "당기순이익",
                    "canonical": "당기순이익",
                    "amount": 20_000_000_000.0 if year == 2024 else 40_000_000_000.0,
                },
                {
                    "year": year,
                    "fs_div": "CFS",
                    "sj_div": "CIS",
                    "account_id": "ifrs-full_ComprehensiveIncome",
                    "label": "총포괄손익",
                    "canonical": "총포괄손익",
                    "amount": 20_000_000_000.0 if year == 2024 else 40_000_000_000.0,
                },
            ]
        )
    data = pd.DataFrame(rows)

    accounts = {item.account for item in scan_universal_signals(data, 2025, include_all=True)}

    assert "총포괄손익" in accounts
    assert "당기순이익" not in accounts


def test_universal_yoy_skips_small_or_sign_changed_prior_base() -> None:
    data = pd.DataFrame(
        [
            {
                "year": 2024,
                "fs_div": "CFS",
                "sj_div": "IS",
                "account_id": "small_base",
                "label": "작은기저",
                "canonical": "기타 중요 계정",
                "amount": 10_000_000.0,
            },
            {
                "year": 2025,
                "fs_div": "CFS",
                "sj_div": "IS",
                "account_id": "small_base",
                "label": "작은기저",
                "canonical": "기타 중요 계정",
                "amount": 10_000_000_000.0,
            },
            {
                "year": 2024,
                "fs_div": "CFS",
                "sj_div": "IS",
                "account_id": "sign_flip",
                "label": "부호반전",
                "canonical": "기타 중요 계정",
                "amount": -1_000_000_000.0,
            },
            {
                "year": 2025,
                "fs_div": "CFS",
                "sj_div": "IS",
                "account_id": "sign_flip",
                "label": "부호반전",
                "canonical": "기타 중요 계정",
                "amount": 1_000_000_000.0,
            },
        ]
    )

    signals = scan_universal_signals(data, 2025)

    assert not any(item.account in {"작은기저", "부호반전"} for item in signals)


def test_universal_z_score_is_capped() -> None:
    rows = []
    for year, amount in zip(
        [2021, 2022, 2023, 2024, 2025],
        [100_000_000.0, 101_000_000.0, 99_000_000.0, 100_500_000.0, 1_000_000_000.0],
        strict=True,
    ):
        rows.append(
            {
                "year": year,
                "fs_div": "CFS",
                "sj_div": "BS",
                "account_id": "capped_z",
                "label": "캡대상",
                "canonical": "기타 중요 계정",
                "amount": amount,
            }
        )
    data = pd.DataFrame(rows)

    signal = next(
        item
        for item in scan_universal_signals(data, 2025)
        if item.signal_type == "universal_z_score"
    )

    assert signal.account == "캡대상"
    assert signal.metric_value == 10.0


def test_universal_scan_excludes_asset_sanity_bad_year() -> None:
    rows = []
    for year, asset, sales in [
        (2021, 1_000_000_000_000.0, 100_000_000_000.0),
        (2022, 1_000_000_000_000_000_000.0, 1_000_000_000_000_000.0),
        (2023, 1_100_000_000_000.0, 120_000_000_000.0),
    ]:
        rows.extend(
            [
                {
                    "year": year,
                    "fs_div": "CFS",
                    "sj_div": "BS",
                    "account_id": "ifrs-full_Assets",
                    "label": "자산총계",
                    "canonical": "자산총계",
                    "amount": asset,
                },
                {
                    "year": year,
                    "fs_div": "CFS",
                    "sj_div": "IS",
                    "account_id": "ifrs-full_Revenue",
                    "label": "매출",
                    "canonical": "매출",
                    "amount": sales,
                },
            ]
        )

    signals = scan_universal_signals(pd.DataFrame(rows), 2022)

    assert signals == []


def test_universal_scan_returns_all_material_signals_without_quota() -> None:
    # ② 채점/랭킹(track quota·top-N) 제거: 스캔은 material 신호를 전부 반환한다(선택·할당 없음).
    rows = []
    for year in [2024, 2025]:
        rows.append(
            {
                "year": year,
                "fs_div": "CFS",
                "sj_div": "BS",
                "account_id": "ifrs-full_Assets",
                "label": "자산총계",
                "canonical": "자산총계",
                "amount": 1_000_000_000_000.0,
            }
        )
    for idx in range(7):
        for year, amount in [(2024, 100_000_000_000.0), (2025, 200_000_000_000.0 + idx)]:
            rows.append(
                {
                    "year": year,
                    "fs_div": "CFS",
                    "sj_div": "IS",
                    "account_id": f"big_{idx}",
                    "label": f"규모계정{idx}",
                    "canonical": "기타 중요 계정",
                    "amount": amount,
                }
            )
    for idx in range(7):
        for year, amount in [(2024, 20_000_000_000.0), (2025, 40_000_000_000.0 + idx)]:
            rows.append(
                {
                    "year": year,
                    "fs_div": "CFS",
                    "sj_div": "IS",
                    "account_id": f"small_{idx}",
                    "label": f"소액계정{idx}",
                    "canonical": "기타 중요 계정",
                    "amount": amount,
                }
            )
    data = pd.DataFrame(rows)

    posted = scan_universal_signals(data, 2025)
    all_signals = scan_universal_signals(data, 2025, include_all=True)

    # quota/top-N 없이 material 신호 전부(=14) 반환. include_all 인자는 무시되어 동일.
    assert len(posted) == 14
    assert len(all_signals) == 14
    assert all(item.current_amount is not None for item in posted)
