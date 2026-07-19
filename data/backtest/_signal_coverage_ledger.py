"""신호 정의 커버리지 원장 — 정의가 '실제로 산출되는가'를 코퍼스로 재는 결정론 하니스.

왜 필요한가(F1, 2026-07-19 회고):
  관계사슬 3축을 추가하며 계정명이 사전에 있다는 것만 확인하고 넣었다. G5(dangling)는
  "사전에 이름이 있나"만 보고, Layer B는 "코퍼스 전수 0회인가"만 봐서 둘 다 PASS했다.
  실제로는 4개 중 2개가 0사·1개가 2사로 사문(死文)이었고, 손으로 프로브를 짜기 전까지
  아무도 몰랐다. 신호가 소리 없이 죽는 경로가 측정되지 않는다는 것이 근본 결함이다.

이 원장이 박는 규율(src/report/coverage.py의 계정 셀 원장과 같은 철학, 축만 다르다):
  모집단 = config에 선언된 모든 신호 정의
         = 산출된 정의 + 사유를 단 미실행 정의 + **0사 정의(사문)**
  0사 정의가 1건이라도 있으면 FAIL — 조용한 사문을 구조가 숨기지 못하게 한다.

임계로 자르지 않는다. 저커버리지는 차단이 아니라 수치로 게시한다(등급 컷 금지와 같은 규율).
판정은 "0사인가"만 본다 — 자의적 임계 없이 사문만 잡는다.

사용:
  uv run python data/backtest/_signal_coverage_ledger.py [--sample N] [--json PATH]
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

import duckdb
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.analysis_tools.data import load_normalized_financials  # noqa: E402
from src.report.decomposition import decompose_change, load_bridges  # noqa: E402
from src.signals.mvp1 import build_mvp1_signal_report  # noqa: E402
from src.signals.ratios import build_ratio_report  # noqa: E402
from src.signals.red_flags import extract_red_flags  # noqa: E402

BASE = ROOT / "data" / "companies"
CHAINS = ROOT / "config" / "playbooks" / "relationship_chains.yaml"
DECOMP = ROOT / "config" / "decomposition.yaml"


def deferred_ids() -> set[str]:
    """config가 사유를 달아 '계산하지 않는다'고 선언한 정의 — 사문이 아니라 사유 있는 제외.

    예: ROI는 공시 기본 합계 계정에 투자원가가 없어 deferred_ratios에 사유와 함께 선언돼 있다.
    선언된 제외를 사문으로 잡으면 원장이 거짓 경보를 낸다.
    """

    rc = yaml.safe_load(CHAINS.read_text(encoding="utf-8"))
    out: set[str] = set()
    for item in rc.get("l2_mvp1", {}).get("deferred_ratios", []) or []:
        name = str(item.get("name", "")).strip()
        if name:
            out.add(name.lower())
    return out


def declared_definitions() -> dict[str, list[str]]:
    """모집단 — config가 선언한 신호 정의 전수(분모). 손으로 세지 않는다."""

    rc = yaml.safe_load(CHAINS.read_text(encoding="utf-8"))
    l2 = rc.get("l2_mvp1", {})
    thresholds = l2.get("signal_thresholds", {})
    bridges = load_bridges(DECOMP)
    return {
        "growth_divergence": [d["id"] for d in l2.get("growth_divergences", [])],
        "direction_check": [d["id"] for d in l2.get("direction_checks", [])],
        "direction_red_flag": [r["id"] for r in thresholds.get("direction_red_flags", [])],
        "decomposition_bridge": sorted(bridges),
        "financial_ratio": [r["id"] for r in _ratio_ids()],
        # 관계사슬(문서 축)은 코드가 읽지 않는다 — 사유를 단 미실행으로 분류한다.
        "relationship_chain(문서축·미실행)": [c["id"] for c in rc.get("relationship_chains", [])],
    }


def _ratio_ids() -> list[dict]:
    path = ROOT / "config" / "playbooks" / "financial_ratios.yaml"
    return yaml.safe_load(path.read_text(encoding="utf-8")).get("ratios", [])


def company_years() -> dict[str, list[int]]:
    out: dict[str, list[int]] = defaultdict(list)
    for corp in sorted(BASE.iterdir()):
        if not corp.is_dir():
            continue
        for year in sorted(corp.iterdir()):
            if (year / "analysis.duckdb").exists():
                try:
                    out[corp.name].append(int(year.name))
                except ValueError:
                    continue
    # YoY·분해는 최소 2개 연도가 필요하다 — 단년 회사는 모집단에서 사유 있는 제외.
    return {c: sorted(ys) for c, ys in out.items() if len(ys) >= 2}


def _has_body(corp: str, year: int) -> bool:
    path = BASE / corp / str(year) / "analysis.duckdb"
    try:
        with duckdb.connect(str(path), read_only=True) as con:
            con.execute("SELECT 1 FROM normalized_financials LIMIT 1").fetchall()
        return True
    except Exception:
        return False


def measure(sample: int) -> dict:
    """정의별 '값이 실제로 산출된 회사 수'를 센다. 빈 스캐폴드 행은 세지 않는다."""

    pool = company_years()
    sampled = dict(list(pool.items())[:sample])
    bridges = load_bridges(DECOMP)
    fired: dict[str, set[str]] = defaultdict(set)
    analysed = 0
    skipped_no_body = 0

    for corp, years in sampled.items():
        if not any(_has_body(corp, y) for y in years):
            skipped_no_body += 1
            continue
        try:
            frame = load_normalized_financials(corp, years)
        except Exception:
            skipped_no_body += 1
            continue
        if frame.empty:
            skipped_no_body += 1
            continue
        analysed += 1
        target = max(years)

        try:
            report = build_mvp1_signal_report(frame)
        except Exception:
            report = {}
        _count_table(report.get("growth_divergences"), "divergence_pp", fired, corp)
        _count_table(report.get("direction_checks"), None, fired, corp)
        # direction_red_flag는 mvp1 리포트가 아니라 red_flags.py가 소비한다 — 실제 소비자로 잰다.
        # (이 경로를 빠뜨려 원장이 정상 정의를 '사문'으로 오판했던 것을 고친 자리다.)
        if report:
            for year in years:
                try:
                    flags = extract_red_flags(report, int(year), include_all=True)
                except Exception:
                    continue
                for flag in flags:
                    # id 형식: "direction:{rule_id}:{year}"
                    parts = str(getattr(flag, "id", "")).split(":")
                    if len(parts) >= 3 and parts[0] == "direction":
                        fired[parts[1]].add(corp)

        try:
            ratios = build_ratio_report(frame, years)
            _count_ratios(ratios, fired, corp)
        except Exception:
            pass

        rows = frame.to_dict("records")
        for row in rows:
            row["series_key"] = f"{row.get('fs_div')}:{row.get('canonical')}"
        for parent in bridges:
            result = decompose_change(rows, f"CFS:{parent}", target, bridges)
            if result is not None:
                fired[parent].add(corp)

    return {
        "sample": len(sampled),
        "analysed": analysed,
        "skipped_no_body": skipped_no_body,
        "pool": len(pool),
        "fired": {k: len(v) for k, v in fired.items()},
    }


def _count_table(table, value_col: str | None, fired: dict, corp: str) -> None:
    """id별로 '실값이 있는 행'이 하나라도 있으면 산출로 센다(빈 스캐폴드 제외)."""

    if not isinstance(table, pd.DataFrame) or table.empty or "id" not in table.columns:
        return
    col = value_col if (value_col and value_col in table.columns) else None
    for ident, group in table.groupby("id"):
        if col is None:
            valued = group.dropna(how="all")
        else:
            valued = group[pd.to_numeric(group[col], errors="coerce").notna()]
        if len(valued):
            fired[str(ident)].add(corp)


def _count_ratios(table, fired: dict, corp: str) -> None:
    if not isinstance(table, pd.DataFrame) or table.empty or "id" not in table.columns:
        return
    col = "value" if "value" in table.columns else None
    for ident, group in table.groupby("id"):
        valued = (
            group[pd.to_numeric(group[col], errors="coerce").notna()]
            if col
            else group.dropna(how="all")
        )
        if len(valued):
            fired[str(ident)].add(corp)


def render(declared: dict[str, list[str]], result: dict) -> tuple[str, bool]:
    fired = result["fired"]
    deferred = deferred_ids()
    analysed = max(result["analysed"], 1)
    lines: list[str] = []
    lines.append("[신호 정의 커버리지 원장]")
    lines.append(
        f"  모집단 회사(2개 연도 이상) {result['pool']} · 표본 {result['sample']}"
        f" · 분석 {result['analysed']} · 본표 부재 제외 {result['skipped_no_body']}"
    )

    dead: list[str] = []
    total_defs = 0
    for kind, ids in declared.items():
        lines.append(f"\n  ── {kind} ({len(ids)}개)")
        if "미실행" in kind:
            lines.append("      사유 있는 미실행 — 코드가 읽지 않는 문서 축(집계 제외)")
            continue
        total_defs += len(ids)
        for ident in ids:
            n = fired.get(ident, 0)
            pct = n / analysed * 100
            if n == 0 and str(ident).lower() in deferred:
                lines.append(f"      [제외] {ident:<44}    — 사유 선언됨(deferred)")
                continue
            if n == 0:
                mark = "사문"
                dead.append(f"{kind}:{ident}")
            elif pct < 15:
                mark = "저커버"
            else:
                mark = "  ok"
            lines.append(f"      [{mark}] {ident:<44} {n:>4}사 ({pct:>4.0f}%)")

    lines.append("")
    lines.append("=" * 72)
    if dead:
        lines.append(f"판정: FAIL — 0사 정의(사문) {len(dead)}/{total_defs}건")
        for d in dead:
            lines.append(f"  ⛔ {d}")
        lines.append("  선언했으나 어느 회사에서도 산출되지 않는다. 정의를 고치거나 제거하라.")
    else:
        lines.append(f"판정: PASS — 사문 0건 / 선언 {total_defs}건")
    return "\n".join(lines), not dead


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample", type=int, default=200, help="측정할 회사 수(기본 200)")
    parser.add_argument("--json", type=Path, default=None, help="결과 JSON 저장 경로")
    args = parser.parse_args()

    declared = declared_definitions()
    result = measure(args.sample)
    text, passed = render(declared, result)
    print(text)
    if args.json:
        args.json.write_text(
            json.dumps({"declared": declared, **result}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
