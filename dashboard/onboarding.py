"""L5 온보딩 전처리 페이지 — 신규 회사를 Phase1/2 분석에 넣기 전 게이트·이탈등록·재검사.

흐름: corp/year 입력 → [전처리 검사](run_gate) → gate_report 단계별 표시 → 이탈 등록 폼
      (company_quirks.yaml 안전 append) → [재검사] → 통과 시 [Phase1/2 진입] 활성.
온보딩 LLM = S7 청크선별 + 별칭 제안. 감사 소견은 Phase2(의심건 카드)가 전담한다(G6 홀리스틱 제거).
API 미설정 시 안내만(크래시 금지). corp_code/year/계정명은 모두 입력·데이터(하드코딩 금지).

run_gate·load_company_quirks 로직은 재구현하지 않고 호출/로드만 한다.
"""

from __future__ import annotations

from pathlib import Path

import streamlit as st
import yaml

from src.normalize.config import load_company_quirks
from src.normalize.onboarding_gate import run_gate
from src.report.alias_suggest import suggest_aliases

ROOT = Path(__file__).resolve().parents[1]
QUIRKS_PATH = ROOT / "config" / "company_quirks.yaml"


# ──────────────────────────────────────────────────────────────────────────
# quirk 등록 (company_quirks.yaml 안전 append — 작은 파일이라 load→dict 갱신→dump)
# ──────────────────────────────────────────────────────────────────────────
def append_quirk(
    corp_code: str,
    year: str,
    kind: str,
    entry: dict,
    path: Path = QUIRKS_PATH,
) -> dict:
    """이탈 1건을 company_quirks.yaml에 안전 append.

    kind: 'alias_additions' | 'account_overrides'. corp_code/year는 데이터 키(코드 분기 아님).
    파일을 load→해당 corp/year 리스트에 append→dump. UTF-8·allow_unicode로 mojibake 0.
    헤더 주석(파일 상단 안내)은 dump가 지우므로 보존을 위해 원문 주석 블록을 다시 얹는다.
    """

    raw = path.read_text(encoding="utf-8") if path.exists() else ""
    payload = yaml.safe_load(raw) or {}
    quirks = payload.get("company_quirks") or {}

    corp_bucket = quirks.setdefault(str(corp_code), {})
    year_bucket = corp_bucket.setdefault(str(year), {})
    bucket_list = year_bucket.setdefault(kind, [])
    bucket_list.append(entry)
    payload["company_quirks"] = quirks

    # 기존 헤더 주석 보존: dump 전 원문에서 선두 주석 라인을 추출해 다시 얹는다.
    header_lines = []
    for line in raw.splitlines():
        if line.startswith("#"):
            header_lines.append(line)
        else:
            break
    header = ("\n".join(header_lines) + "\n") if header_lines else ""

    body = yaml.safe_dump(payload, allow_unicode=True, sort_keys=False, default_flow_style=False)
    path.write_text(header + body, encoding="utf-8")
    return load_company_quirks(path)


# ──────────────────────────────────────────────────────────────────────────
# S7 Step4 — 사업보고서 원문 통독 → 검토관심 청크 선별(B안) → quirk 캐시
# ──────────────────────────────────────────────────────────────────────────
def run_review_chunk_selection(corp_code: str, year: str) -> dict:
    """원문 수집(Step1)→PART 추출(Step2)→온보딩 LLM 청크선별(Step4)→quirk 캐시.

    선별·판단은 src/report/review_chunks가 한다(여기선 호출만). 실패는 graceful 반환.
    """

    from src.collect.opendart import DartCollector
    from src.notes.report_parts import extract_parts
    from src.report.review_chunks import persist_review_chunks, select_review_chunks

    try:
        collector = DartCollector()
        report = collector.annual_report(corp_code, int(year))
        if report is None:
            return {"status": "absent", "message": "사업보고서 원문 미제공", "selection": None}
        parts = extract_parts(collector.document(report.rcept_no))
    except Exception as exc:  # noqa: BLE001
        return {"status": "error", "message": f"{type(exc).__name__}: {exc}", "selection": None}

    result = select_review_chunks(parts, corp_code, year)
    if result["status"] == "ok" and result["selection"] is not None:
        persist_review_chunks(corp_code, year, result["selection"])
    return result


