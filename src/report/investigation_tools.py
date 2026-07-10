"""조사원 도구 4종의 결정론 순수 함수 — Agent 등록과 분리해 단위테스트 가능하게 둔다.

LLM은 이 함수들이 반환하는 값 밖의 숫자를 만들 수 없다(투명한 grounding).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from src.report.decomposition import decompose_change


@dataclass
class InvestigationDeps:
    """조사 도구가 읽는 결정론 데이터 묶음 — LLM은 이 밖의 숫자를 만들 수 없다."""

    series_rows: list[dict]
    target_year: int
    bridges: dict = field(default_factory=dict)
    note_facts: list[dict] = field(default_factory=list)


def get_series(deps: InvestigationDeps, series_key: str) -> dict[int, float]:
    out: dict[int, float] = {}
    for r in deps.series_rows:
        if str(r.get("series_key")) == series_key and r.get("amount") is not None:
            out[int(r["year"])] = float(r["amount"])
    return out


def get_decomposition(deps: InvestigationDeps, series_key: str) -> dict | None:
    return decompose_change(deps.series_rows, series_key, deps.target_year, deps.bridges)


def find_notes(deps: InvestigationDeps, keyword: str, limit: int = 20) -> list[dict]:
    kw = str(keyword)
    return [f for f in deps.note_facts if kw in str(f)][:limit]


def top_changes(deps: InvestigationDeps, limit: int = 15) -> list[dict]:
    """target_year 전년비 |Δ| 상위 — '같이 움직인 계정'을 조사원이 훑는 용도."""

    prior_year = deps.target_year - 1
    by_key: dict[str, dict[int, float]] = {}
    for r in deps.series_rows:
        key = str(r.get("series_key"))
        if r.get("amount") is not None:
            by_key.setdefault(key, {})[int(r["year"])] = float(r["amount"])
    rows = [
        {
            "series_key": key,
            "prior": amounts[prior_year],
            "current": amounts[deps.target_year],
            "delta": amounts[deps.target_year] - amounts[prior_year],
        }
        for key, amounts in by_key.items()
        if deps.target_year in amounts and prior_year in amounts
    ]
    return sorted(rows, key=lambda x: abs(x["delta"]), reverse=True)[:limit]


__all__ = [
    "InvestigationDeps",
    "find_notes",
    "get_decomposition",
    "get_series",
    "top_changes",
]
