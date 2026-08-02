"""L5 대시보드 공용 CSS — shadcn 스타일 (네이비/슬레이트 팔레트, 라운드 카드, pill 칩).

팔레트(k-ifrs-1115 layout.py 참고):
  #0F172A 텍스트 · #334155 강조 · #E2E8F0 테두리 · #64748B 보조 · #F8FAFC 배경
위험도 색: High=붉은계열 / Medium=앰버 / Low=슬레이트 (은은하게, 과하지 않게).
"""

from __future__ import annotations

import html
from contextlib import contextmanager

import streamlit as st

SHADCN_CSS = """
<style>
    /* ── 커스텀 스피너 — reduced-motion 무시(강제 애니메이션) ─────── */
    @keyframes drv-busy-kf { to { transform: rotate(360deg); } }
    .drv-busy {
        display: flex; align-items: center; gap: 8px;
        color: #64748B; font-size: 0.92em; padding: 0.4rem 0;
    }
    .drv-busy-spin {
        width: 16px; height: 16px; flex-shrink: 0;
        border: 2px solid #E2E8F0; border-top-color: #334155;
        border-radius: 50%;
        /* !important — Streamlit·전역 reduced-motion 리셋(animation:none)을 이기고 항상 회전 */
        animation: drv-busy-kf 0.8s linear infinite !important;
    }
    /* ── 본문 폭 — wide 레이아웃을 중앙 정렬·축소해 좌우 여백 확보 ── */
    .block-container, [data-testid="stMainBlockContainer"] {
        max-width: 1000px !important;
        margin: 0 auto !important;
        padding-left: 1.5rem !important;
        padding-right: 1.5rem !important;
        padding-top: 2.5rem !important;
    }

    /* ── 헤더 ─────────────────────────────────────────────── */
    .drv-header {
        padding: 4px 0 12px;
        border-bottom: 1px solid #E2E8F0;
        margin-bottom: 14px;
    }
    .drv-title { font-size: 1.55em; font-weight: 700; color: #0F172A; }
    .drv-badge-year {
        display: inline-block;
        border: 1px solid #E2E8F0; border-radius: 4px;
        padding: 2px 10px; font-size: 0.78em; font-weight: 600;
        color: #334155; letter-spacing: 0.02em;
    }
    .drv-warn {
        display: inline-block;
        background: #FEF2F2; color: #B91C1C;
        border: 1px solid #FECACA; border-radius: 999px;
        padding: 2px 10px; font-size: 0.76em; font-weight: 600;
    }

    /* ── 카드 (라운드8 · hover 트랜지션) ──────────────────── */
    .drv-card {
        background: #FFFFFF;
        border: 1px solid #E2E8F0; border-radius: 8px;
        padding: 12px 16px; margin-bottom: 8px;
        box-shadow: 0 1px 2px rgba(0,0,0,0.04);
        transition: border-color 0.15s, box-shadow 0.15s;
    }
    .drv-card:hover {
        border-color: #CBD5E1;
        box-shadow: 0 2px 6px rgba(0,0,0,0.06);
    }

    /* ── 행·텍스트 ────────────────────────────────────────── */
    .drv-row {
        display: flex; flex-wrap: wrap;
        align-items: center; gap: 0.45rem;
        margin-bottom: 2px;
    }
    .drv-strong { font-weight: 700; color: #0F172A; font-size: 0.95em; }
    .drv-card-title { font-weight: 700; color: #0F172A; font-size: 1.15em; }
    .drv-caption { color: #64748B; font-size: 0.84em; margin-top: 2px; }
    .drv-kv { color: #94A3B8; font-size: 0.8em; }
    .drv-rank { color: #94A3B8; font-size: 0.85em; font-weight: 600; min-width: 1.2em; }
    .drv-section-title {
        font-size: 1.02em; font-weight: 700; color: #334155;
        margin: 16px 0 8px;
    }
    .drv-sub {
        font-size: 0.74em; font-weight: 600; color: #64748B;
        text-transform: uppercase; letter-spacing: 0.05em;
        margin-top: 8px;
    }
    .drv-list { margin: 3px 0 6px 18px; padding: 0; color: #0F172A; font-size: 0.87em; }
    .drv-list li { margin-bottom: 2px; line-height: 1.55; }

    /* ── pill 칩 ─────────────────────────────────────────── */
    .drv-chip {
        display: inline-block;
        background: #FFFFFF; color: #334155;
        border: 1px solid #E2E8F0; border-radius: 999px;
        padding: 1px 10px; font-size: 0.76em; font-weight: 500;
    }
    .drv-pill {
        display: inline-block;
        border-radius: 999px; padding: 1px 10px;
        font-size: 0.74em; font-weight: 600;
    }
    .drv-pill-high   { background: #FEF2F2; color: #B91C1C; border: 1px solid #FECACA; }
    .drv-pill-medium { background: #FFFBEB; color: #B45309; border: 1px solid #FDE68A; }
    .drv-pill-low    { background: #F8FAFC; color: #64748B; border: 1px solid #E2E8F0; }
    .drv-pill-done   { background: #ECFDF5; color: #047857; border: 1px solid #A7F3D0; }

    /* ── 비율 grid ───────────────────────────────────────── */
    .drv-grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
        gap: 8px; margin-top: 6px;
    }
    .drv-metric {
        background: #F8FAFC; border: 1px solid #E2E8F0;
        border-radius: 6px; padding: 8px 10px;
    }
    .drv-metric-name { color: #64748B; font-size: 0.76em; }
    .drv-metric-value { color: #0F172A; font-size: 1.05em; font-weight: 700; }

    /* ── 실행 단계 목록 (분석 실행 버튼 아래) ─────────────── */
    .drv-step {
        display: flex; align-items: baseline; gap: 10px;
        padding: 7px 0; font-size: 0.92em; color: #334155;
    }
    .drv-step + .drv-step { border-top: 1px dashed #E2E8F0; }
    .drv-step-mark { width: 1.1em; flex-shrink: 0; font-weight: 700; }
    .drv-step-done .drv-step-mark { color: #047857; }
    .drv-step-run .drv-step-mark { color: #334155; }
    .drv-step-wait { color: #94A3B8; }
    .drv-step-wait .drv-step-mark { color: #CBD5E1; }
    .drv-step-label { flex: 1; }
    .drv-step-meta { color: #94A3B8; font-size: 0.86em; white-space: nowrap; }
    .drv-note {
        background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px;
        padding: 10px 14px; color: #334155; font-size: 0.88em; margin: 4px 0 10px;
    }

    /* ── 빈 상태 안내 ────────────────────────────────────── */
    .drv-empty {
        background: #F8FAFC;
        border: 1px dashed #CBD5E1; border-radius: 8px;
        padding: 12px 16px; color: #64748B; font-size: 0.88em;
    }
</style>
"""


def inject_css() -> None:
    """shadcn 스타일 CSS를 페이지에 주입한다."""

    st.markdown(SHADCN_CSS, unsafe_allow_html=True)


@contextmanager
def busy(message: str):
    """커스텀 스피너 컨텍스트 — Streamlit 기본 스피너가 OS/브라우저 reduced-motion에서
    멈추는 문제를 회피한다(자체 @keyframes는 reduced-motion 가드가 없어 항상 돈다).
    블록 시작 전에 스피너를 그리고, 끝나면 지운다."""

    placeholder = st.empty()
    placeholder.markdown(
        f'<div class="drv-busy"><span class="drv-busy-spin"></span>{html.escape(message)}</div>',
        unsafe_allow_html=True,
    )
    try:
        yield
    finally:
        placeholder.empty()
