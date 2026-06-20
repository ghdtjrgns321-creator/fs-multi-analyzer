"""S7 대표본 실측: 서식버전 분포 + 시대인식 다중패턴 selector 정착률 + 동시fetch 처리속도.

①FORMULA-VERSION으로 서식 버전이 실제 몇 개인지(시대 매핑이 2개로 충분한가)
②논리섹션별 다중패턴(시대 매핑)으로 정착률이 단일키워드 대비 오르는가
③ThreadPool 동시fetch throughput → 전수 시간/비용 추정
"""

from __future__ import annotations

import json
import random
import re
import sys
import time
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import OpenDartReader

from config.settings import settings

random.seed(11)
dart = OpenDartReader(settings.dart_api_key)
root = settings.data_dir
RESULT = Path("data/backtest/_S7_VERSION_PROBE.md")

# 논리 섹션 → 다중 패턴(시대 매핑). any 패턴이 TITLE에 있으면 정착.
LOGICAL = {
    "주석": ["재무제표 주석", "재무제표에 대한 주석"],
    "감사의견": ["감사의견"],
    "거래내용": ["대주주 등과의 거래", "이해관계자와의 거래", "특수관계자와의 거래"],
    "우발부채": ["우발부채", "우발채무"],
    "종속회사": ["연결대상 종속회사", "종속기업 현황", "연결대상 회사", "타법인출자"],
    "자금조달": ["자금조달", "증권의 발행"],
    "제재": ["제재"],
}
VER_RE = re.compile(r'<FORMULA-VERSION[^>]*ADATE="(\d+)"[^>]*>([\d.]+)</FORMULA-VERSION>')
TITLE_RE = re.compile(r"<TITLE[^>]*>(.*?)</TITLE>", re.S)
ROMAN = re.compile(r"^(I|II|III|IV|V|VI|VII|VIII|IX|X|XI|XII)[.\s]")


def list_reports(corp: str) -> list[tuple[str, int]]:
    try:
        lst = dart.list(corp, start="2010-01-01", end="2024-12-31", kind="A")
    except Exception:
        return []
    if lst is None or not len(lst):
        return []
    out = []
    for _, r in lst[lst["report_nm"].astype(str).str.contains("사업보고서")].iterrows():
        m = re.search(r"\((\d{4})\.\d{2}\)", str(r["report_nm"]))
        if m:
            out.append((str(r["rcept_no"]), int(m.group(1))))
    return out


def probe(rcept: str, fy: int) -> dict:
    try:
        xml = str(dart.document(rcept))
    except Exception as exc:
        return {"fy": fy, "status": "FAIL", "err": str(exc)[:40]}
    vm = VER_RE.search(xml)
    version = f"{vm.group(2)}@{vm.group(1)}" if vm else "?"
    titles = [re.sub(r"<[^>]+>", "", t).strip() for t in TITLE_RE.findall(xml)]
    n_roman = sum(1 for t in titles if ROMAN.match(t))
    found = {}
    for sec, pats in LOGICAL.items():
        found[sec] = any(any(p in t for p in pats) for t in titles)
    return {"fy": fy, "status": "OK", "version": version, "n_roman": n_roman, "found": found}


def main() -> None:
    n_target = int(sys.argv[1]) if len(sys.argv) > 1 else 400
    workers = int(sys.argv[2]) if len(sys.argv) > 2 else 8
    corps = sorted(d.name for d in root.iterdir() if d.is_dir() and d.name.isdigit())
    random.shuffle(corps)

    # rcept 후보 모으기(동시 list)
    print(f"corpus {len(corps)}사 → 동시 list로 사업보고서 후보 수집…", flush=True)
    cands: list[tuple[str, int]] = []
    t0 = time.perf_counter()
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(list_reports, c): c for c in corps[:600]}
        for fut in as_completed(futs):
            cands.extend(fut.result())
            if len(cands) >= n_target * 3:
                break
    random.shuffle(cands)
    cands = cands[:n_target]
    print(
        f"후보 {len(cands)} (list {time.perf_counter() - t0:.0f}s). document 동시fetch 시작…",
        flush=True,
    )

    results = []
    t1 = time.perf_counter()
    done = 0
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = [ex.submit(probe, rc, fy) for rc, fy in cands]
        for fut in as_completed(futs):
            results.append(fut.result())
            done += 1
            if done % 50 == 0:
                el = time.perf_counter() - t1
                print(f"  {done}/{len(cands)}  {el:.0f}s  ({done / el:.1f} doc/s)", flush=True)
    fetch_s = time.perf_counter() - t1

    ok = [r for r in results if r["status"] == "OK"]
    fail = [r for r in results if r["status"] == "FAIL"]
    vers = Counter(r["version"] for r in ok)
    cap = {sec: sum(1 for r in ok if r["found"][sec]) for sec in LOGICAL}
    # 버전별 섹션 정착률
    by_ver = defaultdict(lambda: defaultdict(int))
    by_ver_n = Counter()
    for r in ok:
        by_ver_n[r["version"]] += 1
        for sec, v in r["found"].items():
            if v:
                by_ver[r["version"]][sec] += 1

    rate = done / fetch_s if fetch_s else 0
    lines = ["# S7 서식버전 + 시대인식 selector 정착률 대표본 실측", ""]
    lines.append(f"- 표본 OK {len(ok)} / FAIL {len(fail)}, 동시 {workers} workers")
    lines.append(f"- **document fetch {fetch_s:.0f}s, throughput {rate:.1f} doc/s**")
    lines.append(
        f"- 전수 추정: 5,000 회사연도 ÷ {rate:.1f}/s ≈ **{5000 / rate / 60:.0f}분** (DART 무료, rate limit만)"
    )
    lines.append("")
    lines.append(f"## ★FORMULA-VERSION 분포 (distinct {len(vers)}개)")
    for v, n in vers.most_common():
        lines.append(f"- {v}: {n}건")
    lines.append("")
    lines.append("## 논리섹션 정착률 (시대인식 다중패턴)")
    for sec in LOGICAL:
        lines.append(f"- {sec}: {cap[sec]}/{len(ok)} ({100 * cap[sec] // max(len(ok), 1)}%)")
    lines.append("")
    lines.append("## 버전별 정착률 (시대 매핑 충분성 판정)")
    for v, n in vers.most_common(6):
        secs = " ".join(
            f"{s}={by_ver[v][s]}/{n}"
            for s in ["주석", "감사의견", "거래내용", "우발부채", "종속회사"]
        )
        lines.append(f"- {v} (n={n}): {secs}")
    lines.append("")
    lines.append("## 연도분포")
    lines.append(f"- {dict(sorted(Counter(r['fy'] for r in ok).items()))}")
    RESULT.write_text("\n".join(lines), encoding="utf-8")
    print(
        f"\n[완료] OK={len(ok)} FAIL={len(fail)} versions={len(vers)} rate={rate:.1f}doc/s → {RESULT}",
        flush=True,
    )


if __name__ == "__main__":
    main()
