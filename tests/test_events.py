"""S10 — event/report 수집·라우팅 테스트(결정론 로직)."""

from pathlib import Path

import pandas as pd

from src.collect.events import (
    EVENT_KEYWORDS,
    REPORT_KEYWORDS,
    collect_events,
    collect_reports,
    load_routing,
    routed_timeline,
)


class _FakeCollector:
    """event/report 대역 — 특정 key_word만 데이터 반환."""

    def __init__(self, events: dict, reports: dict) -> None:
        self._events = events
        self._reports = reports

    def event(self, corp_code: str, key_word: str, start: str, end: str) -> pd.DataFrame:
        return pd.DataFrame(self._events.get(key_word, []))

    def report(self, corp_code: str, key_word: str, year: int) -> pd.DataFrame:
        return pd.DataFrame(self._reports.get(key_word, []))


def test_keyword_counts() -> None:
    assert len(EVENT_KEYWORDS) == 36  # OpenDartReader event 유효목록(주요사항보고서 36종)
    assert len(REPORT_KEYWORDS) == 28  # 정기보고서 주요정보 28종


def test_collect_events_keeps_only_nonempty_and_saves(tmp_path: Path) -> None:
    collector = _FakeCollector(
        events={
            "전환사채발행": [{"bddd": "2021-07-28", "cv_prc": "20751"}],
            "유상증자": [{"bddd": "2020-03-02"}],
        },
        reports={},
    )

    out = collect_events(collector, "00100", data_dir=tmp_path)

    assert set(out) == {"전환사채발행", "유상증자"}  # 비어있는 33종 제외
    assert (tmp_path / "00100" / "raw" / "events.json").exists()


def test_collect_reports_aggregates_years(tmp_path: Path) -> None:
    collector = _FakeCollector(events={}, reports={"최대주주변동": [{"change_on": "2022-05-01"}]})

    out = collect_reports(collector, "00100", (2022, 2023), data_dir=tmp_path)

    assert "최대주주변동" in out
    assert len(out["최대주주변동"]) == 2  # 두 연도 누적


def test_load_routing_flattens_to_keyword_perspective() -> None:
    routing = load_routing()

    assert routing["전환사채발행"] == "flow"
    assert routing["회사합병"] == "trend"
    assert routing["부도발생"] == "numeric"
    assert routing["최대주주변동"] == "trend"


def test_routed_timeline_groups_by_perspective_with_terms(tmp_path: Path) -> None:
    # 수집 저장 후 라우팅. G4: 고가치 조건(terms)을 compact whitelist로 함께 전달.
    collector = _FakeCollector(
        events={
            "전환사채발행": [
                {
                    "bddd": "2021-07-28",
                    "bd_fta": "300,000,000,000",  # 발행총액
                    "cv_prc": "20751",  # 전환가액
                    "act_mktprcfl_cvprc_lwtrsprc": "14525",  # 리픽싱 최저조정가
                    "fdpp_op": "100,000,000,000",  # 운영자금
                    "corp_name": "테스트",  # 메타 — 제외돼야
                }
            ],  # → flow
            "회사합병": [{"bddd": "2019-03-01"}],  # → trend, terms 없음
        },
        reports={"최대주주변동": [{"foo": "2022-05-01"}]},  # → trend
    )
    collect_events(collector, "00100", data_dir=tmp_path)
    collect_reports(collector, "00100", (2022,), data_dir=tmp_path)

    timeline = routed_timeline("00100", tmp_path)

    flow_types = {e["type"] for e in timeline.get("flow", [])}
    change_types = {e["type"] for e in timeline.get("trend", [])}
    assert flow_types == {"전환사채발행"}
    assert change_types == {"회사합병", "최대주주변동"}
    cb = next(e for e in timeline["flow"] if e["type"] == "전환사채발행")
    assert cb["date"] == "2021-07-28"
    assert cb["source"] == "event"
    # G4: terms에 핵심 조건이 사람이 읽는 라벨로 들어가야(발행총액·전환가·리픽싱·자금용도)
    terms = cb["terms"]
    assert terms["발행총액"] == "300,000,000,000"
    assert terms["전환가액"] == "20751"
    assert terms["리픽싱최저가"] == "14525"
    assert terms["자금용도_운영"] == "100,000,000,000"
    # 메타(corp_name)는 terms에 섞이면 안 됨(토큰 bounded whitelist)
    assert "corp_name" not in terms and "테스트" not in terms.values()
    # terms 없는 이벤트는 빈 dict(키는 항상 존재)
    mg = next(e for e in timeline["trend"] if e["type"] == "회사합병")
    assert mg["terms"] == {}


def test_routed_timeline_graceful_when_absent(tmp_path: Path) -> None:
    assert routed_timeline("99999", tmp_path) == {}
