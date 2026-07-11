"""의심건 카드 대형 렌더 — 3섹션 통일: ①주장 ②결과 분해(표·근거) ③시각자료.

카드 타입별 맞는 차트(dataviz 폼 규칙): 분해 카드=워터폴(변동 기여), 관계 카드=지수화
라인+괴리 음영(벌어짐), 일반 계정=추이 바+YoY% 라벨(급변 맥락). 데이터 가공은
card_data(순수), 여기는 st.*·plotly 조립만.
"""

from __future__ import annotations

from typing import Any

import plotly.graph_objects as go
import streamlit as st

from dashboard.card_data import (
    _get,
    claim_lines,
    evidence_rows,
    fmt_krw,
    index_points,
    legs_top,
    review_point,
    series_points,
    split_series_key,
    waterfall_leaves,
    yoy_labels,
)

# 반박 4요소(원 주장 아래 접기로). report_html의 BODY_SECTIONS 어휘 계승.
REBUTTAL_SECTIONS = [
    ("counter_evidence", "숫자상 반대 가능성"),
    ("normal_explanation", "정상일 수 있는 설명"),
    ("confirm_question", "확인 질문"),
    ("next_procedure", "다음 절차"),
]
VERDICT_LABELS = {
    "normal_dominant": "정상설명 우세",
    "mixed": "반반",
    "suspicion_dominant": "의심 우세",
}
# 추이 차트: 같은 슬레이트 계열 강조(과거 연함→당기 진함, 순차 강조 — 범주색 아님).
TREND_BASE, TREND_TARGET = "#CBD5E1", "#334155"
# 관계 차트 4색 — dataviz reference palette 슬롯1~4, validator PASS(CVD ΔE 24.2).
LEG_COLORS = ["#2a78d6", "#1baf7a", "#eda100", "#008300"]
# 워터폴 극성(증가/감소) + 합계 — 범주색과 분리(polarity 규칙).
WF_UP, WF_DOWN, WF_TOTAL = "#1baf7a", "#e34948", "#334155"
_CHART_FONT = dict(family='system-ui, -apple-system, "Segoe UI", sans-serif', color="#64748B")


def _chart_layout(fig: go.Figure, height: int) -> go.Figure:
    fig.update_layout(
        height=height,
        margin=dict(l=8, r=8, t=8, b=8),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=_CHART_FONT,
        showlegend=False,
    )
    fig.update_xaxes(type="category", showgrid=False, tickfont=dict(size=11))
    # y축 눈금 숫자 숨김 — 막대에 억/조 직접 라벨이 있어 "500G" 축은 노이즈(recessive axes).
    fig.update_yaxes(
        showgrid=True,
        gridcolor="#EEF2F6",
        zeroline=True,
        zerolinecolor="#CBD5E1",
        showticklabels=False,
    )
    return fig


def trend_figure(points: list[dict], target_year: int) -> go.Figure:
    """계정 추이 막대 — 당기 진한 색 + 값 라벨, 나머지 막대엔 전년비 % 라벨(급변 위치 즉독)."""

    years = [str(p["year"]) for p in points]
    amounts = [p["amount"] for p in points]
    colors = [TREND_TARGET if p["year"] == target_year else TREND_BASE for p in points]
    yoy = yoy_labels(points)
    texts = [
        fmt_krw(p["amount"]) if p["year"] == target_year else yoy[i] for i, p in enumerate(points)
    ]
    fig = go.Figure(
        go.Bar(
            x=years,
            y=amounts,
            marker_color=colors,
            text=texts,
            textposition="outside",
            textfont=dict(size=11, color="#475569"),
            hovertemplate="%{x}년 %{y:,.0f}원<extra></extra>",
        )
    )
    return _chart_layout(fig, height=250)


