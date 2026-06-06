from pathlib import Path

import pandas as pd

from src.analysis_tools import compare_growth, compute_ratio
from src.backtest.score import _signal_row, positive_discovery_rate, score_case
from src.normalize.config import load_canonical_accounts
from src.normalize.mapper import AccountMapper
from src.normalize.pipeline import normalize_raw_file
from src.schemas.findings import EvidenceRef
from src.signals.mvp1 import build_mvp1_signal_report
from src.signals.red_flags import RedFlagSignal, extract_red_flags
from src.signals.spike import run_signal_spike


def fixture_frame() -> pd.DataFrame:
    rows = []
    values = {
        "매출": [100_000_000_000.0, 150_000_000_000.0, 120_000_000_000.0],
        "매출채권": [50_000_000_000.0, 55_000_000_000.0, 66_000_000_000.0],
        "재고자산": [20_000_000_000.0, 30_000_000_000.0, 60_000_000_000.0],
        "매출원가": [80_000_000_000.0, 100_000_000_000.0, 110_000_000_000.0],
        "영업활동현금흐름": [10_000_000_000.0, 8_000_000_000.0, 12_000_000_000.0],
    }
    for account, amounts in values.items():
        for year, amount in zip([2022, 2023, 2024], amounts, strict=True):
            rows.append({"year": year, "fs_div": "CFS", "canonical": account, "amount": amount})
    return pd.DataFrame(rows)


def test_compare_growth_returns_golden_divergence() -> None:
    result = compare_growth(fixture_frame(), "매출", "매출채권", [2022, 2023, 2024])

    assert result["growth_a_pct"].tolist() == [50.0, -20.0]
    assert result["growth_b_pct"].tolist() == [10.0, 20.0]
    assert result["divergence_pp"].tolist() == [40.0, -40.0]


def test_compute_ratio_handles_zero_denominator() -> None:
    frame = fixture_frame()
    frame.loc[len(frame)] = {"year": 2024, "fs_div": "CFS", "canonical": "분모", "amount": 0.0}

    result = compute_ratio(frame, "매출", "분모", [2024])

    assert result.iloc[0]["ratio_pct"] is None


def test_receivable_combo_labels_map_to_receivable_proxy() -> None:
    mapper = AccountMapper(load_canonical_accounts(Path("config/canonical_accounts.yaml")))

    mapped = [
        mapper.map_row(pd.Series({"account_id": "", "account_nm": label})).canonical
        for label in [
            "매출채권 및 기타유동채권",
            "매출채권 및 기타채권",
            "매출채권및기타채권",
        ]
    ]
    long_term = mapper.map_row(
        pd.Series({"account_id": "", "account_nm": "장기매출채권 및 기타비유동채권"})
    )

    assert mapped == ["매출채권", "매출채권", "매출채권"]
    assert long_term.canonical != "매출채권"


def test_payable_combo_labels_map_to_payable_proxy() -> None:
    mapper = AccountMapper(load_canonical_accounts(Path("config/canonical_accounts.yaml")))

    mapped = [
        mapper.map_row(pd.Series({"account_id": "", "account_nm": label})).canonical
        for label in [
            "매입채무 및 기타유동채무",
            "매입채무및기타채무",
            "매입채무 및 기타채무",
        ]
    ]
    long_term = mapper.map_row(
        pd.Series({"account_id": "", "account_nm": "장기매입채무 및 기타비유동채무"})
    )

    assert mapped == ["매입채무", "매입채무", "매입채무"]
    assert long_term.canonical != "매입채무"


def test_profit_loss_suffix_labels_map_to_profit_loss() -> None:
    mapper = AccountMapper(load_canonical_accounts(Path("config/canonical_accounts.yaml")))

    mapped = [
        mapper.map_row(pd.Series({"account_id": "", "account_nm": label})).canonical
        for label in ["당기순이익(손실)", "당기순이익(이익)", "당기순이익(손익)"]
    ]

    assert mapped == ["당기순이익", "당기순이익", "당기순이익"]


