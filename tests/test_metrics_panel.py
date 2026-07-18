"""계산값 전부 전달 패널 테스트 (phase 2).

원칙: 코드는 계정별 계산값을 하나도 안 고르고 전부 부착, 선택/랭킹/임계 없음.
LLM이 전 계정 계산값에서 직접 이상을 판단한다.
"""

from __future__ import annotations

from src.signals.metrics_panel import (
    DECISION_FIELDS,
    account_metrics_panel,
    occurrence_state,
)

ASSET = 111_411_700_508
CAPEX = {2021: 143_971_000, 2022: 93_950_699, 2023: 1_027_157_497, 2024: 2_849_071_648}
ASSOC = {2022: 5_203_864_137, 2023: 4_771_744_554, 2024: 4_281_246_884}  # 단조감소
CAPITAL = 18_696_175_000  # 4년 불변(정상)


def _row(key: str, sj: str, year: int, amt: float) -> dict:
    return {"series_key": key, "sj_div": sj, "year": year, "amount": amt}


def _rows() -> list[dict]:
    rows: list[dict] = []
    for y, a in CAPEX.items():
        rows.append(_row("유형자산취득", "CF", y, a))
    for y, a in ASSOC.items():
        rows.append(_row("관계기업투자", "BS", y, a))
    for key in ("자본금", "이익잉여금"):
        for y in (2021, 2022, 2023, 2024):
            rows.append(_row(key, "BS", y, CAPITAL))
    for y in (2021, 2022, 2023, 2024):
        rows.append(_row("자산총계", "BS", y, ASSET))
    return rows


def _by_account(panel: list[dict]) -> dict[str, dict]:
    return {p["account"]: p for p in panel}


def test_panel_covers_every_account_no_cap():
    rows = _rows()
    distinct = {r["series_key"] for r in rows}
    panel = account_metrics_panel(rows, ASSET, 2024)
    # 입력 계정 수 == 패널 계정 수 (누락 0·컷 0)
    assert {p["account"] for p in panel} == distinct
    assert len(panel) == len(distinct)


def test_every_entry_has_all_metrics():
    panel = account_metrics_panel(_rows(), ASSET, 2024)
    required = {
        "account",
        "sj_div",
        "amounts",
        "yoy_pct",
        "delta_over_assets",
        "trend",
        "volatility_cv",
        "mix_pct",
        "mix_shift_pp",
        "z_score",
        "percentiles",
    }
    for entry in panel:
        assert required.issubset(entry.keys())


def test_no_decision_fields_present():
    # flag/strength/tail/rank 등 "선택·랭킹" 필드가 없어야(발견=LLM)
    panel = account_metrics_panel(_rows(), ASSET, 2024)
    for entry in panel:
        for forbidden in DECISION_FIELDS:
            assert forbidden not in entry


def test_capex_yoy_computed():
    entry = _by_account(account_metrics_panel(_rows(), ASSET, 2024))["유형자산취득"]
    # 2024 YoY = (2849 - 1027)/1027 *100 ≈ +177%
    assert entry["yoy_pct"][2024] is not None
    assert 170 < entry["yoy_pct"][2024] < 185
    assert entry["delta_over_assets"] > 0


def test_assoc_monotonic_decrease_captured():
    entry = _by_account(account_metrics_panel(_rows(), ASSET, 2024))["관계기업투자"]
    assert entry["yoy_pct"][2024] < 0  # 감소
    assert entry["trend"] > 0  # 단조추세 점수 존재(방향 일관)


def test_flat_account_still_included():
    # 정상(불변) 계정도 임계로 안 거름 — 전부 포함
    panel = _by_account(account_metrics_panel(_rows(), ASSET, 2024))
    assert "자본금" in panel
    assert panel["자본금"]["delta_over_assets"] == 0.0


def test_mix_shift_sign_preserved():
    # 비중이 줄어든 계정은 mix_shift_pp < 0 (방향 정보 보존)
    rows = [
        _row("A", "IS", 2023, 100.0),
        _row("A", "IS", 2024, 100.0),  # A는 불변
        _row("B", "IS", 2023, 100.0),
        _row("B", "IS", 2024, 900.0),  # B 급증 → A의 비중은 감소
    ]
    panel = _by_account(account_metrics_panel(rows, 1000.0, 2024))
    assert panel["A"]["mix_shift_pp"] < 0  # A 비중 감소 = 음수
    assert panel["B"]["mix_shift_pp"] > 0  # B 비중 증가 = 양수