def legs_figure(rows: list[dict], legs: list[str]) -> go.Figure:
    """관계 카드 — 다리를 첫 관측=100 지수화한 라인. 2다리면 사이를 음영해 '벌어짐'을 강조."""

    fig = go.Figure()
    indexed: list[tuple[str, list[dict]]] = []
    for leg in legs:
        pts = index_points(series_points(rows, leg))
        if pts:
            _, name = split_series_key(leg)
            indexed.append((name, pts))
    for idx, (name, pts) in enumerate(indexed):
        # 2다리 괴리 음영: 두 번째 trace에 fill='tonexty'(첫 trace와의 사이).
        fill = "tonexty" if (len(indexed) == 2 and idx == 1) else None
        fig.add_trace(
            go.Scatter(
                x=[str(p["year"]) for p in pts],
                y=[p["amount"] for p in pts],
                mode="lines+markers",
                name=name,
                line=dict(color=LEG_COLORS[idx % len(LEG_COLORS)], width=2),
                marker=dict(size=8),
                fill=fill,
                fillcolor="rgba(42,120,214,0.08)",
                hovertemplate=name + " %{x}년 지수 %{y:.0f}<extra></extra>",
            )
        )
    _chart_layout(fig, height=270)
    # 지수 라인은 y값(100=첫해)이 의미라 눈금 유지(막대 직접라벨과 다름).
    fig.update_yaxes(tickformat=".0f", showticklabels=True, tickfont=dict(size=10))
    fig.update_layout(
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, font=dict(size=11)),
    )
    return fig


def contribution_figure(out: dict) -> go.Figure:
    """분해 카드 — 요인별 기여를 0기준 좌우 발산 가로막대. 왼쪽(빨강)=하락, 오른쪽(초록)=방어.

    워터폴(누적 브릿지)은 큰 감소가 위에 떠 증가처럼 보여 오독됐다. 이 카드의 일은 '극성'(무엇이
    끌어내리고 무엇이 방어)이라 dataviz 발산 막대가 직독된다. 크기순 정렬 + 억/조 직접 라벨.
    """

    leaves = [(name, d) for name, d in waterfall_leaves(out) if d]  # 0 기여는 제외
    # 토네이도 정렬 — 크기(절대값) 오름차순: plotly가 아래→위로 그리므로 최대 기여가 맨 위에 온다.
    leaves.sort(key=lambda x: abs(x[1]))
    names = [name for name, _ in leaves]
    deltas = [d for _, d in leaves]
    colors = [WF_DOWN if d < 0 else WF_UP for d in deltas]
    texts = [f"{fmt_krw(d)}원" for d in deltas]
    fig = go.Figure(
        go.Bar(
            x=deltas,
            y=names,
            orientation="h",
            marker=dict(color=colors, line=dict(width=0), cornerradius=4),
            text=texts,
            textposition="outside",
            textfont=dict(size=11, color="#475569"),
            cliponaxis=False,
            hovertemplate="%{y}: %{x:,.0f}원<extra></extra>",
        )
    )
    fig.update_layout(
        height=max(160, 56 + 44 * len(names)),
        margin=dict(l=8, r=8, t=8, b=8),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=_CHART_FONT,
        showlegend=False,
        bargap=0.45,  # 막대 얇게 — dataviz: 막대가 슬롯을 꽉 채우지 않게(여백 유지)
    )
    # 0 기준선 강조(발산 중심). x 눈금 숨김 + automargin으로 좌우 라벨 클립 방지.
    fig.update_xaxes(
        showgrid=False,
        zeroline=True,
        zerolinecolor="#94A3B8",
        zerolinewidth=1,
        showticklabels=False,
        automargin=True,
    )
    fig.update_yaxes(showgrid=False, tickfont=dict(size=11, color="#334155"))
    return fig


def _header(card: Any) -> None:
    fs_label, name = split_series_key(str(_get(card, "account") or ""))
    title = f"{name}" + (f" <span class='drv-chip'>{fs_label}</span>" if fs_label else "")
    score = float(_get(card, "priority_score") or 0.0)
    # 우측 배지는 연속 점수 하나만 — 등급 라벨은 폐지(근거 없는 라벨이 가장 눈에 띄던 문제③).
    st.html(
        '<div class="drv-row" style="justify-content:space-between;">'
        f'<span class="drv-card-title">{title}</span>'
        f'<span class="drv-pill">우선순위 {score:.2f}</span>'
        "</div>"
    )