def test_revenue_aliases_are_total_revenue_only() -> None:
    mapper = AccountMapper(load_canonical_accounts(Path("config/canonical_accounts.yaml")))

    mapped = [
        mapper.map_row(pd.Series({"account_id": "", "account_nm": label})).canonical
        for label in [
            "영업수익",
            "수익(매출액)",
            "재화의 판매로 인한 수익(매출액)",
            "방송수익",
        ]
    ]
    component = mapper.map_row(pd.Series({"account_id": "", "account_nm": "제품매출"}))

    assert mapped == ["매출", "매출", "매출", "매출"]
    assert component.canonical != "매출"


def test_contract_progress_accounts_map_to_canonical() -> None:
    mapper = AccountMapper(load_canonical_accounts(Path("config/canonical_accounts.yaml")))

    assets = [
        mapper.map_row(pd.Series({"account_id": "", "account_nm": label})).canonical
        for label in ["계약자산", "미청구공사", "단기미청구공사", "미청구공사채권", "확정계약자산"]
    ]
    liabilities = [
        mapper.map_row(pd.Series({"account_id": "", "account_nm": label})).canonical
        for label in ["계약부채", "초과청구공사", "단기초과청구공사", "확정계약부채"]
    ]
    provision = mapper.map_row(pd.Series({"account_id": "", "account_nm": "공사손실충당부채"}))

    assert assets == ["계약자산"] * 5
    assert liabilities == ["계약부채"] * 4
    assert provision.canonical == "공사손실충당부채"


def test_signal_report_uses_configured_accounts(tmp_path) -> None:
    config = tmp_path / "chains.yaml"
    config.write_text(
        """
l2_mvp1:
  primary_fs_div: CFS
  reference_fs_div: CFS
  years: [2022, 2023, 2024]
  yoy_accounts: [매출, 매출채권]
  growth_divergences:
    - id: revenue-vs-receivable
      name: 매출 vs 매출채권
      account_a: 매출
      account_b: 매출채권
  direction_checks:
    - id: receivable-vs-cf
      name: 매출채권 vs 영업활동현금흐름
      growth_account: 매출채권
      flow_account: 영업활동현금흐름
  deferred_ratios: []
""",
        encoding="utf-8",
    )

    report = build_mvp1_signal_report(fixture_frame(), config)

    assert report["growth_divergences"]["divergence_pp"].tolist() == [40.0, -40.0]
    assert report["direction_checks"]["direction_same"].tolist() == [False, True]
    assert len(report["primary_yoy"]) == 4


def test_signal_report_can_compare_revenue_and_contract_asset(tmp_path) -> None:
    config = tmp_path / "chains.yaml"
    config.write_text(
        """
l2_mvp1:
  primary_fs_div: CFS
  reference_fs_div: CFS
  years: [2023, 2024, 2025]
  yoy_accounts: [매출, 계약자산]
  growth_divergences:
    - id: revenue-vs-contract-asset
      name: 매출 vs 계약자산 증가율 괴리
      account_a: 매출
      account_b: 계약자산
  direction_checks: []
  deferred_ratios: []
  signal_thresholds:
    universal_min_pct_of_assets: 1.0
    universal_min_abs_amount: 100000000
""",
        encoding="utf-8",
    )
    data = pd.DataFrame(
        [
            {
                "year": year,
                "fs_div": "CFS",
                "sj_div": sj_div,
                "canonical": account,
                "amount": amount,
            }
            for year, sales, contract_asset in [
                (2023, 100_000_000_000.0, 10_000_000_000.0),
                (2024, 110_000_000_000.0, 30_000_000_000.0),
                (2025, 121_000_000_000.0, 60_000_000_000.0),
            ]
            for account, sj_div, amount in [
                ("자산총계", "BS", 1_000_000_000_000.0),
                ("매출", "IS", sales),
                ("계약자산", "BS", contract_asset),
            ]
        ]
    )

    report = build_mvp1_signal_report(data, config)

    row = report["growth_divergences"][
        report["growth_divergences"]["year"] == 2025
    ].set_index("id").loc["revenue-vs-contract-asset"]
    assert row["divergence_pp"] == -90.0


