"""신호 정의 유효성 원장 — '뜨는가'(커버리지)가 아니라 '뜬 게 맞는가'(판별력)를 잰다.

왜 필요한가(F1-b, 2026-07-19):
  커버리지 원장(_signal_coverage_ledger.py)은 정의가 몇 사에서 산출되는지만 본다. 그런데
  모든 회사에서 똑같이 뜨는 신호는 커버리지가 100%여도 판별력이 0이다. 커버리지를 유효성의
  증거로 쓰는 것이 이번 회고의 핵심 실수였다.

무엇을 재나:
  분식 확정 회사연도(labels.csv positive)에서의 발화율 대(對) 대조군 발화율 = lift.
  lift ≈ 1이면 "분식 회사에서도 정상 회사에서도 똑같이 뜬다" → 판별력 없음.
  계정 일치(hit)도 함께 본다 — 라벨이 지목한 계정과 정의가 보는 계정이 겹쳐야 진짜 적중이다.
  매출 급변 신호가 셀트리온(개발비 자산화)에서 떴다면 그건 우연이지 적중이 아니다.

**측정의 한계를 산출물에 박는다(이 하니스의 핵심 규율):**
  - positive 라벨 중 코퍼스 보유분은 소수다. n이 작으면 lift의 신뢰구간이 넓다.
  - 대조군은 '제재 라벨이 없는 회사'일 뿐 정상이 검증된 것이 아니다(unlabeled negative).
  따라서 이 원장은 **판별력이 없는 정의를 걸러내는 용도**이지, 있다고 증명하는 용도가 아니다.
  낮은 lift는 신호가 약하다는 증거지만, 높은 lift는 n이 작아 확정 근거가 못 된다.

사용:
  uv run python data/backtest/_signal_validity_ledger.py [--controls N] [--json PATH]
"""

from __future__ import annotations

import argparse
import csv
import json
import random
import sys
from collections import defaultdict
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.analysis_tools.data import load_normalized_financials  # noqa: E402
from src.signals.mvp1 import build_mvp1_signal_report  # noqa: E402
from src.signals.red_flags import extract_red_flags  # noqa: E402

BASE = ROOT / "data" / "companies"
LABELS = ROOT / "data" / "backtest" / "labels.csv"
CHAINS = ROOT / "config" / "playbooks" / "relationship_chains.yaml"
SEED = 20260719  # 고정 시드 — 대조군 표본이 실행마다 바뀌면 비교가 성립하지 않는다


def load_labels() -> list[dict]:
    with LABELS.open(encoding="utf-8-sig") as fh:
        return list(csv.DictReader(fh))


def corpus_years(corp: str) -> list[int]:
    path = BASE / corp
    if not path.exists():
        return []
    out = []
    for year in path.iterdir():
        if (year / "analysis.duckdb").exists():
            try:
                out.append(int(year.name))
            except ValueError:
                continue
    return sorted(out)


def positive_cases() -> list[dict]:
    """positive 라벨 ∩ 코퍼스 보유. 분식 연도와 지목 계정을 함께 들고 온다."""

    cases = []
    for row in load_labels():
        if row.get("label") != "positive":
            continue
        corp = (row.get("corp_code") or "").strip()
        if not corp:
            continue
        years = corpus_years(corp)
        if not years:
            continue
        try:
            start = int(row["fraud_year_start"])
            end = int(row["fraud_year_end"])
        except (KeyError, TypeError, ValueError):
            continue
        fraud_years = [y for y in years if start <= y <= end]
        if not fraud_years:
            continue
        accounts = [a.strip() for a in (row.get("accounts") or "").split(";") if a.strip()]
        cases.append(
            {
                "corp_code": corp,
                "company": row.get("company", ""),
                "years": years,
                "fraud_years": fraud_years,
                "accounts": accounts,
                "fraud_type": row.get("fraud_type", ""),
            }
        )
    return cases