def _claims_block(card: Any) -> None:
    st.markdown("**① 무엇이 의심스러운가**")
    lines = claim_lines(card)
    if not lines:
        st.caption("관점 주장 원문 없음(집계 이전 카드).")
        return
    for line in lines:
        # 인용 수치(12자리 원숫자) 접미 제거 · 관점 라벨은 굵은 말머리로(가독).
        st.markdown(f"- **[{line['perspective']}]** {line['description']}")


def _decomposition_table(out: dict) -> None:
    """ "왜 움직였나" 분해 표(재귀 들여쓰기·잔차 정직 표시)."""

    _, parent_name = split_series_key(str(out["parent"]))
    # 얼마→얼마·변동은 표 첫 행("전체")에 이미 있다 — 서문 반복 금지(사용자 지적).
    st.markdown(f"**왜 움직였나 — {parent_name}**")

    pct_values: list[float | None] = []  # 기여율 셀 색(방향×강도) 계산용 — 표 행과 1:1

    def _row(r: dict, indent: str = "") -> dict:
        delta = r.get("delta")
        arrow = "▼ " if (delta or 0) < 0 else ("▲ " if (delta or 0) > 0 else "")
        pct_values.append(r.get("contribution_pct"))
        return {
            "구성": indent + str(r["account"]),
            f"{out['prior_year']}": fmt_krw(r["prior"]) if r["prior"] is not None else "결측",
            f"{out['year']}": fmt_krw(r["current"]) if r["current"] is not None else "결측",
            "기여(Δ)": fmt_krw(delta) if delta is not None else "-",
            # 증감 방향을 기여율에 살짝 표기(▼=끌어내림, ▲=방어) — 표만 훑어도 방향 즉독.
            "기여율": (
                f"{arrow}{r['contribution_pct']}%" if r["contribution_pct"] is not None else "-"
            ),
        }

    # 최상단에 분해 대상 자신의 값을 명시(얼마→얼마) — 구성만 나열하고 본체를 숨기지 않는다.
    pct_values.append(None)  # 전체 행은 기준선 — 무색
    table = [
        {
            "구성": f"{parent_name} (전체)",
            f"{out['prior_year']}": fmt_krw(out["parent_prior"]),
            f"{out['year']}": fmt_krw(out["parent_current"]),
            "기여(Δ)": fmt_krw(out["delta"]),
            "기여율": "100%",
        }
    ]

    def _append_rows(rows: list[dict], depth: int) -> None:
        indent = "└ " * depth
        for r in rows:
            table.append(_row(r, indent=indent))
            if r.get("children"):
                _append_rows(r["children"], depth + 1)
            child_resid = r.get("child_residual")
            if child_resid is not None and r.get("delta") and abs(child_resid / r["delta"]) > 0.005:
                pct_values.append(None)
                table.append(
                    {
                        "구성": "└ " * (depth + 1) + "(하위 미설명)",
                        f"{out['prior_year']}": "",
                        f"{out['year']}": "",
                        "기여(Δ)": fmt_krw(child_resid),
                        "기여율": "-",
                    }
                )

    _append_rows(out["rows"], depth=0)
    # 미설명 잔차는 숨기지 않는다(커버리지 원장 원칙) — 0이어도 0으로 명시.
    pct_values.append(None)  # 잔차 행 무색
    table.append(
        {
            "구성": "미설명 잔차",
            f"{out['prior_year']}": "",
            f"{out['year']}": "",
            "기여(Δ)": fmt_krw(out["residual"]),
            "기여율": f"{out['residual_pct']}%" if out["residual_pct"] is not None else "-",
        }
    )
    # 기여율 강약을 색 농도로(빨강=끌어내림/초록=방어, |기여율| 비례) — pandas Styler.
    import pandas as pd

    from dashboard.card_data import contribution_cell_style

    frame = pd.DataFrame(table)
    styles = [contribution_cell_style(p) for p in pct_values]
    styled = frame.style.apply(lambda _col: styles, subset=["기여율"])
    st.dataframe(styled, width="stretch", hide_index=True)
    if out["residual_pct"] is not None and abs(out["residual_pct"]) > 20:
        st.caption(
            f"⚠ 분해 불충분 — 미설명 잔차 {out['residual_pct']}%. "
            "이 회사의 손익 구조가 표준 항등식과 달라 구성 일부를 설명하지 못했습니다."
        )


