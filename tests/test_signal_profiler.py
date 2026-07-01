"""S1 다축 프로파일러 self축 계산기 테스트 (PHASE1_SIGNAL_REDESIGN §3·§9).

capex(변화금액축)·관계기업(추세축)이 정상계정보다 높은 점수를 받는지 실 시계열로 단언.
순수함수 — DB·LLM 없음.
"""

from __future__ import annotations

import math

import pytest

from src.signals.profiler import (
    build_account_profile,
    compute_self_axes,
    compute_strength,
    delta_score,
    mix_score,
    normalize_axes,
    trend_score,
    volatility_score,
)

ASSET = 111_411_700_508  # 대주산업 2024 자산총계(원)

# 실 시계열(원) — 회귀 검증 oracle
CAPEX = {2021: 143_971_000, 2022: 93_950_699, 2023: 1_027_157_497, 2024: 2_849_071_648}
ASSOC = {2022: 5_203_864_137, 2023: 4_771_744_554, 2024: 4_281_246_884}  # 관계기업투자(단조감소)
CAPITAL = 18_696_175_000  # 자본금(4년 불변, 정상)


def _row(key: str, sj: str, year: int, amt: float) -> dict:
    return {"series_key": key, "sj_div": sj, "year": year, "amount": amt}


def _rows() -> list[dict]:
    rows: list[dict] = []
    for y, a in CAPEX.items():
        rows.append(_row("유형자산취득", "CF", y, a))
    for y, a in ASSOC.items():
        rows.append(_row("관계기업투자", "BS", y, a))
    for y in (2021, 2022, 2023, 2024):
        rows.append(_row("자본금", "BS", y, CAPITAL))
        rows.append(_row("자산총계", "BS", y, ASSET))
    return rows


# ── delta_score ──────────────────────────────────────────────────────────────
def test_delta_score_basic():
    score = delta_score(2_849_071_648, 1_027_157_497, ASSET)
    assert math.isclose(score, abs(2_849_071_648 - 1_027_157_497) / ASSET, rel_tol=1e-9)
    assert score > 0.016


def test_delta_score_prior_none_is_zero():
    assert delta_score(2_849_071_648, None, ASSET) == 0.0


def test_delta_score_zero_asset_is_zero():
    assert delta_score(100, 50, 0) == 0.0


# ── trend_score ──────────────────────────────────────────────────────────────
def test_trend_score_monotonic_decline_full_monotonicity():
    # 관계기업 단조감소 → 단조성 1.0 × 누적변화/자산
    vals = [ASSOC[2022], ASSOC[2023], ASSOC[2024]]
    score = trend_score(vals, ASSET)
    expected = 1.0 * abs(ASSOC[2024] - ASSOC[2022]) / ASSET
    assert math.isclose(score, expected, rel_tol=1e-9)
    assert score > 0


def test_trend_score_nonmonotonic_penalised():
    # capex U자(감소후 급증) → 단조성 < 1
    vals = [CAPEX[2021], CAPEX[2022], CAPEX[2023], CAPEX[2024]]
    score = trend_score(vals, ASSET)
    # diffs 부호 -,+,+ → 단조성 2/3
    mono = 2 / 3
    expected = mono * abs(CAPEX[2024] - CAPEX[2021]) / ASSET
    assert math.isclose(score, expected, rel_tol=1e-9)


def test_trend_score_too_short_is_zero():
    assert trend_score([100], ASSET) == 0.0
    assert trend_score([None, 100], ASSET) == 0.0  # 결측 제거 후 1개


# ── volatility_score ─────────────────────────────────────────────────────────
def test_volatility_zero_for_constant():
    assert volatility_score([100, 100, 100]) == 0.0


def test_volatility_positive_for_varying():
    assert volatility_score([10, 20, 30]) > 0


# ── mix_score ────────────────────────────────────────────────────────────────
def test_mix_score_is_share_change():
    assert math.isclose(mix_score(0.30, 0.20), 0.10, rel_tol=1e-9)


# ── compute_self_axes (통합, 2케이스 ripple) ─────────────────────────────────
def test_capex_delta_beats_constant_account():
    axes = {a["series_key"]: a for a in compute_self_axes(_rows(), ASSET, 2024)}
    # capex는 변화금액축에서 불변 자본금보다 크게 잡혀야 한다
    assert axes["유형자산취득"]["delta"] > axes["자본금"]["delta"]
    assert axes["자본금"]["delta"] == 0.0


def test_associate_trend_beats_constant_and_is_monotonic():
    axes = {a["series_key"]: a for a in compute_self_axes(_rows(), ASSET, 2024)}
    # 관계기업 단조감소는 추세축에서 불변 자본금보다 크게 잡혀야 한다
    assert axes["관계기업투자"]["trend"] > axes["자본금"]["trend"]
    assert axes["자본금"]["trend"] == 0.0
    assert axes["관계기업투자"]["volatility"] > 0


# ── S2: 정규화 + 통합강도 (합성분포 2케이스 ripple) ──────────────────────────
ASSET2 = 100_000_000_000  # 합성 자산총계


NORMALS = ("n1", "n2", "n3", "n4", "n5", "n6")
CHANGE_AXES = ("delta_q", "trend_q", "volatility_q")  # 규모변화 축(mix 제외 — 보완효과)


