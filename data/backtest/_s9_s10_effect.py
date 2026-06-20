"""S9/S10 수집 효과 실측 — 분식 vs 정상 변별력.

S9: 재무제표 정정 재제출(특히 ★과거연도 사업보고서 정정 = 분식 자인 패턴) 발생률을 분식 6사 vs
    정상 표본으로 대조. benign 기재정정과 과거연도 재무정정을 구분(hollow 방지).
S10: 고신호 event(자기주식·유상증자·CB/BW·내부자 소유변동·특수관계 거래) 빈도를 분식 vs 정상 대조.

list만 사용(문서 fetch 없음, 가벼움). 결과 → _S9_S10_EFFECT.md
"""

from __future__ import annotations

import json
import random
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import OpenDartReader

from config.settings import settings

random.seed(41)
d = OpenDartReader(settings.dart_api_key)
OUT = Path("data/backtest/_S9_S10_EFFECT.md")

FS_REPORT = re.compile("사업보고서|반기보고서|분기보고서")
PERIOD = re.compile(r"\((\d{4})\.\d{2}\)")
# S10 고신호 event 유형(시점 있는 결정/거래/내부자).
S10_EVENTS = {
    "자기주식": re.compile("자기주식"),
    "유상증자": re.compile("유상증자|신주발행"),
    "CB/BW": re.compile("전환사채|신주인수권부사채|교환사채"),
    "내부자소유변동": re.compile("임원ㆍ주요주주|특정증권등소유|대량보유|최대주주.*변동"),
    "특수관계거래": re.compile("특수관계인|동일인등출자|계열회사와의"),
    "자산양수도": re.compile("자산양[수도]|영업양[수도]|타법인주식.*(취득|처분)"),
}


def analyze(corp: str, tag: str) -> dict | None:
    try:
        lst = d.list(corp, start="2016-01-01", end="2024-12-31")
    except Exception:
        return None
    if lst is None or lst.empty:
        return None
    fs_corr = 0
    past_year_corr = 0  # ★과거연도 사업보고서 정정(자인)
    event_counts = {k: 0 for k in S10_EVENTS}
    for _, r in lst.iterrows():
        nm = str(r["report_nm"])
        rcept_year = int(str(r["rcept_dt"])[:4])
        if "정정" in nm and FS_REPORT.search(nm):
            fs_corr += 1
            m = PERIOD.search(nm)
            if m and int(m.group(1)) <= rcept_year - 2:
                past_year_corr += 1
        for key, pat in S10_EVENTS.items():
            if pat.search(nm):
                event_counts[key] += 1
    return {
        "corp": corp,
        "tag": tag,
        "n_filings": int(len(lst)),
        "fs_corr": fs_corr,
        "past_year_corr": past_year_corr,
        "events": event_counts,
    }


def main() -> None:
    cases = json.loads(Path("data/backtest/known_cases.json").read_text(encoding="utf-8"))["cases"]
    targets: list[tuple[str, str]] = []
    fraud_corps = set()
    for c in cases:
        corp = c.get("corp_code")
        if not corp:
            continue
        if c.get("label") == "positive":
            targets.append((corp, "분식"))
            fraud_corps.add(corp)
        elif c.get("label") == "clean":
            targets.append((corp, "정상(clean)"))
            fraud_corps.add(corp)

    # 정상 base-rate 표본: corpus 무작위(분식사 제외).
    root = settings.data_dir
    corps = [
        p.name
        for p in root.iterdir()
        if p.is_dir() and p.name.isdigit() and p.name not in fraud_corps
    ]
    random.shuffle(corps)
    for corp in corps[:28]:
        targets.append((corp, "정상(표본)"))

    print(f"분석 {len(targets)}사, list 동시…", flush=True)
    rows: list[dict] = []
    with ThreadPoolExecutor(max_workers=8) as ex:
        futs = {ex.submit(analyze, c, t): c for c, t in targets}
        for fut in as_completed(futs):
            r = fut.result()
            if r:
                rows.append(r)
    print(f"수집 {len(rows)}사", flush=True)

    fraud = [r for r in rows if r["tag"] == "분식"]
    normal = [r for r in rows if r["tag"].startswith("정상")]

    def rate(group, key):
        n = len(group)
        return (sum(1 for r in group if r[key] > 0), n)

    lines = ["# S9/S10 수집 효과 — 분식 vs 정상 변별력 실측", ""]
    lines.append(f"- 표본: 분식 {len(fraud)}사 / 정상 {len(normal)}사(clean+층화)")
    lines.append("")
    lines.append("## S9. 재무 정정 재제출 변별력")
    fc = rate(fraud, "fs_corr")
    nc = rate(normal, "fs_corr")
    fp = rate(fraud, "past_year_corr")
    np_ = rate(normal, "past_year_corr")
    lines.append("```")
    lines.append(f"{'지표':<28}{'분식':>12}{'정상':>12}")
    lines.append(
        f"{'재무 정정 1건이상 보유율':<24}{f'{fc[0]}/{fc[1]}':>12}{f'{nc[0]}/{nc[1]}':>12}"
    )
    lines.append(
        f"{'★과거연도 사업보고서 정정율':<22}{f'{fp[0]}/{fp[1]}':>12}{f'{np_[0]}/{np_[1]}':>12}"
    )
    lines.append("```")
    lines.append("")
    lines.append("## S9. 분식사별 상세")
    lines.append("```")
    lines.append(f"{'corp':<10}{'tag':>10}{'총공시':>8}{'재무정정':>9}{'과거연도정정':>12}")
    for r in sorted(fraud, key=lambda r: -r["past_year_corr"]):
        lines.append(
            f"{r['corp']:<10}{r['tag']:>10}{r['n_filings']:>8}{r['fs_corr']:>9}{r['past_year_corr']:>12}"
        )
    lines.append("```")
    lines.append("")
    lines.append("## S10. 고신호 event 평균 빈도(회사당, 2016~2024 누적)")
    lines.append("```")
    lines.append(f"{'event유형':<16}{'분식평균':>10}{'정상평균':>10}")
    for key in S10_EVENTS:
        fa = sum(r["events"][key] for r in fraud) / max(len(fraud), 1)
        na = sum(r["events"][key] for r in normal) / max(len(normal), 1)
        lines.append(f"{key:<16}{fa:>10.1f}{na:>10.1f}")
    lines.append("```")
    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"[완료] → {OUT}", flush=True)
    print(f"S9 과거연도정정: 분식 {fp[0]}/{fp[1]} vs 정상 {np_[0]}/{np_[1]}", flush=True)


if __name__ == "__main__":
    main()