def _analysis_block(card: Any, decomposition: dict | None) -> None:
    """② 결과 분해 — 변동 분해 표 + (분해와 안 겹치는) 근거 수치 + 외부 검증 결과."""

    from dashboard.card_data import decomposition_accounts

    st.markdown("**② 결과 분해**")
    shown = False
    if decomposition is not None:
        _decomposition_table(decomposition)
        shown = True
    # 분해 표가 이미 보여준 계정의 근거는 재나열 금지(같은 숫자 두 번 대기 = 노이즈).
    rows = evidence_rows(card, exclude_accounts=decomposition_accounts(decomposition))
    if rows:
        st.markdown("추가 근거 수치 (실측 대조 — 분해 표 밖 항목)")
        st.dataframe(rows, width="stretch", hide_index=True)
        shown = True
    _external_block(card)
    if not shown:
        st.caption("분해 가능한 소계 아님 · 추가 근거 수치 없음.")


def _external_block(card: Any) -> None:
    """외부 검증 결과 3분기 — 근거 있음 / 검색했으나 미발견 / 미수행(상위 카드만 검색)."""

    external = _get(card, "external_evidence") or []
    checked = bool(_get(card, "external_checked"))
    if external:
        st.markdown("외부 근거 (타깃 검색)")
        for item in external:
            summary = str(_get(item, "summary") or "")
            url = str(_get(item, "url") or "")
            source = str(_get(item, "source") or "출처")
            link = f" — [{source}]({url})" if url else ""
            st.markdown(f"- {summary}{link}")
    elif checked:
        st.caption("외부 근거 미발견 — 타깃 검색을 수행했으나 출처 있는 관련 보도·공시 없음.")
    else:
        st.caption(
            "외부 검증 미수행 — 조사 미해결·우선순위 상위 카드에만 타깃 검색을 겁니다"
            "(대상 수는 config/investigation.yaml external.top_n)."
        )


def _chart_block(
    card: Any, series_rows: list[dict], target_year: int, decomposition: dict | None
) -> None:
    """③ 시각자료 — 카드 타입별 맞는 폼: 분해=기여 발산막대 / 관계=지수화+괴리 / 계정=추이 바."""

    st.markdown("**③ 시각자료**")
    related = _get(card, "related_accounts") or []
    account_key = str(_get(card, "account") or "")
    if decomposition is not None:
        st.caption("요인별 기여 — 왼쪽(빨강)=하락 요인, 오른쪽(초록)=방어 요인")
        st.plotly_chart(contribution_figure(decomposition), width="stretch")
        return
    if related:
        legs = legs_top(related, series_rows)
        if any(series_points(series_rows, leg) for leg in legs):
            st.caption("지수화 추이(첫해=100) — 선이 벌어질수록 관계 괴리")
            st.plotly_chart(legs_figure(series_rows, legs), width="stretch")
        else:
            st.caption("다리 계정 시계열 없음.")
        return
    points = series_points(series_rows, account_key)
    if points:
        st.caption("추이 — 진한 막대=분석 연도, 라벨=전년비")
        st.plotly_chart(trend_figure(points, target_year), width="stretch")
    else:  # 회사 전체 카드 등 — 시계열 없는 카드는 차트 생략(빈 차트 금지)
        st.caption("단일 계정 시계열 없음(회사 전체 이슈).")


def _conclusion_block(card: Any) -> None:
    """조사 결론 — 카드의 '그래서 뭐가 문제인가'를 맨 위에(문제② 결론 주체)."""

    from dashboard.card_data import conclusion_view

    view = conclusion_view(card)
    if view is None:
        st.caption("조사 미수행 — LLM 미실행 또는 실패(결론 없음을 숨기지 않음).")
        return
    st.markdown(f"🧭 **결론** — {view['headline']}")
    if view["cause_path"]:
        st.markdown("원인 경로")
        st.markdown("\n".join(f"{i}. {s}" for i, s in enumerate(view["cause_path"], 1)))
    if view["anomaly_points"]:
        st.markdown("이상 지점")
        st.markdown("\n".join(f"- {s}" for s in view["anomaly_points"]))
    if view["open_questions"]:
        st.markdown("남은 확인사항")
        st.markdown("\n".join(f"- {s}" for s in view["open_questions"]))
    # 경로·완결 캡션은 시스템 내부 정보라 감사인에게 무의미 — 표시하지 않는다(사용자 결정).