def _profile_rows() -> list[dict]:
    """이상 2계정(급변·추세) + 정상 6계정(상수). 상수 정상은 변화 축에서 0점."""
    rows: list[dict] = []
    for y, a in {2021: 140, 2022: 90, 2023: 1000, 2024: 2800}.items():  # capex류 급변
        rows.append(_row("capex류", "CF", y, a * 1_000_000))
    for y, a in {2022: 5200, 2023: 4770, 2024: 4280}.items():  # 관계기업류 단조감소
        rows.append(_row("assoc류", "BS", y, a * 1_000_000))
    for key, base in {
        "n1": 10000,
        "n2": 8000,
        "n3": 6000,
        "n4": 5000,
        "n5": 3000,
        "n6": 2000,
    }.items():
        for y in (2021, 2022, 2023, 2024):  # 상수(변화 0)
            rows.append(_row(key, "BS", y, base * 1_000_000))
    return rows


def test_normalize_monotonic_preserves_order():
    axes = compute_self_axes(_profile_rows(), ASSET2, 2024)
    norm = {a["series_key"]: a for a in normalize_axes(axes)}
    # capex류 delta 원점수 최대 → delta 분위도 최상위
    assert norm["capex류"]["delta_q"] >= max(
        norm[k]["delta_q"] for k in ("n1", "n2", "n3", "n4", "n5", "n6")
    )
    assert 0.0 <= norm["capex류"]["delta_q"] <= 1.0


def test_strength_sorted_descending():
    strengths = compute_strength(normalize_axes(compute_self_axes(_profile_rows(), ASSET2, 2024)))
    vals = [s["strength"] for s in strengths]
    assert vals == sorted(vals, reverse=True)


def test_capex_flagged_on_delta_axis():
    strengths = {
        s["series_key"]: s
        for s in compute_strength(normalize_axes(compute_self_axes(_profile_rows(), ASSET2, 2024)))
    }
    assert strengths["capex류"]["flagged"] is True
    assert "delta" in strengths["capex류"]["tail_axes"]


def test_associate_flagged_on_trend_axis():
    strengths = {
        s["series_key"]: s
        for s in compute_strength(normalize_axes(compute_self_axes(_profile_rows(), ASSET2, 2024)))
    }
    assert strengths["assoc류"]["flagged"] is True
    assert "trend" in strengths["assoc류"]["tail_axes"]


def test_constant_normals_low_on_change_axes():
    # 상수 정상계정은 규모변화 축(delta/trend/volatility)에서 분위가 tail 미만(거짓 급변 0)
    norm = {
        a["series_key"]: a for a in normalize_axes(compute_self_axes(_profile_rows(), ASSET2, 2024))
    }
    for key in NORMALS:
        for axis_q in CHANGE_AXES:
            assert norm[key][axis_q] < 0.8, f"{key}.{axis_q}={norm[key][axis_q]} should be < tail"


def test_anomalies_flagged_normals_not_on_change_axes():
    strengths = {
        s["series_key"]: s
        for s in compute_strength(normalize_axes(compute_self_axes(_profile_rows(), ASSET2, 2024)))
    }
    # 이상 2계정은 반드시 후보(거짓 음성 0) — 변화 축으로 flag
    assert strengths["capex류"]["flagged"] and "delta" in strengths["capex류"]["tail_axes"]
    assert strengths["assoc류"]["flagged"] and "trend" in strengths["assoc류"]["tail_axes"]
    # 정상계정은 규모변화 축(delta/trend/volatility)으로는 flag되지 않는다
    for key in NORMALS:
        change_flags = {
            ax for ax in strengths[key]["tail_axes"] if ax in ("delta", "trend", "volatility")
        }
        assert not change_flags, f"{key} flagged on change axis {change_flags}"


# ── S3: 실데이터(대주산업) — build_account_profile이 capex를 후보로 올리는지 ────
_DAEJU = ("00112457", [2021, 2022, 2023, 2024])


@pytest.fixture(scope="module")
def daeju_profile():
    """실 DB 의존(대주산업 정규화 필요). build_company_report→build_account_profile."""
    from src.report.company_report import build_company_report

    report = build_company_report(_DAEJU[0], _DAEJU[1])
    prof = build_account_profile(report)
    if not prof:
        pytest.skip("대주산업 정규화 DB 없음 — 실데이터 테스트 건너뜀")
    return {p["series_key"]: p for p in prof}, prof


def test_real_capex_surfaces_as_candidate(daeju_profile):
    by_key, _ = daeju_profile
    capex = next((by_key[k] for k in by_key if "유형자산취득" in k), None)
    assert capex is not None
    # capex 급증(+177%)은 변화금액 축으로 후보에 떠야 한다(설계 핵심)
    assert capex["flagged"] is True
    assert "delta" in capex["tail_axes"]


def test_real_associate_trend_detected_but_below_tail(daeju_profile):
    # §9 정직 고정: 관계기업 단조감소는 추세축으로 감지(trend_q 상위권)되나, 금액이 작아
    # self축만으론 tail 미달(현 동작). 잡으려면 peer 수준축(S4)/단조성 가중 보강 필요.
    by_key, _ = daeju_profile
    assoc = next((by_key[k] for k in by_key if "관계기업투자" in k), None)
    assert assoc is not None
    assert assoc["trend_q"] > 0.6  # 추세는 감지(상위권)
    assert assoc["flagged"] is False  # 알려진 갭: self축 단독 미달


def test_real_candidate_count_bounded(daeju_profile):
    _, prof = daeju_profile
    flagged = sum(1 for p in prof if p["flagged"])
    assert 0 < flagged < len(prof)  # 후보 폭주(전체=후보) 아님
