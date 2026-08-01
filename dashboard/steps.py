"""분석 실행 4단계의 상태 계산 + HTML — Streamlit 런타임 없이 테스트 가능한 순수 함수.

사용자는 [분석 실행] 하나만 누른다. 수집·정규화·본문읽기·교차검증은 버튼이 아니라
진행 표시이며, 이미 끝난 단계는 마커를 보고 건너뛴다(마커 판정은 src/report/prep.py).
"""

from __future__ import annotations

import html

COLLECT = "collect"
NORMALIZE = "normalize"
READ = "read"
CROSS = "cross"

STEP_ORDER = (COLLECT, NORMALIZE, READ, CROSS)
STEP_LABELS = {
    COLLECT: "원본 수집",
    NORMALIZE: "표준 계정 변환 · 품질 검문",
    READ: "사업보고서 본문 읽기 (LLM)",
    CROSS: "멀티 에이전트 교차검증 (LLM)",
}
SKIP = "건너뜀 — 이미 있음"


def build_steps(
    window: list[int],
    missing_years: list[int],
    prepared: bool,
    onboarded_at: str | None,
    cards_at: str | None,
) -> list[dict]:
    """4단계의 done 여부와 부가 설명. 실행 전·실행 후 화면이 같은 목록을 쓴다.

    normalize는 마커가 없으면 window 전체를 다시 변환한다(연도별 부분 건너뛰기 없음,
    prep.prepare_company). 그래서 남은 작업량을 '5개년 전체'로 밝혀 적는다.
    """

    span = f"{window[0]}~{window[-1]}" if window else ""
    need = ", ".join(str(y) for y in missing_years)
    return [
        {
            "key": COLLECT,
            "label": f"{STEP_LABELS[COLLECT]} ({span})" if span else STEP_LABELS[COLLECT],
            "done": not missing_years,
            "meta": SKIP if not missing_years else f"없는 연도 {need}",
        },
        {
            "key": NORMALIZE,
            "label": STEP_LABELS[NORMALIZE],
            "done": prepared,
            "meta": SKIP if prepared else f"{len(window)}개년 전체",
        },
        {
            "key": READ,
            "label": STEP_LABELS[READ],
            "done": bool(onboarded_at),
            "meta": f"건너뜀 — {onboarded_at} 실행" if onboarded_at else "",
        },
        {
            "key": CROSS,
            "label": STEP_LABELS[CROSS],
            "done": bool(cards_at),
            "meta": f"건너뜀 — {cards_at} 실행" if cards_at else "",
        },
    ]


def all_done(steps: list[dict]) -> bool:
    """네 단계가 모두 끝났는지 — 버튼 라벨을 '분석 실행'/'다시 실행'으로 가른다."""

    return all(s["done"] for s in steps)


def render_steps_html(steps: list[dict], running: str | None = None, running_meta: str = "") -> str:
    """단계 목록 HTML.

    running 미지정(실행 전·후) — done이면 ✓, 아니면 ○.
    running 지정(실행 중) — 그 단계는 ●, 앞은 전부 ✓, 뒤는 ○.
    """

    marks = {"done": "✓", "run": "●", "wait": "○"}
    rows, seen = [], False
    for step in steps:
        if running is None:
            state = "done" if step["done"] else "wait"
            meta = step["meta"]
        elif step["key"] == running:
            state, seen = "run", True
            meta = running_meta
        elif not seen:
            state, meta = "done", step["meta"]
        else:
            state, meta = "wait", ""
        rows.append(
            f'<div class="drv-step drv-step-{state}">'
            f'<span class="drv-step-mark">{marks[state]}</span>'
            f'<span class="drv-step-label">{html.escape(step["label"])}</span>'
            f'<span class="drv-step-meta">{html.escape(meta)}</span></div>'
        )
    return "".join(rows)
