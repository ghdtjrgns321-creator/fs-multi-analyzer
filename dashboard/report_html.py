"""분석 리포트 순수 HTML 렌더 — Streamlit 런타임 없이 테스트 가능한 str 함수들.

AccountFinding 객체와 dict 둘 다 받는다(_get: getattr 우선 → .get).
포지셔닝 원칙: 부정 확정 표현 금지 — '의심 후보'·'검토 관심' 톤 유지(PLAN §15).
"""

from __future__ import annotations

import html
from typing import Any

# 큐는 상위만 카드로(전체는 결정론 markdown 리포트 몫) — 표시 개수는 프레젠테이션 상수.
QUEUE_TOP_LIMIT = 10
# 반박 판정 라벨(card_report.py와 동일 어휘). None이면 '반박 미수행' 명시(빈칸 숨김 금지 §9).
VERDICT_LABELS = {
    "normal_dominant": "정상설명 우세",
    "mixed": "반반",
    "suspicion_dominant": "의심 우세",
}
# 카드 본문 4요소 — 모든 Finding은 반대근거·정상설명·확인질문·다음절차를 포함(포지셔닝 원칙).
BODY_SECTIONS = [
    ("counter_evidence", "숫자상 반대 가능성"),
    ("normal_explanation", "정상일 수 있는 설명"),
    ("confirm_question", "확인 질문"),
    ("next_procedure", "다음 절차"),
]


def _get(obj: Any, key: str, default: Any = None) -> Any:
    """객체(getattr 우선)·dict(.get) 양쪽에서 필드를 읽는다."""

    if hasattr(obj, key):
        return getattr(obj, key)
    if isinstance(obj, dict):
        return obj.get(key, default)
    return default


def _esc(value: Any) -> str:
    return html.escape(str(value if value is not None else ""))


def _fmt_num(value: Any) -> str:
    try:
        return f"{float(value):,.2f}"
    except (TypeError, ValueError):
        return "-"


def _risk_pill(level: Any) -> str:
    css = {"High": "high", "Medium": "medium", "Low": "low"}.get(str(level), "low")
    return f'<span class="drv-pill drv-pill-{css}">{_esc(level or "Low")}</span>'


def render_selection_html(
    company_name: str, corp_code: str, raw_years: list[int], prepared_years: list[int]
) -> str:
    """회사 선택 헤더 — 회사명·코드 + raw/준비완료 연도를 배지로 나란히 표시."""

    raw_badges = (
        "".join(f'<span class="drv-badge-year">{_esc(y)}</span>' for y in reversed(raw_years))
        or '<span class="drv-kv">없음</span>'
    )
    prep_badges = (
        "".join(f'<span class="drv-badge-year">{_esc(y)}</span>' for y in reversed(prepared_years))
        or '<span class="drv-kv">없음</span>'
    )
    return (
        '<div class="drv-header">'
        f'<div class="drv-row"><span class="drv-title">{_esc(company_name)}</span>'
        f'<span class="drv-chip">{_esc(corp_code)}</span></div>'
        f'<div class="drv-row" style="margin-top:6px;">'
        f'<span class="drv-kv">raw 보유</span>{raw_badges}'
        "</div>"
        f'<div class="drv-row" style="margin-top:4px;">'
        f'<span class="drv-kv">준비완료</span>{prep_badges}'
        "</div>"
        "</div>"
    )


def render_header_html(company_name: str, target_year: Any, review_scope: dict) -> str:
    """회사명 타이틀 + 연도 배지 + 검토범위 캡션(+커버리지 경고 배지)."""

    scope = review_scope or {}
    unaccounted = int(scope.get("unaccounted_cells", 0) or 0)
    # 근본구조 C: 이유 없이 빠진 셀 >0이면 '위험 없음' 둔갑 금지 — 경고 배지로 표면화.
    warn = (
        f'<span class="drv-warn">커버리지 경고 — 미분석 셀 {unaccounted}건</span>'
        if unaccounted
        else ""
    )
    return (
        '<div class="drv-header">'
        f'<div class="drv-row"><span class="drv-title">{_esc(company_name)}</span>'
        f'<span class="drv-badge-year">{_esc(target_year)} 사업연도</span>{warn}</div>'
        f'<div class="drv-caption">검토 범위: 계정 {int(scope.get("accounts_reviewed", 0) or 0)}개 · '
        f"관점 {int(scope.get('perspectives_run', 0) or 0)}개</div>"
        "</div>"
    )


