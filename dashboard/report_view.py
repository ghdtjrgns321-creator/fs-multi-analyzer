"""L5 분석 리포트 페이지 — 결정론 리포트(헤더·큐·비율) + 의심건 카드(LLM).

계산·카드 로직은 src/report가 담당(여기선 호출만). HTML 생성은 report_html 순수 함수를
st.html로 주입한다. corp_code·연도는 입력에서 받는다(하드코딩 금지). API 미설정·데이터
부재·LLM 오류는 전부 안내로 흡수한다(크래시 금지).
"""

from __future__ import annotations

import asyncio

import streamlit as st

from dashboard.company_search import render_company_search
from dashboard.report_html import (
    render_card_html,
    render_cards_section_html,
    render_header_html,
    render_queue_html,
    render_ratio_html,
    render_selection_html,
)
from dashboard.style import busy, inject_css

__all__ = [
    "render",
    "render_card_html",
    "render_cards_section_html",
    "render_header_html",
    "render_queue_html",
    "render_ratio_html",
    "analysis_window",
    "visible_stages",
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


def visible_stages(is_prepared: bool) -> dict[str, bool]:
    """화면 단계 노출 판정(순수). 미준비→준비만. 준비완료→온보딩(선택)+분석(의심건 카드).

    phase1 결정론 지표(검토큐·비율)는 UI에 표시하지 않는다(내부 중간산출물 — 추후 별도 탭 그래프).
    분석 = 내부에서 phase1 계산 후 phase2 카드 생성. 순서: 온보딩 → phase1 → phase2.
    """

    return {
        "prepare": not is_prepared,
        "onboarding": is_prepared,
        "analysis": is_prepared,
    }


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
    if not card_result.get("has_findings"):
        _render_zero_findings(card_result.get("review_scope") or {})
        return
    st.html(render_cards_section_html("계정별 의심 후보", card_result.get("account_cards") or []))
    st.html(
        render_cards_section_html(
            "계정 관계 이상 (흐름)", card_result.get("relationship_cards") or []
        )
    )
    st.html(render_cards_section_html("회사 전체 이슈", card_result.get("company_cards") or []))


def _run_prepare(corp_code: str, corp_name: str, target_year: int, window: list[int]) -> None:
    """분석 준비 파이프라인 실행 + 진행표시. 성공 시 rerun(상태 갱신), 실패 시 게이트 표시."""

    from src.report.prep import prepare_company

    # st.status 대신 busy() 스피너 + 로그 placeholder — 기본 스피너가 reduced-motion에서 멈추는 문제 회피.
    log_ph = st.empty()
    logs: list[str] = []

    def _progress(msg: str) -> None:
        logs.append(msg)
        log_ph.markdown("\n".join(f"- {m}" for m in logs))

    try:
        with busy(f"{corp_name or corp_code} {target_year} 분석 준비 중 (수 분 소요)..."):
            result = prepare_company(corp_code, target_year, window, progress=_progress)
    except Exception as exc:  # noqa: BLE001 — 준비 오류는 안내로 흡수(크래시 금지)
        st.error(f"분석 준비 실패(안내만): {type(exc).__name__}: {exc}")
        return
    log_ph.empty()
    if result["gate_passed"]:
        st.session_state.pop("rv_report", None)
        st.rerun()
    else:
        st.error(
            "온보딩 게이트 미통과 — 정규화 이탈이 있습니다. "
            "온보딩 페이지에서 quirk 교정 후 재시도하세요."
        )
        gate = result.get("gate") or {}
        st.json({k: gate.get(k) for k in ("gate_passed", "G1_machine", "G3_arithmetic")})


def _run_analysis(corp_code: str, corp_name: str, year: int, window: list[int], key: str) -> None:
    """의심건 카드 생성 — 내부에서 Phase1(결정론) 계산 후 Phase2(6관점 LLM). 카드만 남긴다.

    Phase1 리포트는 화면에 표시하지 않고 Phase2 입력으로만 쓴다(사람용 산출물 = 카드).
    """

    from src.report.card_pipeline import build_suspicion_cards
    from src.report.company_report import build_company_report

    try:
        with busy(f"Phase1 결정론 신호 계산 중 ({corp_name or corp_code} {year})..."):
            report = build_company_report(corp_code, window)
        with busy("Phase2 6관점 병렬 분석·근거검증·반박 중 (수 분 소요)..."):
            st.session_state["rv_cards"] = asyncio.run(build_suspicion_cards(report))
        st.session_state["rv_analysis_key"] = key
    except Exception as exc:  # noqa: BLE001 — LLM·데이터 오류는 안내로 흡수(크래시 금지)
        st.error(f"분석 실패(안내만): {type(exc).__name__}: {exc}")


def _run_onboarding(corp_code: str, year: int, key: str) -> None:
    """온보딩 실행 + 완료 마커 영속(재실행 방지). API 키 없으면 안내만."""

    from config.settings import settings

    if not settings.openai_api_key:
        st.info("OPENAI_API_KEY 미설정 — 온보딩 생략. .env 설정 후 재실행.")
        return
    import time

    from dashboard.onboarding import run_full_onboarding
    from src.report.prep import write_onboarding_marker

    progress = st.empty()
    started = time.perf_counter()

    def _on_progress(p: dict) -> None:
        elapsed = int(time.perf_counter() - started)
        progress.info(
            f"본문 파트 읽는 중 — {p['done']}/{p['total']} (방금 PART {p['numeral']}) · 경과 {elapsed}s"
        )

    with busy(f"{year} 본문·정규화 통독 중 (수 분 소요)..."):
        result = run_full_onboarding(corp_code, str(year), on_progress=_on_progress)
    progress.empty()
    st.session_state["rv_onboarding"] = result
    st.session_state["rv_onboarding_key"] = key
    extracts = (result.get("layer1") or {}).get("extracts", []) or []
    write_onboarding_marker(corp_code, year, chunks=len(extracts))


def _render_onboarding_llm(corp_code: str, year: int, key: str) -> None:
    """① 온보딩 — LLM 사전 검토. 이미 완료(마커)면 재실행을 요구하지 않는다."""

    from src.report.prep import onboarding_done

    st.markdown("##### 온보딩 — 데이터 다듬기")
    if onboarding_done(corp_code, year):
        st.caption(
            "✅ 온보딩 완료 — 본문 서술 추출·계정 이름 제안을 이미 수행했습니다. "
            "다시 할 필요는 없습니다(내용이 바뀌었으면 아래에서 재실행)."
        )
        if st.button("온보딩 다시 실행"):
            _run_onboarding(corp_code, year, key)
    else:
        st.caption(
            "분석 전 LLM이 표준분류가 안된 계정에 이름을 제안하고, 본문을 파트별로 읽어 서술형 감사관심을 추출합니다."
        )
        if st.button("온보딩 실행"):
            _run_onboarding(corp_code, year, key)
    # 이번 세션에서 방금 실행했으면 무엇을 산출했는지 요약(감사 소견 아님 — Phase2 전담).
    if st.session_state.get("rv_onboarding_key") == key:
        _render_onboarding_summary(st.session_state.get("rv_onboarding") or {})


def _render_onboarding_summary(result: dict) -> str:
    """온보딩 산출 요약(추출 N·경고 N·별칭 N)을 렌더하고 요약 문자열 반환(테스트 가능)."""

    layer1 = result.get("layer1") or {}
    n_extracts = len(layer1.get("extracts", []) or [])
    n_warns = len(layer1.get("warnings", []) or [])
    elapsed = layer1.get("elapsed_s")
    alias = (result.get("alias") or {}).get("result")
    n_alias = len(getattr(alias, "suggestions", []) or [])
    took = f" · {elapsed:.0f}s 소요" if elapsed else ""
    text = (
        f"서술 추출 {n_extracts}건 · 완결성 경고 {n_warns}건 · 계정 이름 제안 {n_alias}건{took} "
        "(Phase2 재료로 report_extracts 적재)"
    )
    st.caption(text)
    return text


def _render_analysis(
    corp_code: str, corp_name: str, year: int, window: list[int], key: str
) -> None:
    """의심건 카드 섹션(최종 결과). 버튼 → 내부 Phase1→Phase2. Phase1 지표는 미표시."""

    from config.settings import settings

    st.markdown("##### ② 의심건 카드 (6관점 교차검증 · 최종 결과)")
    st.caption(
        "결정론 신호(Phase1)를 계산한 뒤 6관점 LLM이 교차검증·반박해 의심건 카드를 만듭니다. "
        "부정을 확정하지 않으며, 각 카드는 반대근거·정상설명·확인질문·다음절차를 포함합니다."
    )
    if st.button("의심건 카드 생성"):
        if not settings.openai_api_key:
            st.info("OPENAI_API_KEY 미설정 — 의심건 카드(LLM) 생략. .env 설정 후 재실행.")
        else:
            _run_analysis(corp_code, corp_name, year, window, key)
    # 회사·연도가 바뀐 옛 카드는 표시하지 않는다(잔상 방지).
    if st.session_state.get("rv_cards") and st.session_state.get("rv_analysis_key") == key:
        _render_card_sections(st.session_state["rv_cards"])


def _render_uncollected(corp_code: str, corp_name: str) -> None:
    """상태 A(미수집) — 타깃 연도 입력 후 수집+준비를 한 번에."""

    st.caption(
        "수집할 타깃 사업연도를 고르면 직전 4년까지 총 5년을 DART 수집·재정규화·게이트합니다."
    )
    year = int(st.number_input("타깃 사업연도", min_value=2015, max_value=2030, value=2024, step=1))
    if st.button("수집 후 분석 준비 (DART)"):
        _run_prepare(corp_code, corp_name, year, analysis_window(year))


def render() -> None:
    """분석 리포트 페이지 — 검색 → 상태판정 → 준비 → 온보딩(선택) → 의심건 카드(내부 P1→P2)."""

    inject_css()
    st.title("FS Multi-agents analyzer")

    corp_code = render_company_search()
    if not corp_code:
        return
    corp_name = st.session_state.get("cs_selected_name", "")

    from src.report.prep import company_state, onboarding_done

    state = company_state(corp_code)
    st.html(
        render_selection_html(corp_name, corp_code, state["raw_years"], state["prepared_years"])
    )

    if state["state"] == "A":  # 미수집 — 수집부터
        st.warning("미수집 회사 — DART 수집이 필요합니다(수집 후 재정규화·게이트 자동).")
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

    is_prepared = selected_year in state["prepared_years"]
    key = f"{corp_code}:{selected_year}"
    stages = visible_stages(is_prepared)

    window = analysis_window(selected_year)
    if stages["prepare"]:  # 미준비 — 준비부터(분석 차단)
        st.warning(f"{selected_year}년 아직 미준비 상태입니다.")
        have = ", ".join(str(y) for y in reversed(raw_yrs)) or "없음"
        need = [y for y in window if y not in raw_yrs]
        need_txt = ", ".join(str(y) for y in need) if need else "없음(전부 보유)"
        st.markdown(
            f"**[분석 준비]** 를 누르면 이 회사의 **{window[0]}~{window[-1]} 5개 사업연도**를 "
            "분석 가능한 상태로 만듭니다:\n"
            f"- **DART 수집**: 아직 없는 연도({need_txt}) — 현재 보유: {have}\n"
            "- **재정규화**: 최신 코드로 계정 표준화(연결/별도)\n"
            "- **주석 분류** + **온보딩 게이트**(정규화 품질 검문 G1~G5)\n\n"
            "5개년을 확보해야 전년대비(YoY)·다년 추세 신호가 성립합니다. "
            "없는 연도 수집 시 수 분 걸릴 수 있습니다."
        )
        if st.button("분석 준비"):
            _run_prepare(corp_code, corp_name, selected_year, window)
        return

    st.success(f"{selected_year} 준비완료 — 게이트 PASS")
    # 순서: ① 온보딩 → ② 의심건 카드. 온보딩 완료 전에는 카드 단계를 열지 않는다(안내도 생략).
    _render_onboarding_llm(corp_code, selected_year, key)
    # 온보딩 완료(영속 마커) 또는 이번 세션 실행이면 카드 단계를 연다.
    onboarded = onboarding_done(corp_code, selected_year) or (
        st.session_state.get("rv_onboarding_key") == key
    )
    if onboarded:
        st.markdown("---")
        _render_analysis(corp_code, corp_name, selected_year, window, key)