# ──────────────────────────────────────────────────────────────────────────
# gate_report 렌더링 — 결정론 단계 G1~G5 PASS/FAIL + 이탈 목록
# ──────────────────────────────────────────────────────────────────────────
def _tag(passed: bool) -> str:
    return "✅ PASS" if passed else "⛔ FAIL"


def render_restatement_badge(corp_code: str, year: str) -> None:
    """S9: 이 회사연도 재무가 나중에 재작성된 정정본인지 배지로 표시(데이터 출처).

    corrections.json 미수집이면 표시 생략(graceful). 분식 확정 아님 — 출처 안내.
    """

    from config.settings import settings
    from src.collect.correction import load_corrections, restated_years

    if not load_corrections(corp_code, settings.data_dir):
        return  # 정정 이력 미수집 — 안내 생략
    restated = restated_years(corp_code, settings.data_dir)
    if year.isdigit() and int(year) in restated:
        st.warning(
            f"⚠ 이 연도({year}) 재무제표는 이후 **재작성(정정본)**입니다. "
            "원본이 아니라 고쳐진 숫자일 수 있으니 비교·해석에 주의하세요."
        )
    else:
        others = ", ".join(str(y) for y in sorted(restated))
        note = f" (이 회사 재작성 연도: {others})" if others else ""
        st.caption(f"데이터 출처: 이 연도({year})는 재작성 이력 없음{note}.")


def render_gate_report(report: dict) -> None:
    """run_gate 결과 dict를 단계별 표·이탈목록으로 표시."""

    if "error" in report:
        st.error(f"게이트 실행 불가: {report['error']}")
        return

    overall = report.get("gate_passed", False)
    st.subheader(f"게이트 판정: {_tag(overall)}")

    g1 = report.get("G1_machine", {})
    with st.expander(f"G1 기계검사 — {_tag(g1.get('passed', False))}", expanded=True):
        st.write(
            {
                "완결성": g1.get("completeness"),
                "SCE검산": g1.get("sce_check"),
                "SCE표준화": g1.get("sce_std"),
                "소실후보": g1.get("loss_candidates"),
            }
        )
        breaks = g1.get("bs_breaks") or []
        if breaks:
            st.warning(f"BS 항등식 이탈 {len(breaks)}건")
            st.table([{"line": b["line"], "잔차(원)": b["resid_won"]} for b in breaks])

    g2 = report.get("G2_conflicts", {})
    with st.expander(
        f"G2 충돌 인벤토리 (보고용) — id_label_conflict {g2.get('total_conflicts', 0)}행"
    ):
        triage = g2.get("triage_rows") or []
        if triage:
            st.caption(f"동일표·범주상이(진짜충돌 후보) {len(triage)}건")
            st.dataframe(
                [
                    {
                        "표": r["sj_div"],
                        "raw label": r["label"],
                        "id canonical": r["id_canonical"],
                        "label canonical": r["label_canonical"],
                        "cat_id": r["cat_id"],
                        "cat_label": r["cat_label"],
                    }
                    for r in triage
                ],
                use_container_width=True,
            )
        else:
            st.caption("충돌 후보 없음")

    g3 = report.get("G3_arithmetic", {})
    with st.expander(f"G3 산술검산 — {_tag(g3.get('passed', False))}"):
        hard = g3.get("hard_violations") or []
        if hard:
            st.warning(f"경성 위반 {len(hard)}건")
            st.dataframe(hard, use_container_width=True)
        else:
            st.caption("경성 위반 없음")

    g5 = report.get("G5_signal", {})
    with st.expander(f"G5 신호 무결성 — {_tag(g5.get('passed', False))}"):
        dangling = g5.get("layer_a_dangling") or {}
        if dangling:
            st.warning(f"Layer A dangling {len(dangling)}건")
            st.table([{"canonical": n, "참조": (p[0] if p else "?")} for n, p in dangling.items()])
        else:
            st.caption("dangling 없음")

    g6 = report.get("G6_dump", {})
    with st.expander("G6 dump (LLM 통독 입력)"):
        st.write({"dump 경로": g6.get("dump_path"), "줄수": g6.get("dump_lines")})