def control_cases(exclude: set[str], count: int) -> list[dict]:
    """대조군 — 제재 라벨이 없는 코퍼스 회사 무작위 표본(미검증 정상 추정)."""

    pool = []
    for corp in sorted(BASE.iterdir()):
        if not corp.is_dir() or corp.name in exclude:
            continue
        years = corpus_years(corp.name)
        if len(years) >= 2:
            pool.append({"corp_code": corp.name, "company": "", "years": years})
    rng = random.Random(SEED)
    rng.shuffle(pool)
    return pool[:count]


def fired_by_year(corp: str, years: list[int], target_years: list[int]) -> dict[int, set[str]]:
    """target_years **각 연도별로** 산출된 정의 id 집합.

    회사 단위로 집계하면 관측 연도가 많은 쪽이 '한 번이라도 뜰' 확률이 높아져 발화율이
    부풀려진다(분식 라벨은 분식 연도만, 대조군은 전 연도라 대조군이 유리해지는 편향).
    분모를 회사연도로 맞춰야 lift가 성립한다.
    """

    out: dict[int, set[str]] = {int(y): set() for y in target_years}
    try:
        frame = load_normalized_financials(corp, years)
    except Exception:
        return out
    if frame.empty:
        return out
    try:
        report = build_mvp1_signal_report(frame)
    except Exception:
        return out

    for key, value_col in (("growth_divergences", "divergence_pp"), ("direction_checks", None)):
        table = report.get(key)
        if not isinstance(table, pd.DataFrame) or table.empty or "id" not in table.columns:
            continue
        if "year" not in table.columns:
            continue
        years_num = pd.to_numeric(table["year"], errors="coerce")
        for year in out:
            scoped = table[years_num == year]
            if scoped.empty:
                continue
            for ident, group in scoped.groupby("id"):
                if value_col and value_col in group.columns:
                    valued = group[pd.to_numeric(group[value_col], errors="coerce").notna()]
                else:
                    valued = group.dropna(how="all")
                if len(valued):
                    out[year].add(str(ident))

    for year in out:
        try:
            for flag in extract_red_flags(report, int(year), include_all=True):
                parts = str(getattr(flag, "id", "")).split(":")
                if len(parts) >= 3 and parts[0] == "direction":
                    out[year].add(parts[1])
        except Exception:
            continue
    return out


def definition_accounts() -> dict[str, set[str]]:
    """정의 id → 그 정의가 보는 계정 집합(라벨 계정과의 겹침 판정용)."""

    import yaml

    rc = yaml.safe_load(CHAINS.read_text(encoding="utf-8"))
    l2 = rc.get("l2_mvp1", {})
    out: dict[str, set[str]] = {}
    for d in l2.get("growth_divergences", []):
        out[d["id"]] = {d["account_a"], d["account_b"]}
    for d in l2.get("direction_checks", []):
        out[d["id"]] = {d["growth_account"], d["flow_account"]}
    for r in l2.get("signal_thresholds", {}).get("direction_red_flags", []):
        out[r["id"]] = {r["account_a"], r["account_b"]}
    return out


def _overlaps(defined: set[str], labelled: list[str]) -> bool:
    """정의가 보는 계정과 라벨이 지목한 계정이 겹치나(부분 문자열 허용 — 라벨 표기가 자유롭다)."""

    for a in defined:
        for b in labelled:
            if a in b or b in a:
                return True
    return False