def test_cfs_ofs_same_account_not_merged_and_fs_div_denominators():
    """OFS 개방: CFS와 OFS에 같은 계정명(차입금)이 있어도 series_key 접두로 별개 series가 되고,
    구성비(mix) 분모·자산 분모가 fs_div별로 격리된다(이질병합 차단)."""
    rows = [
        {
            "series_key": "CFS:차입금",
            "sj_div": "BS",
            "fs_div": "CFS",
            "year": 2023,
            "amount": 100.0,
        },
        {
            "series_key": "CFS:차입금",
            "sj_div": "BS",
            "fs_div": "CFS",
            "year": 2024,
            "amount": 200.0,
        },
        {"series_key": "OFS:차입금", "sj_div": "BS", "fs_div": "OFS", "year": 2023, "amount": 10.0},
        {"series_key": "OFS:차입금", "sj_div": "BS", "fs_div": "OFS", "year": 2024, "amount": 80.0},
        {
            "series_key": "CFS:자산총계",
            "canonical": "자산총계",
            "sj_div": "BS",
            "fs_div": "CFS",
            "year": 2024,
            "amount": 1000.0,
        },
        {
            "series_key": "OFS:자산총계",
            "canonical": "자산총계",
            "sj_div": "BS",
            "fs_div": "OFS",
            "year": 2024,
            "amount": 100.0,
        },
    ]
    asset = {"CFS": 1000.0, "OFS": 100.0}
    panel = _by_account(account_metrics_panel(rows, asset, 2024))
    # 두 차입금이 합쳐지지 않고 별개 series
    assert "CFS:차입금" in panel and "OFS:차입금" in panel
    # OFS 차입금 delta는 OFS 자산(100)으로: |80-10|/100 = 0.7 (CFS 자산 1000 아님)
    assert abs(panel["OFS:차입금"]["delta_over_assets"] - 0.7) < 1e-9
    # CFS 차입금 delta: |200-100|/1000 = 0.1
    assert abs(panel["CFS:차입금"]["delta_over_assets"] - 0.1) < 1e-9
    # mix 분모도 fs_div 격리: OFS-BS 2024 합 = 80+100 = 180 (CFS 섞이면 5.8%로 떨어짐)
    assert abs(panel["OFS:차입금"]["mix_pct"] - 80 / 180 * 100) < 1e-3


def test_occurrence_state_four_cases():
    # 근본구조 B: 변화율 0/None이 죽이던 신규·소멸·재개를 신호로.
    assert occurrence_state({2023: 100.0, 2024: 120.0}, 2024) == "present"
    assert occurrence_state({2024: 100.0}, 2024) == "appeared"  # 과거 전무
    assert (
        occurrence_state({2022: 100.0, 2023: 0.0, 2024: 80.0}, 2024) == "resumed"
    )  # 직전 0, 과거 존재
    assert occurrence_state({2022: 100.0, 2023: 50.0}, 2024) == "disappeared"  # 당기 없음


def test_panel_entry_carries_occurrence_state():
    rows = [
        {
            "series_key": "CFS:사라짐",
            "sj_div": "BS",
            "fs_div": "CFS",
            "year": 2023,
            "amount": 500.0,
        },
        {"series_key": "CFS:정상", "sj_div": "BS", "fs_div": "CFS", "year": 2023, "amount": 100.0},
        {"series_key": "CFS:정상", "sj_div": "BS", "fs_div": "CFS", "year": 2024, "amount": 120.0},
    ]
    panel = _by_account(account_metrics_panel(rows, 1000.0, 2024))
    assert panel["CFS:사라짐"]["occurrence_state"] == "disappeared"
    assert panel["CFS:정상"]["occurrence_state"] == "present"


def test_empty_rows_returns_empty_panel():
    assert account_metrics_panel([], 0.0, 2024) == []


def test_zero_asset_delta_is_zero():
    rows = [_row("매출", "IS", 2023, 1_000_000), _row("매출", "IS", 2024, 2_000_000)]
    panel = account_metrics_panel(rows, 0.0, 2024)
    assert panel[0]["delta_over_assets"] == 0.0


# ── SCE 미매핑 정체성 복원(자본거래 병합 버그) ──────────────────────────────
def test_sce_change_identity_unmapped_uses_label():
    """미매핑 강등행은 canonical이 '기타 중요 계정' 상수 — 원문 라벨이 정체성이다."""

    from src.signals.metrics_panel import sce_change_identity

    unmapped = {
        "change_canonical": "기타 중요 계정",
        "change_label": "자기주식 매입",
        "change_status": "unmapped_extension_account",
    }
    mapped = {
        "change_canonical": "자기주식변동",
        "change_label": "자기주식매입",
        "change_status": "exact_taxonomy_match",
    }
    assert sce_change_identity(unmapped) == "자기주식 매입"
    assert sce_change_identity(mapped) == "자기주식변동"


def test_sce_occurrence_not_merged_across_unmapped_transactions():
    """서로 다른 미매핑 자본거래가 한 키로 병합되면 신규/소멸 신호가 뒤섞인다.

    작년 전환사채 상환 + 올해 자기주식 매입(둘 다 미매핑)일 때, 병합되면 '계속 있음'으로
    둔갑해 자기주식 appeared 신호가 죽는다 — 거래별로 갈라져야 한다."""

    from src.signals.metrics_panel import sce_occurrence_states

    window = [
        {
            "fs_div": "CFS",
            "year": 2023,
            "amount": 100.0,
            "change_canonical": "기타 중요 계정",
            "change_label": "전환사채의 조기상환",
            "change_status": "unmapped_extension_account",
        },
        {
            "fs_div": "CFS",
            "year": 2024,
            "amount": 582.0,
            "change_canonical": "기타 중요 계정",
            "change_label": "자기주식 매입",
            "change_status": "unmapped_extension_account",
        },
    ]
    states = sce_occurrence_states(window, 2024)
    assert states[("CFS", "자기주식 매입")] == "appeared"
    assert states[("CFS", "전환사채의 조기상환")] == "disappeared"