# ──────────────────────────────────────────────────────────────────────────
# 이탈 등록 폼 — 오매핑(account_override)·미존재(alias_addition)를 quirk로 등록
# ──────────────────────────────────────────────────────────────────────────
# ──────────────────────────────────────────────────────────────────────────
# 별칭 제안기 배선 — LLM이 미매핑 계정에 canonical 후보 제안(제안만), 사람 확인 시에만 등록
# ──────────────────────────────────────────────────────────────────────────
def _register_suggestion(
    corp_code: str, year: str, suggestion, path: Path = QUIRKS_PATH
) -> dict | None:
    """제안 1건을 사람 확인 후 alias_additions로 등록. '기타 중요 계정' 제안은 등록 거부.

    자동적용 금지 원칙: 이 함수는 사람이 버튼을 눌렀을 때만 호출된다(LLM 제안의 자동 기록 아님).
    """

    from src.report.alias_suggest import NO_MATCH

    if suggestion.suggested_canonical == NO_MATCH or not suggestion.suggested_canonical:
        return None
    return append_quirk(
        corp_code,
        year,
        "alias_additions",
        {"canonical": suggestion.suggested_canonical, "alias": suggestion.alias},
        path=path,
    )


def render_alias_suggestions(corp_code: str, year: str) -> None:
    """미매핑 계정에 LLM canonical 제안을 표시하고, 사람이 확인 클릭 시에만 등록."""

    st.markdown("##### 별칭 자동 제안 (LLM — 제안일 뿐, 확인 후 등록)")
    st.caption(
        "무표준코드 미매핑 계정에 canonical 후보를 제안한다. 회계적으로 맞는지 확인 후 등록."
    )
    if st.button("미매핑 계정 별칭 제안 실행", key="alias_suggest_run"):
        result = suggest_aliases(corp_code, int(year))
        if result["status"] == "skipped":
            st.info(result["message"])
        elif result["status"] == "error":
            st.error(f"별칭 제안 LLM 오류(안내만): {result['message']}")
        elif result.get("result") is not None:
            st.session_state["alias_suggestions"] = result["result"].suggestions

    for idx, sug in enumerate(st.session_state.get("alias_suggestions", []) or []):
        from src.report.alias_suggest import NO_MATCH

        col_info, col_btn = st.columns([4, 1])
        with col_info:
            st.write(
                f"**{sug.alias}** ({sug.sj_div}) → `{sug.suggested_canonical}` "
                f"· 신뢰도 {sug.confidence:.2f}"
            )
            if sug.reason:
                st.caption(sug.reason)
        with col_btn:
            disabled = sug.suggested_canonical == NO_MATCH
            if st.button("등록", key=f"alias_reg_{idx}", disabled=disabled):
                reloaded = _register_suggestion(corp_code, year, sug)
                if reloaded is not None:
                    st.success(f"{sug.alias} → {sug.suggested_canonical} 등록 완료")


