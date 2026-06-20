"""S7 검증: 사업보고서 대파트 구조가 회사 불문 표준인지 층화랜덤 50 회사연도로 실증.

연도(포맷 드리프트) 버킷 × corp 다양성으로 표집 → 각 원문 fetch → 대파트 I~XII 수 +
고가치 섹션(주석·대주주거래·우발부채·종속회사·감사의견) TITLE 발견 측정. 어긋남 식별.
"""

from __future__ import annotations

import json
import random
import re
from collections import defaultdict
from pathlib import Path

import OpenDartReader

from config.settings import settings

random.seed(7)  # 재현
dart = OpenDartReader(settings.dart_api_key)
root = settings.data_dir

ROMAN = re.compile(r"^(I|II|III|IV|V|VI|VII|VIII|IX|X|XI|XII)[.\s]")
HOT = ["주석", "대주주", "우발부채", "종속회사", "감사의견"]
RESULT = Path("data/backtest/_S7_STRUCTURE_PROBE.md")


def fiscal_year(report_nm: str) -> int | None:
    m = re.search(r"\((\d{4})\.\d{2}\)", report_nm)
    return int(m.group(1)) if m else None


def collect_candidates(corps: list[str], cap: int = 500) -> list[tuple[str, str, int]]:
    cands: list[tuple[str, str, int]] = []
    for corp in corps:
        try:
            lst = dart.list(corp, start="2016-01-01", end="2024-12-31", kind="A")
        except Exception:
            continue
        if lst is None or not len(lst):
            continue
        rows = lst[lst["report_nm"].astype(str).str.contains("사업보고서")]
        for _, r in rows.iterrows():
            fy = fiscal_year(str(r["report_nm"]))
            if fy:
                cands.append((corp, str(r["rcept_no"]), fy))
        if len(cands) > cap:
            break
    return cands


def stratified_sample(cands: list[tuple[str, str, int]], n: int = 50) -> list[tuple[str, str, int]]:
    buckets: dict[int, list] = defaultdict(list)
    for c in cands:
        buckets[c[2] // 2 * 2].append(c)  # 2년 버킷
    per = max(1, n // max(1, len(buckets)))
    seen_corp: set[str] = set()
    sample: list[tuple[str, str, int]] = []
    for b in sorted(buckets):
        items = buckets[b]
        random.shuffle(items)
        taken = 0
        for it in items:
            if it[0] in seen_corp:  # 회사 중복 줄여 다양성↑
                continue
            sample.append(it)
            seen_corp.add(it[0])
            taken += 1
            if taken >= per + 3:
                break
    random.shuffle(sample)
    return sample[:n]


def probe_one(corp: str, rcept: str, fy: int) -> dict:
    try:
        xml = str(dart.document(rcept))
    except Exception as exc:
        return {"corp": corp, "fy": fy, "status": "FETCH_FAIL", "err": str(exc)[:60]}
    titles = [
        re.sub(r"<[^>]+>", "", t).strip()
        for t in re.findall(r"<TITLE[^>]*>(.*?)</TITLE>", xml, re.S)
    ]
    roman = [t for t in titles if ROMAN.match(t)]
    found = {h: any(h in t for t in titles) for h in HOT}
    return {
        "corp": corp,
        "fy": fy,
        "status": "OK" if len(roman) >= 11 else "DEVIATE",
        "n_roman": len(roman),
        "n_titles": len(titles),
        "found": found,
        "xml_chars": len(xml),
    }


def main() -> None:
    corps = sorted(d.name for d in root.iterdir() if d.is_dir() and d.name.isdigit())
    random.shuffle(corps)
    print(f"corpus {len(corps)}사 → 후보 수집(앞 150사 list)…", flush=True)
    cands = collect_candidates(corps[:150])
    print(
        f"후보 {len(cands)} 회사연도, 연도분포: {dict(sorted({c[2]: 1 for c in cands}.items()))}",
        flush=True,
    )
    sample = stratified_sample(cands, 50)
    print(f"표집 {len(sample)} 회사연도. fetch 시작…", flush=True)

    results = []
    for i, (corp, rcept, fy) in enumerate(sample):
        r = probe_one(corp, rcept, fy)
        results.append(r)
        f = r.get("found", {})
        print(
            f"  {i + 1:2}/{len(sample)} {corp}/{fy} {r['status']} "
            f"roman={r.get('n_roman', '-')} hot={sum(f.values())}/5",
            flush=True,
        )

    ok = [r for r in results if r["status"] == "OK"]
    dev = [r for r in results if r["status"] == "DEVIATE"]
    fail = [r for r in results if r["status"] == "FETCH_FAIL"]
    hot_miss = defaultdict(int)
    for r in ok:
        for h, v in r.get("found", {}).items():
            if not v:
                hot_miss[h] += 1

    lines = ["# S7 사업보고서 구조 표준화 — 층화랜덤 50 검증", ""]
    lines.append(f"- 표본 {len(results)} 회사연도, seed=7 재현")
    lines.append(
        f"- **표준 12파트 부합(roman≥11): {len(ok)} / 이탈: {len(dev)} / fetch실패: {len(fail)}**"
    )
    lines.append(f"- 연도분포: {dict(sorted({r['fy']: 1 for r in results}.items()))}")
    lines.append("")
    lines.append("## 고가치 섹션 TITLE 미발견(부합 표본 중)")
    for h in HOT:
        lines.append(f"- {h}: {hot_miss.get(h, 0)} / {len(ok)} 미발견")
    lines.append("")
    if dev:
        lines.append("## 이탈 회사연도")
        for r in dev:
            lines.append(
                f"- {r['corp']}/{r['fy']}: roman={r.get('n_roman')} titles={r.get('n_titles')}"
            )
    if fail:
        lines.append("## fetch 실패")
        for r in fail:
            lines.append(f"- {r['corp']}/{r['fy']}: {r.get('err')}")
    lines.append("")
    lines.append("## 전체 raw")
    lines.append("```")
    for r in results:
        lines.append(json.dumps(r, ensure_ascii=False))
    lines.append("```")
    RESULT.write_text("\n".join(lines), encoding="utf-8")
    print(f"\n[완료] OK={len(ok)} DEVIATE={len(dev)} FAIL={len(fail)} → {RESULT}", flush=True)


if __name__ == "__main__":
    main()
