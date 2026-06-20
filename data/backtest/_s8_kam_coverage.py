"""S8 확대 측정 — 별첨 감사보고서 KAM이 본문 PART V 대비 얼마나 더 주는가(연도별).

분식 6사 전 분식연도 + 삼성(clean) + 층화 샘플을 document_all로 받아, PART V KAM 유무 vs
별첨 KAM 유무를 분류한다. "별첨에만 KAM" 비율을 연도별로 집계해 경량 KAM 보강의 실효를 본다.
"""

from __future__ import annotations

import json
import random
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import OpenDartReader

from config.settings import settings
from src.notes.report_parts import LOGICAL_PARTS, extract_parts, select_part

random.seed(31)
d = OpenDartReader(settings.dart_api_key)
OUT = Path("data/backtest/_S8_KAM_COVERAGE.md")


def clean(s: object) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", str(s)))


def get_rcept(corp: str, year: int) -> str | None:
    for final in (True, False):
        try:
            lst = d.list(
                corp, start=f"{year + 1}0101", end=f"{year + 1}1231", kind="A", final=final
            )
        except Exception:
            continue
        if lst is None or lst.empty:
            continue
        m = lst[lst["report_nm"].astype(str).str.contains("사업보고서", regex=False)]
        if not m.empty:
            return str(m.sort_values("rcept_dt").iloc[-1]["rcept_no"])
    return None


def measure(corp: str, year: int, tag: str) -> dict | None:
    rc = get_rcept(corp, year)
    if not rc:
        return None
    try:
        da = d.document_all(rc)
        partv = select_part(extract_parts(str(da[0])), LOGICAL_PARTS["감사의견"])
        pv = partv.text if partv else ""
        pv_kam = pv.count("핵심감사사항")
        att_kam = max([clean(x).count("핵심감사사항") for x in da[1:]], default=0)
    except Exception:
        return None
    if pv_kam == 0 and att_kam > 0:
        cls = "별첨에만"
    elif pv_kam > 0:
        cls = "둘다"
    else:
        cls = "둘다없음"
    return {
        "corp": corp,
        "year": year,
        "tag": tag,
        "pv_kam": pv_kam,
        "att_kam": att_kam,
        "cls": cls,
    }


def main() -> None:
    cases = json.loads(Path("data/backtest/known_cases.json").read_text(encoding="utf-8"))["cases"]
    targets: list[tuple[str, int, str]] = []
    for c in cases:
        corp = c.get("corp_code")
        if not corp:
            continue
        tag = c.get("label", "?")
        for y in c.get("run_years", []):
            targets.append((corp, int(y), tag))

    # 층화 샘플: 보유 corpus에서 무작위 corp × 2018~2023 한 해.
    root = settings.data_dir
    corps = sorted(p.name for p in root.iterdir() if p.is_dir() and p.name.isdigit())
    random.shuffle(corps)
    years = [2018, 2019, 2020, 2021, 2022, 2023]
    for i, corp in enumerate(corps[:30]):
        targets.append((corp, years[i % len(years)], "sample"))

    print(f"측정 대상 {len(targets)} 회사연도, document_all 동시 fetch…", flush=True)
    results: list[dict] = []
    with ThreadPoolExecutor(max_workers=6) as ex:
        futs = {ex.submit(measure, c, y, t): (c, y) for c, y, t in targets}
        for fut in as_completed(futs):
            r = fut.result()
            if r:
                results.append(r)
                if len(results) % 10 == 0:
                    print(f"  {len(results)} done", flush=True)

    # 연도별 집계
    by_year: dict[int, dict[str, int]] = {}
    for r in results:
        b = by_year.setdefault(r["year"], {"별첨에만": 0, "둘다": 0, "둘다없음": 0, "n": 0})
        b[r["cls"]] += 1
        b["n"] += 1

    lines = ["# S8 확대 측정 — 별첨 KAM 커버리지(연도별)", ""]
    lines.append(
        f"- 표본 {len(results)} 회사연도(분식 정답지 전 분식연도 + 삼성 clean + 층화 샘플 30)"
    )
    lines.append("")
    lines.append("## 연도별 KAM 보유")
    lines.append("```")
    lines.append(f"{'연도':<6}{'n':>4}{'별첨에만':>9}{'둘다':>7}{'둘다없음':>9}")
    for y in sorted(by_year):
        b = by_year[y]
        lines.append(f"{y:<6}{b['n']:>4}{b['별첨에만']:>9}{b['둘다']:>7}{b['둘다없음']:>9}")
    lines.append("```")
    lines.append("")
    # 분식사 분식연도 상세
    lines.append("## 분식 정답지 — 분식연도별 KAM 위치")
    lines.append("```")
    lines.append(f"{'corp':<10}{'year':>6}{'tag':>10}{'PV_KAM':>8}{'별첨_KAM':>9}  {'판정'}")
    for r in sorted(
        [x for x in results if x["tag"] == "positive"], key=lambda r: (r["corp"], r["year"])
    ):
        lines.append(
            f"{r['corp']:<10}{r['year']:>6}{r['tag']:>10}{r['pv_kam']:>8}{r['att_kam']:>9}  {r['cls']}"
        )
    lines.append("```")
    lines.append("")
    only = sum(1 for r in results if r["cls"] == "별첨에만")
    only_pos = sum(1 for r in results if r["cls"] == "별첨에만" and r["tag"] == "positive")
    lines.append("## 요약")
    lines.append(f"- 별첨에만 KAM: {only}/{len(results)} (그중 분식연도 {only_pos})")
    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"\n[완료] {len(results)}건, 별첨에만 KAM {only}(분식 {only_pos}) → {OUT}", flush=True)


if __name__ == "__main__":
    main()