def render_quirk_form(corp_code: str, year: str) -> None:
    """이탈을 company_quirks.yaml에 등록하는 폼. 두 종류(alias/override)."""

    st.markdown("#### 이탈 등록 (company_quirks.yaml)")
    render_alias_suggestions(corp_code, year)
    quirk_kind = st.radio(
        "등록 종류",
        ["alias_additions (미존재 별칭 추가)", "account_overrides (오매핑 강제 교정)"],
        key="quirk_kind",
    )

    if quirk_kind.startswith("alias_additions"):
        with st.form("alias_form"):
            canonical = st.text_input("canonical (표준 계정명)")
            alias = st.text_input("alias (회사 라벨)")
            submitted = st.form_submit_button("alias 등록")
        if submitted:
            if not (canonical and alias):
                st.error("canonical·alias 모두 입력하세요.")
            else:
                reloaded = append_quirk(
                    corp_code, year, "alias_additions", {"canonical": canonical, "alias": alias}
                )
                st.success(f"등록 완료. 현재 {corp_code}/{year} quirk 재로드:")
                st.json(reloaded.get(corp_code, {}).get(year, {}))
    else:
        with st.form("override_form"):
            account_id = st.text_input("account_id (DART id)")
            label = st.text_input("label (회사 라벨)")
            force_canonical = st.text_input("force_canonical (강제 표준명)")
            reason = st.text_input("reason (사유, 선택)")
            submitted = st.form_submit_button("override 등록")
        if submitted:
            if not (account_id and label and force_canonical):
                st.error("account_id·label·force_canonical 모두 입력하세요.")
            else:
                entry = {
                    "account_id": account_id,
                    "label": label,
                    "force_canonical": force_canonical,
                }
                if reason:
                    entry["reason"] = reason
                reloaded = append_quirk(corp_code, year, "account_overrides", entry)
                st.success(f"등록 완료. 현재 {corp_code}/{year} quirk 재로드:")
                st.json(reloaded.get(corp_code, {}).get(year, {}))


# ──────────────────────────────────────────────────────────────────────────
# 페이지 본체
# ──────────────────────────────────────────────────────────────────────────
def run_full_onboarding(corp_code: str, year: str) -> dict:
    """온보딩 일괄 실행 — 전처리검사(게이트)→S7 청크선별→alias 제안을 순차 실행.

    한 단계 실패가 전체를 막지 않게 각 단계를 graceful 흡수한다(LLM 실패 시 경고 후 사람이 강행).
    alias는 제안만 — 등록/제외는 사람 몫(자동등록 금지 설계 유지).
    G6 홀리스틱 통독은 제거했다 — 감사 소견은 Phase2(의심건 카드)가 전담한다(역할 중복 차단).
    """

    result: dict = {"corp": corp_code, "year": year}

    def _stage(key: str, fn) -> None:
        try:
            result[key] = fn()
        except Exception as exc:  # noqa: BLE001 — 단계 오류를 안내로 흡수하고 다음 단계 계속
            result[key] = {"status": "error", "message": f"{type(exc).__name__}: {exc}"}

    _stage("gate", lambda: run_gate(corp_code, year))
    _stage("review_chunks", lambda: run_review_chunk_selection(corp_code, year))
    _stage("alias", lambda: suggest_aliases(corp_code, int(year)))
    return result


def can_enter_analysis(gate_report: dict, s7_status: str) -> dict:
    """분석 진입 가능 여부 판정(순수). 게이트 미통과면 차단, 통과면 진입 허용.

    S7(청크선별) 실패 시에도 게이트 통과면 진입은 허용하되 needs_override로 경고를 강제한다
    (API 장애로 영구 차단 방지 + silent 누락 금지 §9 — 사람이 확인 후 강행).
    """

    if not gate_report.get("gate_passed"):
        return {"can_enter": False, "needs_override": False, "reason": "결정론 게이트 미통과"}
    if s7_status == "ok":
        return {"can_enter": True, "needs_override": False, "reason": ""}
    # absent(원문없음) vs error(LLM실패)를 status로 구분 노출(§9).
    return {
        "can_enter": True,
        "needs_override": True,
        "reason": f"S7={s7_status or '미실행'} 미완 — 본문 검토관심 공시 누락 가능(사람 확인 후 강행)",
    }