def _card_body(card: Any, series_rows: list[dict], target_year: int, decomposition) -> None:
    """카드 본문 — 조사 결론 → 검토 포인트 → ①주장 → ②결과 분해 → ③시각자료 → 반박 접기."""

    _conclusion_block(card)
    # 두괄식 — "떨어졌다"가 아니라 "왜 비정상인가"(괴리·주도요인)를 첫 줄에 찍는다.
    point = review_point(decomposition, series_rows)
    if point:
        st.markdown(f"🔎 **검토 포인트** — {point}")
    _claims_block(card)
    _analysis_block(card, decomposition)
    _chart_block(card, series_rows, target_year, decomposition)
    _rebuttal_block(card)  # 카드가 expander 단추라 중첩 expander 불가 — 일반 섹션


def render_suspicion_card(card: Any, series_rows: list[dict], target_year: int) -> None:
    """카드 1장(전폭, 단독 렌더용) — 헤더 + 본문."""

    from src.report.decomposition import decompose_change

    with st.container(border=True):
        _header(card)
        account_key = str(_get(card, "account") or "")
        decomposition = decompose_change(series_rows, account_key, target_year)
        _card_body(card, series_rows, target_year, decomposition)


def _rebuttal_block(card: Any) -> None:
    """④ 반박·확인 절차 — 카드 자체가 expander라 중첩 불가, 일반 섹션으로 렌더."""

    st.markdown("**④ 반박·확인 절차**")
    empty = True
    for key, label in REBUTTAL_SECTIONS:
        entries = _get(card, key) or []
        if entries:
            empty = False
            st.markdown(f"{label}")
            st.markdown("\n".join(f"- {e}" for e in entries))
    if empty:
        st.caption("반박 세부 목록 없음.")


def _card_expander(card: Any, series_rows: list[dict], target_year: int, bridges: dict) -> None:
    """카드 1장 단추(접힘) — 라벨 = 계정 + 핵심 한 줄 + 지적 관점 배지(빽빽함 방지)."""

    from dashboard.card_data import card_label, perspective_badge
    from src.report.decomposition import decompose_change

    account_key = str(_get(card, "account") or "")
    decomposition = decompose_change(series_rows, account_key, target_year, bridges)
    fs_label, name = split_series_key(account_key)
    fs_tag = f" ({fs_label})" if fs_label else ""
    # 배지는 "누가 지적했나"(수치·추세 의심) — 표수 숫자보다 읽힌다(사용자 피드백).
    badge = perspective_badge(card)
    badge_tag = f" · :blue[{badge}]" if badge else ""
    # 라벨 본문은 완결된 핵심 한 줄(조사원 label > 결정론 검토포인트) — 중간 절단 금지.
    label = f"**{name}{fs_tag}** — {card_label(card, decomposition, series_rows)}{badge_tag}"
    with st.expander(label, expanded=False):
        _card_body(card, series_rows, target_year, decomposition)


def render_cards_section(
    title: str,
    cards: list,
    series_rows: list[dict],
    target_year: int,
    grouped: bool = False,
) -> None:
    """섹션 제목 + 카드 단추 목록(접힘) — 눌러야 본문이 열린다(개요→상세).

    grouped=True(계정 섹션): 넓은 주제 그룹(config/card_groups.yaml)이 1차 구조,
    그룹 안은 표수→점수 순(card_data.group_cards). False: 점수 정렬 단일 목록(기존).
    빈 섹션도 0건 명시(§9).
    """

    from dashboard.card_data import group_cards, sort_cards
    from src.report.decomposition import load_bridges

    st.markdown(f"#### {title}")
    if not cards:
        st.caption("이 섹션에서 제기된 의심 후보 0건.")
        return
    bridges = load_bridges()
    if grouped:
        for group_label, group in group_cards(cards):
            st.markdown(f"##### {group_label}")
            for card in group:
                _card_expander(card, series_rows, target_year, bridges)
        return
    for card in sort_cards(cards):
        _card_expander(card, series_rows, target_year, bridges)
