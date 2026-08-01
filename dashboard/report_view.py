"""L5 분석 리포트 페이지 — 결정론 리포트(헤더·큐·비율) + 의심건 카드(LLM).

계산·카드 로직은 src/report가 담당(여기선 호출만). HTML 생성은 report_html 순수 함수를
st.html로 주입한다. corp_code·연도는 입력에서 받는다(하드코딩 금지). API 미설정·데이터
부재·LLM 오류는 전부 안내로 흡수한다(크래시 금지).
"""

from __future__ import annotations

import asyncio

import streamlit as st

from dashboard.card_view import render_cards_section
from dashboard.company_search import render_company_search
from dashboard.report_html import (
    render_header_html,
    render_queue_html,
    render_ratio_html,
    render_selection_html,
)
from dashboard.steps import COLLECT, CROSS, NORMALIZE, READ, all_done, build_steps
from dashboard.steps import render_steps_html as _steps_html
from dashboard.style import busy, inject_css

__all__ = [
    "render",
    "render_header_html",
    "render_queue_html",
    "render_ratio_html",
    "analysis_window",
    "window_for_year",
]

ANNUAL_FS_NOTE = "연차별(사업연도) 재무제표 기준 분석입니다. 분기·반기 보고서는 지원하지 않습니다."


def window_for_year(available: list[int], selected: int, size: int = 5) -> list[int]:
    """선택 연도 이하의 최근 size개 연도를 분석 윈도우로(기본 5년). 순수(테스트 가능).

    선택연도를 target으로 하되 YoY·추세 신호를 위해 직전 연도들을 포함한다
    (build_company_report는 window의 max를 target_year로 삼는다).
    """

    priors = [y for y in sorted(available) if y <= selected]
    return priors[-size:]


def analysis_window(target: int, span: int = 5) -> list[int]:
    """타깃 사업연도 기준 최근 span개 연속 연도(기본 5). 보유 raw와 무관하게 전 구간을 낸다.

    이 목록이 '준비'가 확보해야 할 연도 — 없는 연도는 DART에서 수집한다(그래야 YoY·추세 성립).
    window_for_year(보유연도로 제한)와 달리, 미보유 연도까지 포함해 수집 대상을 만든다.
    """

    return list(range(target - span + 1, target + 1))


def _step_context(corp_code: str, year: int, window: list[int], key: str) -> list[dict]:
    """4단계 상태 — 마커·raw 유무·저장 카드를 읽어 진행 표시용 목록을 만든다.

    phase1 결정론 지표(검토큐·비율)는 UI에 표시하지 않는다(내부 중간산출물).
    교차검증 = 내부에서 phase1 계산 후 phase2 카드 생성.
    """

    from src.report.prep import raw_present, read_onboarding_marker, read_prep_marker

    marker = read_onboarding_marker(corp_code, year) or {}
    onboarded_at = str(marker.get("completed_at") or "")[:10] if marker else None
    prep = read_prep_marker(corp_code, year) or {}
    return build_steps(
        window=window,
        missing_years=[y for y in window if not raw_present(corp_code, y)],
        prepared=bool(prep.get("gate_passed")),
        onboarded_at=onboarded_at,
        cards_at=_load_saved_cards_if_needed(corp_code, year, key),
    )


def _review_scope(report: dict, card_result: dict | None = None) -> dict:
    """헤더용 검토범위. 카드 실행 후엔 card_report의 review_scope를 그대로 쓴다."""

    if card_result:
        return card_result.get("review_scope") or {}
    rows = report.get("account_level_series") or []
    ledger = report.get("coverage_ledger") or {}
    return {
        "accounts_reviewed": len({str(r.get("series_key")) for r in rows if r.get("series_key")}),
        "perspectives_run": 0,  # 결정론 단계 — 관점 LLM 미실행
        "unaccounted_cells": len(ledger.get("unaccounted") or []),
        "derived_blocked": len((ledger.get("derived") or {}).get("blocked") or []),
        "derived_blocked_amount": float((ledger.get("derived") or {}).get("blocked_amount") or 0.0),
    }


def _render_zero_findings(scope: dict) -> None:
    """의심건 0건을 빈화면 대신 검토 범위로 명시(§9 hollow-PASS 차단)."""

    failed = int(scope.get("perspectives_failed", 0) or 0)
    run = int(scope.get("perspectives_run", 0) or 0)
    accounts = int(scope.get("accounts_reviewed", 0) or 0)
    if failed:  # LLM 실패한 0건은 '위험 없음'이 아니라 미검증이다.
        st.warning(
            f"관점 {failed}개가 LLM 호출 실패로 의심건이 미검증이다(완료 {run}개). "
            "API 키·크레딧·타임아웃 확인 후 재실행."
        )
        return
    st.info(f"계정 {accounts}개·관점 {run}개를 검토했으나 제기된 의심 후보 0건이다.")


