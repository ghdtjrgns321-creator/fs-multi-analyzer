"""실 LLM Phase2 E2E 측정 — 비용 + 사각 3종 카드화 관측.

근본구조(OFS·주석전량·SCE·occurrence·중립라벨) 후 처음으로 실 6관점+반박에 태운다.
온보딩(S7)은 재실행 안 함(이미 done) — Phase2만. 단가가정 $2.5/$10·₩1380(gpt-5.4 실단가 미확정).
실행: uv run python data/backtest/_e2e_phase2_live.py
산출물: _E2E_PHASE2_LIVE.md
"""

from __future__ import annotations

import asyncio
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pydantic_ai

USD_IN, USD_OUT, PERM, KRW = 2.5, 10.0, 1_000_000, 1380
CASES = [("00126380", "삼성전자"), ("00112457", "대주산업")]

_orig_run = pydantic_ai.Agent.run
USAGE: list[dict] = []
_STAGE = {"name": "?"}


def _cost(inp: int, out: int) -> float:
    return ((inp * USD_IN + out * USD_OUT) / PERM) * KRW


def _usage_of(result):
    u = getattr(result, "usage", None)
    return u() if callable(u) else u


def _extract(usage) -> tuple[int, int]:
    inp = getattr(usage, "request_tokens", None) or getattr(usage, "input_tokens", None) or 0
    out = getattr(usage, "response_tokens", None) or getattr(usage, "output_tokens", None) or 0
    return int(inp), int(out)


async def _patched(self, *a, **k):
    t0 = time.perf_counter()
    result = await _orig_run(self, *a, **k)
    inp, out = _extract(_usage_of(result))
    USAGE.append(
        {"stage": _STAGE["name"], "in": inp, "out": out, "s": round(time.perf_counter() - t0, 1)}
    )
    return result


pydantic_ai.Agent.run = _patched

from src.report.card_pipeline import build_suspicion_cards  # noqa: E402
from src.report.company_report import build_company_report  # noqa: E402

# 사각 마커 — grounded 의심건/카드 텍스트에서 관측(정규식 아닌 부분일치)
BLIND = {
    "note 특수관계자": ["특수관계"],
    "note 지급보증/약정/우발": ["지급보증", "보증", "약정", "우발", "소송"],
    "SCE 자기주식/자본거래": ["자기주식", "자본", "배당", "증자"],
}


def _scan(grounded) -> dict:
    hits: dict[str, int] = {k: 0 for k in BLIND}
    occ = {"appeared": 0, "disappeared": 0, "resumed": 0}
    for g in grounded:
        text = f"{g.item.account_id or ''} {g.item.description or ''} {g.item.cited_value or ''}"
        for label, kws in BLIND.items():
            if any(kw in text for kw in kws):
                hits[label] += 1
        for state in occ:
            if state in text:
                occ[state] += 1
    return {"blind": hits, "occurrence_mention": occ}


def main() -> None:
    out: list[str] = [
        "# 실 LLM Phase2 E2E — 비용 + 사각 카드화",
        "",
        "단가가정 $2.5/1M(입력)·$10/1M(출력)·₩1,380/$ (gpt-5.4 실단가 미확정).",
    ]
    for corp, name in CASES:
        USAGE.clear()
        _STAGE["name"] = name
        report = build_company_report(
            corp_code=corp, company_provider=lambda c, n=name: {"stock_name": n, "corp_code": c}
        )
        note_n = len(report.get("note_facts", []))
        sce_n = len(report.get("sce_cells", []))
        series_n = len(report.get("account_level_series", []))
        t0 = time.perf_counter()
        result = asyncio.run(build_suspicion_cards(report, run_llm=True))
        elapsed = time.perf_counter() - t0

        tin = sum(u["in"] for u in USAGE)
        tout = sum(u["out"] for u in USAGE)
        cost = _cost(tin, tout)
        acc = result.get("account_cards", [])
        comp = result.get("company_cards", [])
        grounded = [g for g in result.get("grounded", []) if g.grounded]
        dropped = result.get("dropped", [])
        scan = _scan(result.get("grounded", []))

        out.append("")
        out.append(f"## {name} ({corp}) target={report['target_year']}")
        out.append(f"- 입력: series {series_n} · note_facts {note_n} · sce_cells {sce_n}")
        out.append(
            f"- **총 비용 ₩{cost:,.0f}** (입력 {tin:,} · 출력 {tout:,} 토큰 · 호출 {len(USAGE)}회 · {elapsed:.0f}초)"
        )
        out.append(
            f"- 카드: 계정 {len(acc)} · 회사 {len(comp)} / grounded {len(grounded)} · dropped {len(dropped)}"
        )
        out.append("- 관점별 토큰:")
        for u in USAGE:
            out.append(
                f"    in={u['in']:>8,} out={u['out']:>6,} ₩{_cost(u['in'], u['out']):>7,.0f} ({u['s']}s)"
            )
        out.append(f"- 사각 관측(grounded 의심건 언급 건수): {scan['blind']}")
        out.append(f"- occurrence 언급: {scan['occurrence_mention']}")
        out.append("- 계정 카드 상위:")
        for c in acc[:12]:
            sub = f"/{c.subtype}" if getattr(c, "subtype", None) else ""
            out.append(
                f"    {c.account} | {c.issue_type.value}{sub} | 표수 {c.vote_count}/{c.internal_total} | {c.risk_level}"
            )
        out.append("- 회사 카드:")
        for c in comp:
            sub = f"/{c.subtype}" if getattr(c, "subtype", None) else ""
            out.append(
                f"    {c.account} | {c.issue_type.value}{sub} | 표수 {c.vote_count}/{c.internal_total}"
            )

    text = "\n".join(out)
    path = Path(__file__).parent / "_E2E_PHASE2_LIVE.md"
    path.write_text(text, encoding="utf-8")
    print(text)
    print(f"\n[written] {path}")


if __name__ == "__main__":
    main()