def measure(controls: int) -> dict:
    positives = positive_cases()
    exclude = {c["corp_code"] for c in positives} | {
        (r.get("corp_code") or "").strip() for r in load_labels()
    }
    ctrls = control_cases(exclude, controls)
    defs = definition_accounts()

    # 분모는 회사연도 — 관측 연도 수 차이로 생기는 편향을 없앤다.
    pos_fire: dict[str, int] = defaultdict(int)
    pos_hit: dict[str, int] = defaultdict(int)
    pos_cy = 0
    for case in positives:
        by_year = fired_by_year(case["corp_code"], case["years"], case["fraud_years"])
        pos_cy += len(by_year)
        for _year, fired in by_year.items():
            for ident in fired:
                pos_fire[ident] += 1
                if _overlaps(defs.get(ident, set()), case["accounts"]):
                    pos_hit[ident] += 1

    ctl_fire: dict[str, int] = defaultdict(int)
    ctl_cy = 0
    for case in ctrls:
        by_year = fired_by_year(case["corp_code"], case["years"], case["years"])
        ctl_cy += len(by_year)
        for _year, fired in by_year.items():
            for ident in fired:
                ctl_fire[ident] += 1

    return {
        "positives": [
            {k: c[k] for k in ("corp_code", "company", "fraud_years", "fraud_type")}
            for c in positives
        ],
        "n_positive": len(positives),
        "n_control": len(ctrls),
        "pos_company_years": pos_cy,
        "ctl_company_years": ctl_cy,
        "pos_fire": dict(pos_fire),
        "pos_hit": dict(pos_hit),
        "ctl_fire": dict(ctl_fire),
        "definitions": {k: sorted(v) for k, v in defs.items()},
    }


def render(result: dict) -> str:
    npos = max(result["pos_company_years"], 1)
    nctl = max(result["ctl_company_years"], 1)
    lines = ["[신호 정의 유효성 원장 — 판별력]"]
    lines.append(
        f"  positive(분식확정·코퍼스보유) {result['n_positive']}사"
        f" · 분식 회사연도 {result['pos_company_years']}"
    )
    for p in result["positives"]:
        lines.append(f"      {p['company']:<14} {p['fraud_years']} {p['fraud_type']}")
    lines.append(
        f"  대조군(제재라벨 없음·미검증 정상추정) {result['n_control']}사"
        f" · 회사연도 {result['ctl_company_years']}"
    )
    lines.append("")
    lines.append(f"  {'정의':<44} {'분식발화':>8} {'계정적중':>8} {'대조발화':>8} {'lift':>7}")
    rows = []
    for ident in sorted(set(result["pos_fire"]) | set(result["ctl_fire"])):
        pf = result["pos_fire"].get(ident, 0)
        ph = result["pos_hit"].get(ident, 0)
        cf = result["ctl_fire"].get(ident, 0)
        pos_rate = pf / npos
        ctl_rate = cf / nctl
        lift = (pos_rate / ctl_rate) if ctl_rate else (float("inf") if pos_rate else 0.0)
        rows.append((lift, ident, pf, ph, cf, pos_rate, ctl_rate))
    rows.sort(reverse=True)
    for lift, ident, pf, ph, cf, pos_rate, ctl_rate in rows:
        lift_s = "∞" if lift == float("inf") else f"{lift:.2f}"
        mark = "  " if lift >= 1.2 else ("··" if lift >= 0.8 else "▼ ")
        lines.append(
            f"  {mark}{ident:<42} {pf:>3}/{result['pos_company_years']:<4} {ph:>3}건    "
            f"{cf:>4}/{result['ctl_company_years']:<5} {lift_s:>7}"
        )
    lines.append("")
    lines.append("  lift = 분식 회사 발화율 / 대조군 발화율. 1 근처면 판별력이 없다는 뜻이다.")
    lines.append("  계정적중 = 라벨이 지목한 계정과 정의가 보는 계정이 겹친 건수(우연 발화 배제).")
    lines.append("")
    lines.append("  ※ 한계 — 이 표로 '유효하다'를 증명하지 않는다.")
    lines.append(f"     positive n={result['n_positive']}로 신뢰구간이 넓다.")
    lines.append("     대조군은 제재 라벨이 없을 뿐 정상이 검증된 회사가 아니다(unlabeled).")
    lines.append("     낮은 lift는 약함의 증거로 쓰고, 높은 lift는 확정 근거로 쓰지 않는다.")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--controls", type=int, default=40, help="대조군 회사 수(기본 40)")
    parser.add_argument("--json", type=Path, default=None)
    args = parser.parse_args()
    result = measure(args.controls)
    print(render(result))
    if args.json:
        args.json.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
