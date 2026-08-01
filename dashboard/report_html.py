"""분석 리포트 순수 HTML 렌더 — Streamlit 런타임 없이 테스트 가능한 str 함수들.

AccountFinding 객체와 dict 둘 다 받는다(_get: getattr 우선 → .get).
포지셔닝 원칙: 부정 확정 표현 금지 — '의심 후보'·'검토 관심' 톤 유지(PLAN §15).
"""

from __future__ import annotations

import html
from typing import Any

# 큐는 상위만 카드로(전체는 결정론 markdown 리포트 몫) — 표시 개수는 프레젠테이션 상수.
QUEUE_TOP_LIMIT = 10


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


def render_selection_html(company_name: str, corp_code: str) -> str:
    """회사 선택 헤더 — 회사명·코드만.

    raw 보유·준비완료 연도 배지는 뺐다. 내부 상태(수집됨·정규화 최신)를 사용자가 대신
    관리하게 만드는 표시였고, 같은 정보는 [분석 실행] 아래 단계 목록이 대신한다.
    """

    return (
        '<div class="drv-header">'
        f'<div class="drv-row"><span class="drv-title">{_esc(company_name)}</span>'
        f'<span class="drv-chip">{_esc(corp_code)}</span></div>'
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
