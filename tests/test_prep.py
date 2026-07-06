"""분석 준비 상태·마커·phase gating 순수 로직 검증 (tmp dir — 실데이터·LLM 불필요)."""

from __future__ import annotations

from pathlib import Path

from dashboard.report_view import analysis_window, visible_stages, window_for_year
from src.report.prep import (
    company_state,
    onboarding_done,
    prepared_years,
    raw_years,
    read_prep_marker,
    write_onboarding_marker,
    write_prep_marker,
)


def _make_raw(root: Path, corp: str, year: int) -> None:
    raw = root / corp / str(year) / "raw"
    raw.mkdir(parents=True, exist_ok=True)
    (raw / "finstate_all_CFS.csv").write_text("stub", encoding="utf-8")


# ── company_state 3분류 ──────────────────────────────────────────────────
def test_state_a_uncollected(tmp_path):
    st = company_state("00000001", root=tmp_path)
    assert st["state"] == "A" and st["raw_years"] == [] and st["prepared_years"] == []


def test_state_b_collected_not_prepared(tmp_path):
    _make_raw(tmp_path, "00000002", 2024)
    _make_raw(tmp_path, "00000002", 2023)
    st = company_state("00000002", root=tmp_path)
    assert st["state"] == "B"
    assert st["raw_years"] == [2023, 2024]
    assert st["prepared_years"] == []


def test_state_c_prepared(tmp_path):
    _make_raw(tmp_path, "00000003", 2024)
    write_prep_marker("00000003", 2024, gate_passed=True, window=[2020, 2024], root=tmp_path)
    st = company_state("00000003", root=tmp_path)
    assert st["state"] == "C"
    assert st["prepared_years"] == [2024]


def test_gate_failed_marker_not_prepared(tmp_path):
    # 게이트 FAIL 마커는 준비완료로 치지 않는다(상태 B 유지).
    _make_raw(tmp_path, "00000004", 2024)
    write_prep_marker("00000004", 2024, gate_passed=False, root=tmp_path)
    assert prepared_years("00000004", root=tmp_path) == []
    assert company_state("00000004", root=tmp_path)["state"] == "B"


# ── 마커 왕복 ────────────────────────────────────────────────────────────
def test_marker_roundtrip_pass(tmp_path):
    _make_raw(tmp_path, "00000005", 2024)
    write_prep_marker("00000005", 2024, gate_passed=True, window=[2022, 2023, 2024], root=tmp_path)
    m = read_prep_marker("00000005", 2024, root=tmp_path)
    assert m is not None and m["gate_passed"] is True and m["window"] == [2022, 2023, 2024]


def test_marker_roundtrip_fail(tmp_path):
    _make_raw(tmp_path, "00000006", 2024)
    write_prep_marker("00000006", 2024, gate_passed=False, root=tmp_path)
    m = read_prep_marker("00000006", 2024, root=tmp_path)
    assert m is not None and m["gate_passed"] is False


def test_marker_absent_is_none(tmp_path):
    assert read_prep_marker("00000007", 2024, root=tmp_path) is None


# ── 온보딩 완료 마커(재실행 방지) ────────────────────────────────────────
def test_onboarding_not_done_without_marker(tmp_path):
    assert onboarding_done("00000010", 2025, root=tmp_path) is False


def test_onboarding_done_after_marker(tmp_path):
    write_onboarding_marker("00000010", 2025, chunks=3, root=tmp_path)
    assert onboarding_done("00000010", 2025, root=tmp_path) is True
    # 다른 연도는 여전히 미완(연도별 독립)
    assert onboarding_done("00000010", 2024, root=tmp_path) is False


# ── raw_years 정렬 ───────────────────────────────────────────────────────
def test_raw_years_sorted(tmp_path):
    for y in (2025, 2021, 2023):
        _make_raw(tmp_path, "00000008", y)
    assert raw_years("00000008", root=tmp_path) == [2021, 2023, 2025]


# ── phase gating (미준비면 분석·온보딩 숨김) ─────────────────────────────
def test_visible_stages_unprepared():
    s = visible_stages(is_prepared=False)
    assert s["prepare"] is True and s["analysis"] is False and s["onboarding"] is False


def test_visible_stages_prepared():
    s = visible_stages(is_prepared=True)
    assert s["prepare"] is False and s["analysis"] is True and s["onboarding"] is True


# ── 수집·분석 윈도우 5년 ─────────────────────────────────────────────────
def test_window_default_size_five():
    assert window_for_year([2020, 2021, 2022, 2023, 2024, 2025], 2024) == [
        2020,
        2021,
        2022,
        2023,
        2024,
    ]


def test_analysis_window_full_5_years_regardless_of_raw():
    # 보유 raw와 무관하게 타깃-4 ~ 타깃 5개 연속(없는 연도 = 수집 대상).
    assert analysis_window(2025) == [2021, 2022, 2023, 2024, 2025]
    assert analysis_window(2023) == [2019, 2020, 2021, 2022, 2023]