def _render_card_sections(card_result: dict) -> None:
    """의심건 카드 3섹션 — 대형 카드(주장·수치 표·추이 차트). 시계열은 분석 때 저장된 컨텍스트."""

    if not card_result.get("has_findings"):
        _render_zero_findings(card_result.get("review_scope") or {})
        return
    # 외부 검증이 키 부재로 통째 생략된 경우 — 카드별 '미수행'과 구분해 명시(§9).
    if (card_result.get("external_verification") or {}).get("status") == "deferred":
        st.caption(
            "ℹ 외부 검증 생략 — GOOGLE_API_KEY 미설정"
            "(설정 후 재실행 시 상위 카드에 외부 근거가 붙습니다)."
        )
    series_rows = st.session_state.get("rv_series") or []
    target_year = int(st.session_state.get("rv_target_year") or 0)
    render_cards_section(
        "계정별 의심 후보",
        card_result.get("account_cards") or [],
        series_rows,
        target_year,
        grouped=True,  # 넓은 주제 그룹이 1차 구조(점수 전체 줄세우기 대체)
    )
    render_cards_section(
        "계정 관계 이상",
        card_result.get("relationship_cards") or [],
        series_rows,
        target_year,
    )
    render_cards_section(
        "회사 전체 이슈", card_result.get("company_cards") or [], series_rows, target_year
    )


def _do_prepare(corp_code: str, corp_name: str, target_year: int, window: list[int]) -> bool:
    """수집·표준 계정 변환·품질 검문. 통과 여부를 돌려주고, 실패는 안내로 흡수한다(크래시 금지)."""

    from src.report.prep import prepare_company

    # st.status 대신 busy() 스피너 + 로그 placeholder — 기본 스피너가 reduced-motion에서 멈추는 문제 회피.
    log_ph = st.empty()
    logs: list[str] = []

    def _progress(msg: str) -> None:
        logs.append(msg)
        log_ph.markdown("\n".join(f"- {m}" for m in logs))

    try:
        with busy(f"{corp_name or corp_code} {target_year} — 수집·표준 계정 변환 중..."):
            result = prepare_company(corp_code, target_year, window, progress=_progress)
    except Exception as exc:  # noqa: BLE001 — 준비 오류는 안내로 흡수(크래시 금지)
        st.error(f"표준 계정 변환 실패(안내만): {type(exc).__name__}: {exc}")
        return False
    log_ph.empty()
    if result["gate_passed"]:
        st.session_state.pop("rv_report", None)
        return True
    st.error(
        "품질 검문(온보딩 게이트) 미통과 — 정규화 이탈이 있습니다. "
        "정비 페이지(dashboard/onboarding.py 단독 실행)에서 quirk 교정 후 재시도하세요."
    )
    gate = result.get("gate") or {}
    st.json({k: gate.get(k) for k in ("gate_passed", "G1_machine", "G3_arithmetic")})
    return False


