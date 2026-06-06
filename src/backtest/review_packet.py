"""홀리스틱 리뷰 패킷 생성기.

회사별로 (1) 실제 FS 주요계정·연도별 (2) 회계항등식 (3) 미매핑 강등 계정
(4) 엔진 산출 신호 를 한 블록으로 만든다. Claude·Codex가 동일 패킷을 독립 리뷰한다.

사용:
    uv run python -m src.backtest.review_packet --results data/backtest/backtest_results_mega.jsonl
    uv run python -m src.backtest.review_packet --results ... --start 0 --end 40   # 배치
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from src.analysis_tools import load_normalized_financials

KEY = [
    "자산총계",
    "부채총계",
    "자본총계",
    "매출",
    "매출원가",
    "매출총이익",
    "영업이익",
    "당기순이익",
    "재고자산",
    "매출채권",
    "매입채무",
    "계약자산",
    "계약부채",
    "단기차입금",
    "장기차입금",
    "영업활동현금흐름",
]


def _fs_block(corp_code: str, years: list[int]) -> str:
    f = load_normalized_financials(corp_code, years)
    fsd = "CFS" if (f["fs_div"] == "CFS").any() else "OFS"
    f = f[f["fs_div"] == fsd].copy()
    f["amt"] = pd.to_numeric(f["amount"], errors="coerce")
    yrs = sorted(int(y) for y in f["year"].dropna().unique())
    lines = [f"[재무제표 기준: {fsd}, 단위: 억원]"]

    # 주요계정 (BS 항목은 sj_div=BS만 — 자본변동표 중복 방지)
    for k in KEY:
        sub = f[f["canonical"] == k]
        if k in ("자산총계", "부채총계", "자본총계"):
            sub = sub[sub["sj_div"] == "BS"]
        if sub.empty:
            lines.append(f"  {k:14s}: (canonical 없음)")
            continue
        g = sub.groupby("year")["amt"].sum()
        lines.append(
            f"  {k:14s}: "
            + " ".join(f"{y}:{g.get(str(y), g.get(y, float('nan'))) / 1e8:,.0f}" for y in yrs)
        )

    # 회계 항등식 (BS): 자산 == 부채 + 자본
    lines.append("  [항등식 자산=부채+자본]")
    bs = f[f["sj_div"] == "BS"]
    for y in yrs:
        ya = bs[(bs["canonical"] == "자산총계") & (bs["year"] == str(y))]["amt"].sum()
        yl = bs[(bs["canonical"] == "부채총계") & (bs["year"] == str(y))]["amt"].sum()
        ye = bs[(bs["canonical"] == "자본총계") & (bs["year"] == str(y))]["amt"].sum()
        diff = ya - (yl + ye)
        flag = "  <<불일치!" if ya and abs(diff) / abs(ya) > 0.01 else ""
        lines.append(
            f"     {y}: 자산{ya / 1e8:,.0f} = "
            f"부채{yl / 1e8:,.0f}+자본{ye / 1e8:,.0f} "
            f"(차{diff / 1e8:,.0f}){flag}"
        )

    # 미매핑 강등 material 계정 (자산 5% 이상, 기타 중요 계정)
    last = yrs[-1]
    lf = f[f["year"] == str(last)].copy()
    at = lf[(lf["canonical"] == "자산총계") & (lf["sj_div"] == "BS")]["amt"].abs().max()
    if at and at == at:
        big = lf[(lf["canonical"] == "기타 중요 계정") & (lf["amt"].abs() >= 0.05 * at)]
        big = big.sort_values("amt", key=lambda s: s.abs(), ascending=False)
        downs = [f"{r.label}({r.amt / 1e8:,.0f}억)" for r in big.head(12).itertuples()]
        lines.append(
            f"  [미매핑 강등 material 계정 {last}년 (자산5%+)]: "
            + ("; ".join(downs) if downs else "없음")
        )
    return "\n".join(lines)


def _signal_block(row: dict) -> str:
    scored = [s for s in (row.get("fired_signals") or []) if not s.get("excluded_from_scoring")]
    best: dict[str, dict] = {}
    for s in scored:
        a = s["account"]
        if a not in best or (s.get("normalized_strength") or 0) > (
            best[a].get("normalized_strength") or 0
        ):
            best[a] = s
    track_top = row.get("track_scoring_top") or sorted(
        best.values(), key=lambda s: s.get("normalized_strength") or 0, reverse=True
    )[:12]
    lines = [f"[엔진 신호: 고유계정 {len(best)}개, 두 트랙 게시]"]
    for track, title in [("A", "트랙 A — 규모 계정"), ("B", "트랙 B — 소액 급변")]:
        lines.append(f"  [{title}]")
        scoped = [s for s in track_top if s.get("track") == track]
        if not scoped:
            lines.append("    (없음)")
            continue
        for i, s in enumerate(scoped, 1):
            lines.append(
                f"    {i:2d}. {s['account']} | {s['type']} | "
                f"값={s.get('value')} | 강도={s.get('normalized_strength')} | "
                f"규모비율={_pct(s.get('magnitude_ratio'))} | {s.get('year')}"
            )
    accs = row.get("account_scores") or []
    if accs:
        lines.append(
            "  [분식계정 status]: "
            + ", ".join(f"{a['source']}={a.get('status')}({a.get('rank')})" for a in accs)
        )
    return "\n".join(lines)


def _pct(value: object) -> str:
    if not isinstance(value, int | float):
        return ""
    return f"{float(value) * 100:.2f}%"


def build(results_path: Path, start: int, end: int | None) -> None:
    rows = [
        json.loads(line)
        for line in results_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    rows = [r for r in rows if r.get("corp_code") and (r.get("available_years") or r.get("window"))]
    sl = rows[start:end] if end else rows[start:]
    out = []
    for r in sl:
        yrs = r.get("available_years") or r.get("window") or []
        out.append(
            f"\n{'=' * 70}\n"
            f"■ {r['company']} ({r['corp_code']}) | label={r['label']} | 연도={yrs}\n"
            f"{'=' * 70}"
        )
        try:
            out.append(_fs_block(r["corp_code"], yrs))
        except Exception as exc:
            out.append(f"  [FS 로드 실패: {exc}]")
        out.append(_signal_block(r))
    dst = results_path.parent / f"review_packets_{start}_{end or 'end'}.txt"
    dst.write_text("\n".join(out), encoding="utf-8")
    print(f"{len(sl)}사 패킷 → {dst}")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument(
        "--results", type=Path, default=Path("data/backtest/backtest_results_mega.jsonl")
    )
    p.add_argument("--start", type=int, default=0)
    p.add_argument("--end", type=int, default=None)
    a = p.parse_args()
    build(a.results, a.start, a.end)


if __name__ == "__main__":
    main()
