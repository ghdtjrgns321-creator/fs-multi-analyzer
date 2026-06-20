"""S7 Step3 — baseline 씨앗용 층화 샘플 수집.

신(2018+)/구(~2017) 시대를 분산해 ~40 회사연도의 사업보고서 원문을 받아, 검토관심
narrative만 골라 파일로 저장한다. 키워드는 사람(Opus)이 이 파일들을 직접 읽어 도출한다
(외부 LLM 호출 없음). 저장: data/backtest/_s7_sample/{corp}_{year}.txt

검토관심 PART(작고 감사 narrative 집중): V 감사의견·IX 계열회사·X 대주주거래·XI 투자자보호 = 전문.
III 재무(주석, 거대)는 발굴 앵커 정규식에 걸리는 단락만 추출(전문 통독 회피).
"""

from __future__ import annotations

import json
import random
import re
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import OpenDartReader

from config.settings import settings
from src.notes.report_parts import extract_parts

random.seed(23)
dart = OpenDartReader(settings.dart_api_key)
ROOT = settings.data_dir
OUT = Path("data/backtest/_s7_sample")
OUT.mkdir(parents=True, exist_ok=True)

# 발굴 앵커(III 주석 단락 선별용) — 넓게 잡아 맥락 노출. 키워드 확정은 사람이 읽어서.
ANCHOR = re.compile(
    "우발|소송|계류|손해배상|담보|보증|약정|특수관계|종속기업|지배력|연결범위|전환사채|"
    "신주인수권|교환사채|손상|계속기업|존속|제재|과징금|벌금|차입|파생|위험회피|"
    "리스|충당부채|약정사항|채무불이행|기한이익"
)
# 검토관심 PART(전문 저장) 논리섹션 → 시대 다중패턴.
FULL_PART_PATTERNS = [
    ["회계감사인의 감사의견", "감사인의 감사의견", "감사의견"],
    ["계열회사"],
    ["대주주 등과의 거래", "이해관계자와의 거래", "특수관계자와의 거래"],
    ["투자자 보호", "그 밖에 투자자"],
    ["재무에 관한 사항"],  # III: 앵커단락만 별도 처리
]


def _rcept(corp: str, year: int) -> str | None:
    try:
        lst = dart.list(corp, start=f"{year + 1}0101", end=f"{year + 1}1231", kind="A", final=True)
    except Exception:
        return None
    if lst is None or lst.empty:
        return None
    m = lst[lst["report_nm"].astype(str).str.contains("사업보고서", regex=False)]
    if m.empty:
        return None
    return str(m.sort_values("rcept_dt").iloc[-1]["rcept_no"])


def _anchor_paragraphs(text: str) -> str:
    """III 재무 주석에서 앵커가 걸리는 줄만 추린다(전문 회피)."""

    return "\n".join(line for line in text.splitlines() if ANCHOR.search(line))


def collect_one(corp: str, year: int) -> dict | None:
    rcept = _rcept(corp, year)
    if rcept is None:
        return None
    try:
        xml = str(dart.document(rcept))
    except Exception:
        return None
    parts = extract_parts(xml)
    if not parts:
        return None

    blocks: list[str] = [f"### CORP {corp}  YEAR {year}  RCEPT {rcept}  PARTS {len(parts)}"]
    for part in parts:
        title = part.title
        is_finance = "재무에 관한 사항" in title
        wanted = any(any(p in title for p in pats) for pats in FULL_PART_PATTERNS)
        if not wanted:
            continue
        body = _anchor_paragraphs(part.text) if is_finance else part.text
        if body.strip():
            blocks.append(f"\n===== PART {part.numeral}. {title} =====\n{body}")

    digest = "\n".join(blocks)
    (OUT / f"{corp}_{year}.txt").write_text(digest, encoding="utf-8")
    era = "old" if year <= 2017 else "new"
    return {
        "corp": corp,
        "year": year,
        "rcept": rcept,
        "era": era,
        "n_parts": len(parts),
        "bytes": len(digest),
    }


def main() -> None:
    n_new = int(sys.argv[1]) if len(sys.argv) > 1 else 28
    n_old = int(sys.argv[2]) if len(sys.argv) > 2 else 12
    workers = 8

    corps = sorted(d.name for d in ROOT.iterdir() if d.is_dir() and d.name.isdigit())
    random.shuffle(corps)

    # 시대 버킷별 후보 (corp, year). 구시대는 회사 존재여부 불확실 → 넉넉히 후보.
    new_targets = [(c, 2022 if i % 2 else 2023) for i, c in enumerate(corps[:120])]
    old_targets = [(c, 2015 if i % 2 else 2016) for i, c in enumerate(corps[120:400])]

    results: list[dict] = []

    def run_bucket(targets: list[tuple[str, int]], need: int) -> None:
        with ThreadPoolExecutor(max_workers=workers) as ex:
            futs = {ex.submit(collect_one, c, y): (c, y) for c, y in targets}
            for fut in as_completed(futs):
                got = fut.result()
                if got:
                    results.append(got)
                    print(
                        f"  ok {got['corp']} {got['year']} {got['era']} {got['bytes']}b", flush=True
                    )
                if (
                    sum(1 for r in results if r["era"] == ("new" if need == n_new else "old"))
                    >= need
                ):
                    break

    print(f"신시대 {n_new}건 수집…", flush=True)
    run_bucket(new_targets, n_new)
    print(f"구시대 {n_old}건 수집…", flush=True)
    run_bucket(old_targets, n_old)

    manifest = {
        "seed": 23,
        "n_total": len(results),
        "n_new": sum(1 for r in results if r["era"] == "new"),
        "n_old": sum(1 for r in results if r["era"] == "old"),
        "items": sorted(results, key=lambda r: (r["era"], r["corp"])),
    }
    (OUT / "_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(
        f"\n[완료] 총 {manifest['n_total']} (신 {manifest['n_new']} / 구 {manifest['n_old']}) → {OUT}",
        flush=True,
    )


if __name__ == "__main__":
    main()