def render() -> None:
    """온보딩 전처리 페이지 렌더링. 상태는 st.session_state로 관리."""

    st.title("신규회사 온보딩 전처리")
    st.caption(
        "Phase1/2 분석 진입 전, 한 번에 [전처리검사+S7 청크선별+별칭 제안]을 실행해 "
        "이탈을 잡고 quirk로 교정한다. 별칭 제안은 사람이 확인 후 등록한다(수 분 소요)."
    )

    col1, col2 = st.columns(2)
    corp_code = col1.text_input("corp_code (8자리)", key="onb_corp").strip()
    year = col2.text_input("year (YYYY)", key="onb_year").strip()

    if st.button("온보딩 일괄 실행 (전처리+S7+별칭)", disabled=not (corp_code and year)):
        with st.spinner(f"{corp_code}/{year} 온보딩 일괄 실행 중..."):
            result = run_full_onboarding(corp_code, year)
        st.session_state["gate_report"] = result.get("gate")
        st.session_state["review_chunks"] = result.get("review_chunks")
        alias_res = result.get("alias") or {}
        if alias_res.get("status") == "ok" and alias_res.get("result") is not None:
            st.session_state["alias_suggestions"] = alias_res["result"].suggestions
        st.session_state["onb_corp_run"] = corp_code
        st.session_state["onb_year_run"] = year

    report = st.session_state.get("gate_report")
    if not report:
        st.info("corp_code·year를 입력하고 [온보딩 일괄 실행]을 누르세요.")
        return

    run_corp = st.session_state.get("onb_corp_run", corp_code)
    run_year = st.session_state.get("onb_year_run", year)

    render_gate_report(report)

    # S9: 데이터 출처(원본/정정본) 배지
    render_restatement_badge(run_corp, run_year)

    # S7 검토관심 청크(일괄 실행에서 채워짐)
    st.markdown("---")
    st.markdown("##### S7 검토관심 청크 (사업보고서 본문 통독)")
    chunks_result = st.session_state.get("review_chunks")
    if chunks_result:
        if chunks_result.get("status") == "ok" and chunks_result.get("selection") is not None:
            sel = chunks_result["selection"]
            usage = chunks_result.get("usage", {})
            st.caption(
                f"토큰 in {usage.get('input_tokens')}·out {usage.get('output_tokens')} / "
                f"{chunks_result.get('latency_s')}s — company_quirks에 캐시됨"
            )
            st.dataframe(
                [
                    {"공시종류": c.disclosure_type, "PART": c.part, "근거": c.evidence}
                    for c in sel.chunks
                ],
                use_container_width=True,
            )
        else:
            st.info(chunks_result.get("message", "S7 미실행"))

    # 별칭 제안 — 사람이 확인 후 등록(자동등록 금지 유지)
    st.markdown("---")
    render_alias_suggestions(run_corp, run_year)

    # 이탈 등록 폼
    st.markdown("---")
    if "error" not in report:
        render_quirk_form(run_corp, run_year)

    # 게이트 재검사(이탈 해소 후) + Phase1/2 진입
    st.markdown("---")
    if st.button("게이트 재검사", disabled=not (run_corp and run_year)):
        with st.spinner(f"{run_corp}/{run_year} 재게이트..."):
            st.session_state["gate_report"] = run_gate(run_corp, run_year)
        st.rerun()

    # 진입 판정: 게이트 통과 + S7 완료. S7 실패는 경고 후 사람이 강행(§9).
    s7_status = (st.session_state.get("review_chunks") or {}).get("status", "")
    verdict = can_enter_analysis(report, s7_status)
    if not verdict["can_enter"]:
        st.button("Phase1/2 분석 진입", disabled=True)
        st.caption(f"진입 불가 — {verdict['reason']}. 이탈 해소 후 [게이트 재검사]로 통과시키세요.")
    elif verdict["needs_override"]:
        st.warning(f"⚠ {verdict['reason']}")
        st.button("경고 확인 후 Phase1/2 강행 진입", type="primary")
    else:
        st.success("게이트 통과 + S7 완료 — Phase1/2 분석 진입 가능.")
        st.button("Phase1/2 분석 진입", type="primary")


def main() -> None:
    st.set_page_config(page_title="온보딩 전처리", layout="wide")
    render()


if __name__ == "__main__":
    main()