def render_queue_html(items: list[dict]) -> str:
    """검토 우선순위 큐 — 상위 항목 카드. 빈 리스트면 안내 문구(hollow 방지)."""

    title = '<div class="drv-section-title">검토 우선순위 큐</div>'
    if not items:
        return title + (
            '<div class="drv-empty">검토 큐 항목 없음 — '
            "결정론 신호에서 우선 검토 후보가 산출되지 않았다.</div>"
        )
    rows = []
    for idx, item in enumerate(items[:QUEUE_TOP_LIMIT], start=1):
        basis = " · ".join(str(b) for b in (_get(item, "audit_basis") or []))
        rows.append(
            '<div class="drv-card">'
            f'<div class="drv-row"><span class="drv-rank">{idx}</span>'
            f'<span class="drv-strong">{_esc(_get(item, "subject"))}</span>'
            f'<span class="drv-chip">{_esc(_get(item, "item_type"))}</span>'
            f"{_risk_pill(_get(item, 'risk_level'))}"
            f'<span class="drv-kv">score {_fmt_num(_get(item, "materiality_score"))}</span></div>'
            f'<div class="drv-caption">{_esc(_get(item, "issue"))} — '
            f"핵심 근거: {_esc(_get(item, 'key_evidence'))}</div>"
            f'<div class="drv-kv">{_esc(basis)}</div>'
            "</div>"
        )
    return title + "".join(rows)


def render_ratio_html(ratio_summary: dict) -> str:
    """카테고리(수익성·활동성·안정성·이익의 질)별 지표 카드 grid."""

    title = '<div class="drv-section-title">회사 전체 지표 요약</div>'
    if not ratio_summary:
        return title + '<div class="drv-empty">표시할 비율 지표 없음.</div>'
    cards = []
    for category, values in ratio_summary.items():
        cells = (
            "".join(
                f'<div class="drv-metric"><div class="drv-metric-name">{_esc(name)}</div>'
                f'<div class="drv-metric-value">{_fmt_num(value)}</div></div>'
                for name, value in (values or {}).items()
            )
            or '<div class="drv-empty">지표 없음</div>'
        )
        cards.append(
            f'<div class="drv-card"><div class="drv-sub">{_esc(category)}</div>'
            f'<div class="drv-grid">{cells}</div></div>'
        )
    return title + "".join(cards)


def render_card_html(card: Any) -> str:
    """의심 후보 카드 1개 — 헤더(계정·전기값·유형) + 배지 + 본문 4요소 리스트."""

    prior_value, prior_year = _get(card, "prior_value"), _get(card, "prior_year")
    prior = (
        f' <span class="drv-kv">(전기 {_esc(prior_year or "?")}: {_esc(prior_value or "?")})</span>'
        if (prior_value or prior_year)
        else ""
    )
    issue_raw = _get(card, "issue_type")
    issue = str(getattr(issue_raw, "value", issue_raw) or "")
    subtype = str(_get(card, "subtype") or "")
    if subtype:  # '기타' 유형은 값만으론 무의미 — subtype 병기(#14).
        issue = f"{issue}({subtype})"
    vote = f"표수 {int(_get(card, 'vote_count') or 0)}/{int(_get(card, 'internal_total') or 0)}"
    verdict = VERDICT_LABELS.get(str(_get(card, "rebuttal_verdict") or ""), "반박 미수행")
    chips = "".join(
        f'<span class="drv-chip">{_esc(b)}</span>' for b in (_get(card, "reference_badges") or [])
    )
    related = _get(card, "related_accounts") or []
    related_html = (
        f'<div class="drv-kv">관련 계정: {_esc(" ↔ ".join(str(a) for a in related))}</div>'
        if related
        else ""
    )
    body = []
    for key, label in BODY_SECTIONS:
        entries = _get(card, key) or []
        if entries:
            lis = "".join(f"<li>{_esc(e)}</li>" for e in entries)
            body.append(f'<div class="drv-sub">{label}</div><ul class="drv-list">{lis}</ul>')
    body_html = "".join(body) or '<div class="drv-empty">세부 근거 목록 없음</div>'
    return (
        '<div class="drv-card">'
        f'<div class="drv-row"><span class="drv-strong">{_esc(_get(card, "account"))}</span>{prior}'
        f'<span class="drv-chip">{_esc(issue)}</span></div>'
        f'<div class="drv-row"><span class="drv-chip">{vote}</span>'
        f"{_risk_pill(_get(card, 'risk_level'))}"
        f'<span class="drv-chip">{_esc(verdict)}</span>{chips}</div>'
        f"{related_html}{body_html}</div>"
    )


def render_cards_section_html(title: str, cards: list) -> str:
    """섹션 제목 + 카드들. 빈 섹션도 '0건'을 명시한다(빈화면 금지 §9)."""

    header = f'<div class="drv-section-title">{_esc(title)}</div>'
    if not cards:
        return header + '<div class="drv-empty">이 섹션에서 제기된 의심 후보 0건.</div>'
    return header + "".join(render_card_html(card) for card in cards)