def test_signal_report_derives_years_from_frame_not_config(tmp_path) -> None:
    config = tmp_path / "chains.yaml"
    config.write_text(
        """
l2_mvp1:
  primary_fs_div: CFS
  reference_fs_div: CFS
  years: [2022, 2023, 2024, 2025]
  yoy_accounts: [매출, 매출채권]
  growth_divergences:
    - id: revenue-vs-receivable
      name: 매출 vs 매출채권
      account_a: 매출
      account_b: 매출채권
  direction_checks: []
  deferred_ratios: []
""",
        encoding="utf-8",
    )
    shifted = fixture_frame().copy()
    shifted["year"] = shifted["year"] - 6

    report = build_mvp1_signal_report(shifted, config)

    assert report["growth_divergences"]["year"].tolist() == [2017, 2018]
    assert report["growth_divergences"]["divergence_pp"].tolist() == [40.0, -40.0]


def guarded_config(tmp_path) -> object:
    config = tmp_path / "chains.yaml"
    config.write_text(
        """
l2_mvp1:
  primary_fs_div: CFS
  reference_fs_div: CFS
  years: [2024, 2025]
  yoy_accounts: [영업활동현금흐름, 재고자산, 기타수익]
  growth_divergences:
    - id: cogs-vs-inventory
      name: 매출원가 vs 재고자산
      account_a: 매출원가
      account_b: 재고자산
    - id: debt-vs-inventory
      name: 장기차입금 vs 재고자산
      account_a: 장기차입금
      account_b: 재고자산
  direction_checks: []
  deferred_ratios: []
  signal_thresholds:
    divergence_pp_abs: 15
    yoy_pct_abs: 50
    direction_red_flags: []
    universal_min_pct_of_assets: 1.0
    universal_min_abs_amount: 100000000
""",
        encoding="utf-8",
    )
    return config


def guarded_frame() -> pd.DataFrame:
    rows = []
    values = {
        "자산총계": ("BS", [1_000_000_000_000.0, 1_000_000_000_000.0]),
        "영업활동현금흐름": ("CF", [10_000_000_000.0, 100_000_000_000.0]),
        "재고자산": ("BS", [100_000_000_000.0, 150_000_000_000.0]),
        "기타수익": ("CIS", [5_600_000_000.0, 300_000_000_000.0]),
        "매출원가": ("IS", [100_000_000_000.0, 105_000_000_000.0]),
        "장기차입금": ("BS", [1_000_000.0, 100_000_000_000.0]),
    }
    for account, (sj_div, amounts) in values.items():
        for year, amount in zip([2024, 2025], amounts, strict=True):
            rows.append(
                {
                    "year": year,
                    "fs_div": "CFS",
                    "sj_div": sj_div,
                    "canonical": account,
                    "amount": amount,
                }
            )
    return pd.DataFrame(rows)


def test_mvp1_single_yoy_red_flags_exclude_cf_accounts(tmp_path) -> None:
    report = build_mvp1_signal_report(guarded_frame(), guarded_config(tmp_path))

    signals = extract_red_flags(report, 2025)

    assert any(row.canonical == "영업활동현금흐름" for row in report["primary_yoy"].itertuples())
    assert not any(signal.account == "영업활동현금흐름" for signal in signals)


def test_mvp1_single_yoy_uses_current_year_floor_for_base(tmp_path) -> None:
    report = build_mvp1_signal_report(guarded_frame(), guarded_config(tmp_path))

    signals = extract_red_flags(report, 2025)
    row = report["primary_yoy"].set_index("canonical").loc["기타수익"]

    assert bool(row["valid_yoy_base"]) is False
    assert not any(signal.account == "기타수익" for signal in signals)