def _run_analysis(corp_code: str, corp_name: str, year: int, window: list[int], key: str) -> None:
    """의심건 카드 생성 — 내부에서 Phase1(결정론) 계산 후 Phase2(6관점 LLM). 카드만 남긴다.

    Phase1 리포트는 화면에 표시하지 않고 Phase2 입력으로만 쓴다(사람용 산출물 = 카드).
    """

    import time

    from config.settings import settings
    from src.report.card_pipeline import build_suspicion_cards
    from src.report.company_report import build_company_report

    # 본문 읽기가 이미 끝난 회사연도는 _do_read를 건너뛰므로 여기서 키를 다시 확인한다.
    if not settings.openai_api_key:
        st.info("OPENAI_API_KEY 미설정 — 교차검증(LLM) 생략. .env 설정 후 재실행.")
        return

    _phase_label = {
        "grounding": "근거 검증",
        "cards": "카드 생성",
        "rebuttal": "반박 검토",
        "done": "완료",
    }
    progress = st.empty()
    started = time.perf_counter()

    def _on_progress(p: dict) -> None:
        el = int(time.perf_counter() - started)
        if p["phase"] == "perspective":
            progress.info(f"관점 분석 중 — {p['done']}/{p['total']} 완료 · 경과 {el}s")
        else:
            progress.info(f"{_phase_label.get(p['phase'], p['phase'])} 중 · 경과 {el}s")

    try:
        with busy(f"Phase1 결정론 신호 계산 중 ({corp_name or corp_code} {year})..."):
            report = build_company_report(corp_code, window)
        # 카드 차트·근거 표가 참조할 계정 시계열 컨텍스트(분석 시점 스냅샷) 저장.
        st.session_state["rv_series"] = report.get("account_level_series") or []
        st.session_state["rv_target_year"] = report.get("target_year")
        with busy("멀티 에이전트 교차검증 중 (수 분 소요)..."):
            st.session_state["rv_cards"] = asyncio.run(
                build_suspicion_cards(report, on_progress=_on_progress)
            )
        progress.empty()
        st.session_state["rv_analysis_key"] = key
        st.session_state.pop("rv_cards_saved_at", None)  # 방금 실행 — '저장본 표시' 캡션 잔상 제거
        # 영속화 — 세션이 끊겨도 LLM 재실행 없이 다시 본다(비용 방지, 전처리 마커와 동일 원칙).
        from src.report.cards_store import save_cards

        save_cards(
            corp_code,
            year,
            st.session_state["rv_cards"],
            st.session_state["rv_series"],
            st.session_state["rv_target_year"],
        )
    except Exception as exc:  # noqa: BLE001 — LLM·데이터 오류는 안내로 흡수(크래시 금지)
        st.error(f"분석 실패(안내만): {type(exc).__name__}: {exc}")


def _do_read(corp_code: str, year: int, key: str, steps: list[dict]) -> bool:
    """사업보고서 본문 읽기(LLM) + 완료 마커 영속(재실행 방지). API 키 없으면 안내만."""

    from config.settings import settings

    if not settings.openai_api_key:
        st.info("OPENAI_API_KEY 미설정 — 본문 읽기(LLM) 생략. .env 설정 후 재실행.")
        return False
    import time

    from dashboard.onboarding import run_full_onboarding
    from src.report.prep import write_onboarding_marker

    board = st.empty()
    started = time.perf_counter()

    def _on_progress(p: dict) -> None:
        elapsed = int(time.perf_counter() - started)
        board.html(
            _steps_html(
                steps, running=READ, running_meta=f"{p['done']}/{p['total']} 파트 · 경과 {elapsed}s"
            )
        )

    board.html(_steps_html(steps, running=READ, running_meta="시작"))
    with busy(f"{year} 사업보고서 본문 읽는 중 (수 분 소요)..."):
        result = run_full_onboarding(corp_code, str(year), on_progress=_on_progress)
    board.empty()
    st.session_state["rv_onboarding"] = result
    st.session_state["rv_onboarding_key"] = key
    layer1 = result.get("layer1") or {}
    # 실패·미실행에 완료 마커를 쓰면 이 단계가 ✓로 굳어 영영 재실행을 안 한다
    # (셀트리온 2019가 이 경로로 서술 추출 없이 몇 주간 분석됨). 완주(ok/empty)만 완료다.
    if layer1.get("status") not in ("ok", "empty"):
        st.error(f"본문 읽기 실패 — 완료 처리하지 않음. {layer1.get('message', '')}")
        return False
    extracts = layer1.get("extracts", []) or []
    write_onboarding_marker(corp_code, year, chunks=len(extracts))
    return True


def _run_all(corp_code: str, corp_name: str, year: int, window: list[int], key: str) -> None:
    """[분석 실행] — 안 끝난 단계만 순서대로 실행하고, 하나라도 실패하면 거기서 멈춘다."""

    steps = _step_context(corp_code, year, window, key)
    done = {s["key"]: s["done"] for s in steps}
    board = st.empty()

    if not (done[COLLECT] and done[NORMALIZE]):
        board.html(_steps_html(steps, running=NORMALIZE, running_meta="진행 중"))
        if not _do_prepare(corp_code, corp_name, year, window):
            return
    if not done[READ]:
        board.empty()
        if not _do_read(corp_code, year, key, steps):
            return
    board.html(_steps_html(steps, running=CROSS, running_meta="진행 중"))
    _run_analysis(corp_code, corp_name, year, window, key)
    board.empty()
    st.rerun()