def test_mvp1_single_yoy_red_flags_exclude_configured_subtotals(tmp_path) -> None:
    config = tmp_path / "chains.yaml"
    config.write_text(
        """
l2_mvp1:
  primary_fs_div: CFS
  reference_fs_div: CFS
  years: [2024, 2025]
  yoy_accounts: [유동자산, 당기순이익]
  growth_divergences: []
  direction_checks: []
  deferred_ratios: []
  signal_thresholds:
    divergence_pp_abs: 15
    yoy_pct_abs: 50
    direction_red_flags: []
    universal_min_pct_of_assets: 1.0
    universal_min_abs_amount: 100000000
""",
        encoding="utf-8",
    )
    data = pd.DataFrame(
        [
            {
                "year": year,
                "fs_div": "CFS",
                "sj_div": sj_div,
                "canonical": account,
                "amount": amount,
            }
            for year, subtotal, profit in [
                (2024, 100_000_000_000.0, 100_000_000_000.0),
                (2025, 200_000_000_000.0, 200_000_000_000.0),
            ]
            for account, sj_div, amount in [
                ("자산총계", "BS", 1_000_000_000_000.0),
                ("유동자산", "BS", subtotal),
                ("당기순이익", "IS", profit),
            ]
        ]
    )

    signals = extract_red_flags(build_mvp1_signal_report(data, config), 2025)

    assert not any(signal.account == "유동자산" for signal in signals)
    assert any(signal.account == "당기순이익" for signal in signals)


def test_mvp1_growth_divergence_requires_both_material_bases(tmp_path) -> None:
    report = build_mvp1_signal_report(guarded_frame(), guarded_config(tmp_path))

    rows = report["growth_divergences"].set_index("id")

    assert rows.loc["cogs-vs-inventory", "divergence_pp"] == -45.0
    assert pd.isna(rows.loc["debt-vs-inventory", "divergence_pp"])


def test_percent_signal_strength_is_capped() -> None:
    signal = RedFlagSignal(
        id="divergence:test:2025",
        year=2025,
        account="당기순이익",
        signal_type="growth_divergence",
        description="test",
        metric_value=-1854.67,
        evidence=[EvidenceRef(source="financial_statement", locator="x", year="2025")],
    )

    assert _signal_row(signal)["normalized_strength"] == 10.0


def test_discovery_rate_counts_accounts_outside_top10() -> None:
    results = [
        {"label": "positive", "discovered": True, "hit": False},
        {"label": "positive", "discovered": False, "hit": False},
        {"label": "clean", "discovered": False, "hit": False},
    ]

    assert positive_discovery_rate(results) == (1, 2)


def test_score_case_reports_legacy_and_track_hits_separately() -> None:
    frame = pd.DataFrame(
        [
            {
                "year": 2025,
                "fs_div": "CFS",
                "sj_div": "BS",
                "canonical": "재고자산",
                "account_id": "ifrs-full_Inventories",
                "label": "재고자산",
                "amount": 100_000_000_000.0,
            }
        ]
    )
    signals = [
        RedFlagSignal(
            id=f"small:{idx}",
            year=2025,
            account=f"소액계정{idx}",
            signal_type="universal_yoy",
            description="small",
            metric_value=1_000.0,
            evidence=[EvidenceRef(source="financial_statement", locator="x", year="2025")],
            track="B",
            magnitude_ratio=0.02,
            current_amount=20_000_000_000.0,
        )
        for idx in range(10)
    ]
    signals.append(
        RedFlagSignal(
            id="big:inventory",
            year=2025,
            account="재고자산",
            signal_type="universal_yoy",
            description="inventory",
            metric_value=100.0,
            evidence=[EvidenceRef(source="financial_statement", locator="x", year="2025")],
            track="A",
            magnitude_ratio=0.10,
            current_amount=100_000_000_000.0,
        )
    )

    result = score_case(
        {
            "corp_code": "00000000",
            "company": "테스트",
            "label": "positive",
            "accounts": "재고자산",
        },
        [2025],
        signals,
        frame,
        [2025],
    )

    assert result["hit"] is False
    assert result["track_hit"] is True
    assert result["account_scores"][0]["status"] == "상위10밖"
    assert result["track_account_scores"][0]["status"] == "포착"


def test_financial_liability_label_does_not_map_to_subtotal() -> None:
    frame = pd.DataFrame(
        [
            {
                "year": 2025,
                "fs_div": "CFS",
                "sj_div": "BS",
                "canonical": "부채총계",
                "account_id": "ifrs-full_Liabilities",
                "label": "부채총계",
                "amount": 100_000_000_000.0,
                "mapping_status": "exact_taxonomy_match",
            }
        ]
    )

    result = score_case(
        {
            "corp_code": "00000000",
            "company": "테스트",
            "label": "positive",
            "accounts": "금융부채",
        },
        [2025],
        [],
        frame,
        [2025],
    )

    assert result["mapped"][0]["canonical"] is None
    assert result["account_scores"][0]["status"] == "계정부재"


def test_normalize_raw_file_dedupes_same_statement_key(tmp_path) -> None:
    raw = tmp_path / "finstate_all_CFS.csv"
    raw.write_text(
        "\n".join(
            [
                "corp_code,bsns_year,sj_div,account_id,account_nm,account_detail,thstrm_amount",
                "00000000,2025,BS,custom_Asset,기타자산,세부 [member],100",
                "00000000,2025,BS,custom_Asset,기타자산,연결재무제표 [member],200",
                "00000000,2025,BS,custom_Asset,기타자산,연결재무제표 [member],200",
            ]
        ),
        encoding="utf-8",
    )
    (tmp_path / "empty.yaml").write_text("canonical_accounts: {}\n", encoding="utf-8")
    mapper = AccountMapper(load_canonical_accounts(tmp_path / "empty.yaml"))

    frame = normalize_raw_file(raw, "CFS", mapper)

    assert len(frame) == 1
    assert frame.iloc[0]["amount"] == 200.0


def test_normalize_raw_file_keeps_one_canonical_representative(tmp_path) -> None:
    raw = tmp_path / "finstate_all_CFS.csv"
    raw.write_text(
        "\n".join(
            [
                "corp_code,bsns_year,sj_div,account_id,account_nm,account_detail,thstrm_amount",
                "00000000,2025,BS,custom_total,계약자산,연결재무제표,300",
                "00000000,2025,BS,custom_current,유동확정계약자산,연결재무제표,200",
                "00000000,2025,BS,custom_noncurrent,비유동확정계약자산,연결재무제표,100",
            ]
        ),
        encoding="utf-8",
    )
    mapper = AccountMapper(load_canonical_accounts(Path("config/canonical_accounts.yaml")))

    frame = normalize_raw_file(raw, "CFS", mapper)

    rows = frame[frame["canonical"] == "계약자산"]
    assert len(rows) == 1
    assert rows.iloc[0]["label"] == "계약자산"
    assert rows.iloc[0]["amount"] == 300.0


def test_red_flags_tolerate_empty_mvp1_tables() -> None:
    report = build_mvp1_signal_report(pd.DataFrame(), years=[2023])

    assert report["growth_divergences"].columns.tolist() == [
        "year",
        "account_a",
        "account_b",
        "current_amount_a",
        "current_amount_b",
        "growth_a_pct",
        "growth_b_pct",
        "divergence_pp",
        "id",
        "name",
    ]
    assert report["primary_yoy"].columns.tolist() == [
        "fs_div",
        "sj_div",
        "canonical",
        "year",
        "amount",
        "prior_amount",
        "valid_yoy_base",
        "yoy_growth_pct",
    ]
    assert extract_red_flags(report, 2023) == []


def test_single_year_company_signal_spike_does_not_crash() -> None:
    report = run_signal_spike("00688996", [2023])

    assert extract_red_flags(report, 2023) == []