def _render_cards(corp_code: str, year: int, key: str) -> None:
    """의심건 카드 섹션(최종 결과) — 실행 버튼은 위 [분석 실행] 하나로 합쳤다."""

    saved = _load_saved_cards_if_needed(corp_code, year, key)
    # 회사·연도가 바뀐 옛 카드는 표시하지 않는다(잔상 방지).
    if not (st.session_state.get("rv_cards") and st.session_state.get("rv_analysis_key") == key):
        return
    st.markdown("---")
    if saved:
        st.caption(f"저장된 검증 결과 표시 중 (생성: {saved})")
    _render_card_sections(st.session_state["rv_cards"])


def _load_saved_cards_if_needed(corp_code: str, year: int, key: str) -> str | None:
    """세션에 이 회사·연도 카드가 없으면 디스크 스냅샷 로드(LLM 재실행 방지).

    반환: 로드/보유한 스냅샷의 생성시각(표시용, 이번 세션 직접 실행이면 None).
    """

    if st.session_state.get("rv_analysis_key") == key and st.session_state.get("rv_cards"):
        return st.session_state.get("rv_cards_saved_at")  # 이미 세션에 있음(직접 실행 or 기로드)

    from src.report.cards_store import load_cards

    payload = load_cards(corp_code, year)
    if not payload:
        return None
    st.session_state["rv_cards"] = {
        "has_findings": payload.get("has_findings"),
        "review_scope": payload.get("review_scope") or {},
        "external_verification": payload.get("external_verification") or {},
        "account_cards": payload.get("account_cards") or [],
        "relationship_cards": payload.get("relationship_cards") or [],
        "company_cards": payload.get("company_cards") or [],
    }
    st.session_state["rv_series"] = payload.get("series_rows") or []
    st.session_state["rv_target_year"] = payload.get("target_year")
    st.session_state["rv_analysis_key"] = key
    saved_at = str(payload.get("created_at") or "")[:16].replace("T", " ")
    st.session_state["rv_cards_saved_at"] = saved_at
    return saved_at


def _render_uncollected(corp_code: str, corp_name: str) -> None:
    """상태 A(미수집) — 연도 드롭다운을 만들 raw가 없으므로 연도를 직접 입력받는다."""

    st.caption("분석할 사업연도를 고르면 직전 4년까지 총 5년을 DART에서 수집한 뒤 분석합니다.")
    year = int(st.number_input("분석 사업연도", min_value=2015, max_value=2030, value=2024, step=1))
    _render_run_block(corp_code, corp_name, year, analysis_window(year))


def _render_run_block(corp_code: str, corp_name: str, year: int, window: list[int]) -> None:
    """[분석 실행] 버튼 + 4단계 진행 표시. 안 끝난 단계가 있으면 무엇이 도는지 먼저 밝힌다."""

    key = f"{corp_code}:{year}"
    steps = _step_context(corp_code, year, window, key)
    finished = all_done(steps)
    if not finished:
        st.html(
            '<div class="drv-note">원본 수집, 사업보고서 본문 읽기, 멀티 에이전트 교차검증이 '
            "함께 실행됩니다. (LLM 호출 및 수 분 소요)</div>"
        )
    if st.button("다시 실행" if finished else "분석 실행", type="primary"):
        _run_all(corp_code, corp_name, year, window, key)
    st.html(_steps_html(steps))


def render() -> None:
    """분석 리포트 페이지 — 검색 → 연도 선택 → [분석 실행] 하나 → 의심건 카드.

    수집·표준 계정 변환·본문 읽기·교차검증은 사용자가 누르는 단계가 아니라 진행 표시다.
    끝난 단계는 마커를 보고 건너뛴다(_step_context).
    """

    inject_css()
    st.title("FS Multi-agents analyzer")

    corp_code = render_company_search()
    if not corp_code:
        return
    corp_name = st.session_state.get("cs_selected_name", "")

    from src.report.prep import company_state

    state = company_state(corp_code)
    st.html(render_selection_html(corp_name, corp_code))

    if state["state"] == "A":  # 미수집 — 연도 입력부터
        _render_uncollected(corp_code, corp_name)
        return

    raw_yrs = state["raw_years"]
    st.markdown(
        f'<div style="font-size:0.875rem;margin-bottom:0.25rem;">분석 사업연도 '
        f'<span class="drv-caption" style="margin:0;">- {ANNUAL_FS_NOTE}</span></div>',
        unsafe_allow_html=True,
    )
    selected_year = int(
        st.selectbox(
            "분석 사업연도",
            list(reversed(raw_yrs)),
            index=0,
            label_visibility="collapsed",
        )
    )

    window = analysis_window(selected_year)
    _render_run_block(corp_code, corp_name, selected_year, window)
    _render_cards(corp_code, selected_year, f"{corp_code}:{selected_year}")
