"""온보딩 QA 게이트 러너 — 한 회사연도의 정규화 품질을 결정론 단계(G1~G5)로 검문.

위치: raw 수집 → 정규화 → [이 게이트] → FS 분석. 게이트를 통과해야 분석에 진입한다.
이번 단계는 결정론 floor(G1~G5)와 G6용 LLM 입력 dump 생성까지다(실제 LLM 통독·반복
루프·UI는 R4). 모든 단계는 기존 검사 스크립트의 함수를 **재사용**한다(재구현 금지).

부품(재사용 출처):
  G1 기계검사   ← data/backtest/_p1_company_review.py (스크립트 __main__ 전용 → subprocess
                  실행 후 [기계요약]·BS 항등식 라인 파싱. 로직 재구현 아님, 산출 재사용)
  G2 충돌인벤토리 ← _conflict_canonical_inventory.py:compatible/coarse_category + mapper
                  (회사 스코프로 단일 DB의 id_label_conflict 행만 수집)
  G3 산술검산   ← _is_cf_arithmetic.py:check_company_year(db)  (import 그대로)
  G5 신호무결성 ← _f1_signal_dangling.py:collect_references/canonical_keys (Layer A, 전사 1회)
  G6 dump      ← _p1_company_review.py 전체 출력(LLM 통독 입력 — 실제 호출은 R4)

통과기준(gate_passed): G1 완결성 FAIL 0 + BS 항등식 tol 이내 + G3 경성위반 0 + G5 dangling 0.
G2 충돌·G6 dump는 보고용(최종 판정은 G6 LLM이 R4에서).

실행: PYTHONPATH=. uv run python -m src.normalize.onboarding_gate <corp> <year>
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import duckdb

from data.backtest._conflict_canonical_inventory import coarse_category, compatible
from data.backtest._f1_signal_dangling import (
    GUARDED_ABSENT,
    canonical_keys,
    collect_references,
)
from data.backtest._is_cf_arithmetic import check_company_year
from src.normalize.config import load_canonical_accounts, normalize_label
from src.normalize.mapper import AccountMapper

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "data" / "companies"
P1_REVIEW = ROOT / "data" / "backtest" / "_p1_company_review.py"
DUMP_DIR = ROOT / "data" / "backtest" / "_gate_dumps"
BS_TOL = 1_000_000.0  # BS 항등식 허용오차(100만원 — _is_cf_arithmetic TOL과 동일 철학)


def _db_path(corp_code: str, year: str) -> Path:
    return BASE / corp_code / year / "analysis.duckdb"


def _g1_verdict(
    completeness: str,
    bs_residuals: list,
    bs_breaks: list,
    returncode: int,
    sce_std: str = "OK",
) -> bool:
    """G1 통과 판정(순수). §9 hollow-PASS 차단.

    BS 항등식 검산이 0건이면 '검산 못함'이지 '통과'가 아니다. 자산총계 등 BS 핵심행이
    결손되면 검산행이 0이 되어, 빈 검사가 통과로 둔갑하던 갭(BS 통째 결손도 gate_passed=True).
    검산이 최소 1건은 나와야(bs_residuals 존재) 통과를 인정한다.

    SCE 표준화 사망(sce_std=='FAIL', 전 행 unmatched)도 통과 아님 — sce 행은 있으나 전부
    미분류라 SCE 분석이 무력한데 completeness OK로 통과하던 갭(BS 바닥과 대칭).
    """

    bs_checked = bool(bs_residuals)
    sce_ok = sce_std != "FAIL"
    return (
        (completeness == "OK") and bs_checked and sce_ok and (not bs_breaks) and (returncode == 0)
    )


def run_g1(corp_code: str, year: str) -> dict:
    """G1 기계검사 — _p1_company_review.py를 subprocess로 돌려 산출을 파싱(재구현 아님).

    스크립트가 print하는 [기계요약] 라인(완결성·SCE검산 등)과 §B BS 항등식 '차이 N' 라인을
    파싱한다. dump 전문은 stdout으로 반환해 G6가 재사용한다(이중 실행 방지).
    """
    proc = subprocess.run(  # noqa: S603 (고정 인터프리터·고정 스크립트 경로)
        [sys.executable, str(P1_REVIEW), corp_code, year],
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=str(ROOT),
    )
    out = proc.stdout or ""

    summary = {}
    m = re.search(r"^\[기계요약\] (.+)$", out, re.MULTILINE)
    if m:
        for tok in m.group(1).split():
            if "=" in tok:
                k, _, v = tok.partition("=")
                summary[k] = v

    # BS 항등식: §B의 '... 차이 N' 라인(자산=부채+자본, 유동+비유동=자산) 잔차 수집.
    bs_residuals: list[dict] = []
    for line in out.splitlines():
        if "자산" in line and "차이" in line and ("부채" in line or "비유동" in line):
            mm = re.search(r"차이\s+(-?[\d,]+)\s*$", line.strip())
            if mm:
                resid = int(mm.group(1).replace(",", ""))
                # 표시단위 백만 → 원 환산 후 tol 비교
                bs_residuals.append({"line": line.strip(), "resid_won": resid * 1_000_000})

    completeness = summary.get("완결성", "?")
    bs_breaks = [r for r in bs_residuals if abs(r["resid_won"]) > BS_TOL]
    passed = _g1_verdict(
        completeness, bs_residuals, bs_breaks, proc.returncode, summary.get("SCE표준화", "OK")
    )

    return {
        "passed": passed,
        "bs_checked": bool(bs_residuals),
        "completeness": completeness,
        "sce_check": summary.get("SCE검산", "?"),
        "sce_std": summary.get("SCE표준화", "?"),
        "loss_candidates": summary.get("소실후보", "?"),
        "bs_residuals": bs_residuals,
        "bs_breaks": bs_breaks,
        "returncode": proc.returncode,
        "raw_summary": m.group(1) if m else "",
        "dump_stdout": out,
    }


def run_g2(corp_code: str, year: str, mapper: AccountMapper) -> dict:
    """G2 충돌 인벤토리(회사 스코프) — 이 회사연도 id_label_conflict 행을 수집·4분면 분류.

    _conflict_canonical_inventory.py의 충돌 의미(compatible/coarse_category)를 그대로 재사용.
    corpus 전수 루프 대신 단일 DB만 질의한다(회사 스코프 — corp/year는 데이터 인자).
    """
    db = _db_path(corp_code, year)
    by_id = mapper._by_id
    by_alias = mapper._by_alias
    rows: list[dict] = []
    if db.exists():
        con = duckdb.connect(str(db), read_only=True)
        try:
            recs = con.execute(
                "SELECT sj_div, account_id, label, canonical "
                "FROM normalized_financials WHERE mapping_status = 'id_label_conflict'"
            ).fetchall()
        finally:
            con.close()
        for sj_div, account_id, label, canonical in recs:
            id_acct = by_id.get(str(account_id))
            lbl_acct = by_alias.get(normalize_label(label))
            id_stmt = id_acct.statement if id_acct else ""
            lbl_stmt = lbl_acct.statement if lbl_acct else None
            rows.append(
                {
                    "sj_div": sj_div,
                    "label": label,
                    "id_canonical": id_acct.name if id_acct else canonical,
                    "id_statement": id_stmt,
                    "label_canonical": lbl_acct.name if lbl_acct else None,
                    "label_statement": lbl_stmt,
                    "same_statement": bool(lbl_stmt and id_stmt == lbl_stmt),
                    "cat_id": coarse_category(id_acct.name, id_stmt) if id_acct else "",
                    "cat_label": (coarse_category(lbl_acct.name, lbl_stmt) if lbl_acct else None),
                    "id_compatible": compatible(sj_div, id_stmt),
                    "label_compatible": compatible(sj_div, lbl_stmt or ""),
                }
            )
    same_stmt_diff_cat = [
        r for r in rows if r["same_statement"] and r["cat_label"] and r["cat_id"] != r["cat_label"]
    ]
    return {
        "total_conflicts": len(rows),
        "same_statement_diff_category": len(same_stmt_diff_cat),
        "rows": rows,
        "triage_rows": same_stmt_diff_cat,
    }


def run_g3(corp_code: str, year: str) -> dict:
    """G3 산술검산 — _is_cf_arithmetic.py:check_company_year(db) 그대로 호출(경성 위반만)."""
    db = _db_path(corp_code, year)
    findings = check_company_year(db) if db.exists() else []
    # informational(CF)은 floor 통과 — 경성(정의식 IS) 위반만 게이트 차단.
    hard = [f for f in findings if not f.get("informational")]
    return {"passed": not hard, "hard_violations": hard, "all_findings": findings}


def run_g5() -> dict:
    """G5 신호 무결성 — _f1_signal_dangling.py Layer A(전사 1회, 회사 무관).

    신호엔진 참조 canonical이 config 키에 없으면 즉시 사망(dangling). corpus DB 스캔 불필요한
    Layer A만 본다(Layer B는 corpus 구성 의존이라 게이트 제외 — 원스크립트 판정과 동일).
    """
    refs = collect_references()
    keys = canonical_keys()
    dangling = {n: p for n, p in refs.items() if n not in keys and n not in GUARDED_ABSENT}
    return {"passed": not dangling, "layer_a_dangling": dangling, "ref_count": len(refs)}


def run_g6(g1_result: dict) -> dict:
    """G6 dump 생성 — G1이 subprocess로 받은 _p1_company_review.py 전문을 파일로 저장.

    LLM 통독 입력(_HOLISTIC_AUDIT_PROMPT.md 9렌즈)용. 실제 LLM 호출은 R4. 여기선 dump 경로만.
    """
    return {"dump_path": None, "dump_lines": g1_result.get("dump_stdout", "").count("\n")}


def _currency_ok(currencies) -> bool:
    """통화 단일성 판정(순수). KRW(또는 빈값)만이면 True, 외화(USD 등) 포함이면 False.

    외화재무는 원화 환산 없이 분석하면 환율(~1300배) 오차가 항등식엔 안 잡혀 silent로 통과한다.
    DART는 환율을 안 주므로 환산이 불가·부정확 → 외화재무는 '원화 분석 부적합'으로 차단한다(§9).
    """

    foreign = {str(c).strip().upper() for c in currencies if str(c).strip()} - {"KRW"}
    return not foreign


def run_currency_check(corp_code: str, year: str) -> dict:
    """정규화 DB의 통화 단일성 검사 — 외화재무(비KRW)면 분석부적합으로 차단."""

    db = _db_path(corp_code, year)
    currencies: list = []
    if db.exists():
        with duckdb.connect(str(db), read_only=True) as con:
            currencies = [
                r[0]
                for r in con.execute(
                    "SELECT DISTINCT currency FROM normalized_financials"
                ).fetchall()
            ]
    foreign = sorted({str(c).strip().upper() for c in currencies if str(c).strip()} - {"KRW"})
    return {"passed": _currency_ok(currencies), "currencies": currencies, "foreign": foreign}


def run_gate(corp_code: str, year: str) -> dict:
    """G1~G5 결정론 단계 + 통화검사 + G6 dump를 순차 실행해 gate_report dict를 집계."""
    db = _db_path(corp_code, year)
    if not db.exists():
        return {
            "corp": corp_code,
            "year": year,
            "gate_passed": False,
            "error": f"정규화 DB 없음: {db}",
        }

    mapper = AccountMapper(load_canonical_accounts(ROOT / "config" / "canonical_accounts.yaml"))

    g1 = run_g1(corp_code, year)
    g2 = run_g2(corp_code, year, mapper)
    g3 = run_g3(corp_code, year)
    g5 = run_g5()
    currency = run_currency_check(corp_code, year)

    # G6 dump 파일 기록(G1이 받아온 전문 재사용 — _p1_company_review 이중 실행 안 함)
    DUMP_DIR.mkdir(parents=True, exist_ok=True)
    dump_path = DUMP_DIR / f"{corp_code}_{year}.txt"
    dump_path.write_text(g1.get("dump_stdout", ""), encoding="utf-8")
    g6 = run_g6(g1)
    g6["dump_path"] = str(dump_path)

    gate_passed = bool(g1["passed"] and g3["passed"] and g5["passed"] and currency["passed"])
    return {
        "corp": corp_code,
        "year": year,
        "gate_passed": gate_passed,
        "G1_machine": g1,
        "G_currency": currency,
        "G2_conflicts": g2,
        "G3_arithmetic": g3,
        "G5_signal": g5,
        "G6_dump": g6,
    }


def _print_report(report: dict) -> None:
    corp, year = report["corp"], report["year"]
    print(f"{'=' * 70}")
    print(f"온보딩 QA 게이트 — {corp}/{year}")
    print(f"{'=' * 70}")
    if "error" in report:
        print(f"⛔ {report['error']}")
        print("\n게이트 판정: FAIL (DB 없음 — 정규화부터)")
        return

    g1 = report["G1_machine"]
    g1_tag = "PASS" if g1["passed"] else "FAIL"
    print(f"\n[G1 기계검사] {g1_tag}")
    print(
        f"  완결성={g1['completeness']} SCE검산={g1['sce_check']} "
        f"SCE표준화={g1['sce_std']} 소실후보={g1['loss_candidates']}"
    )
    for r in g1["bs_residuals"]:
        flag = "⛔이탈" if abs(r["resid_won"]) > BS_TOL else "ok"
        print(f"    BS항등식[{flag}]: {r['line']}")
    if g1["bs_breaks"]:
        print(f"  ⛔ BS 항등식 이탈 {len(g1['bs_breaks'])}건(>{int(BS_TOL):,}원)")

    cur = report.get("G_currency", {})
    cur_tag = "PASS" if cur.get("passed", True) else "FAIL"
    if cur.get("foreign"):
        print(
            f"\n[통화 단일성] {cur_tag} — 외화재무 {cur['foreign']}: 원화 환산 불가로 분석 부적합"
        )
    else:
        print(f"\n[통화 단일성] {cur_tag} (KRW)")

    g2 = report["G2_conflicts"]
    print(f"\n[G2 충돌 인벤토리] (보고용) 총 id_label_conflict {g2['total_conflicts']}행")
    print(f"  동일표·범주상이(진짜충돌 후보) {g2['same_statement_diff_category']}건")
    for r in g2["triage_rows"][:10]:
        print(
            f"    · [{r['sj_div']}] id={r['id_canonical']}[{r['cat_id']}] ↔ "
            f"label={r['label_canonical']}[{r['cat_label']}] (raw label={r['label']})"
        )
    if len(g2["triage_rows"]) > 10:
        print(f"    … 외 {len(g2['triage_rows']) - 10}건")

    g3 = report["G3_arithmetic"]
    g3_tag = "PASS" if g3["passed"] else "FAIL"
    print(f"\n[G3 산술검산] {g3_tag} — 경성 위반 {len(g3['hard_violations'])}건")
    for f in g3["hard_violations"]:
        note = f"  [{f['note']}]" if f.get("note") else ""
        print(f"  ✗ {f['fs_div']:3} {f['id']:14} 잔차={f['resid']:+,.0f}{note}")

    g5 = report["G5_signal"]
    g5_tag = "PASS" if g5["passed"] else "FAIL"
    print(f"\n[G5 신호 무결성] {g5_tag} — Layer A dangling {len(g5['layer_a_dangling'])}건")
    for n, prov in g5["layer_a_dangling"].items():
        print(f"  ✗ {n!r}  <- {prov[0] if prov else '?'}")

    g6 = report["G6_dump"]
    print("\n[G6 dump] (LLM 통독 입력, 실제 호출은 R4)")
    print(f"  dump 경로: {g6['dump_path']}  ({g6['dump_lines']}줄)")

    print(f"\n{'=' * 70}")
    verdict = (
        "PASS — FS 분석 진입 가능" if report["gate_passed"] else "FAIL — 이탈 해소 후 재게이트"
    )
    print(f"게이트 판정: {verdict}")
    print(
        "  (통과기준: G1 완결성 OK + BS 항등식 tol 이내 + G3 경성위반 0 + G5 dangling 0. "
        "G2·G6은 보고용 — 최종 판정은 G6 LLM·R4)"
    )


def main() -> None:
    if len(sys.argv) < 3:
        print("사용: python -m src.normalize.onboarding_gate <corp_code> <year>")
        sys.exit(2)
    corp_code, year = sys.argv[1], sys.argv[2]
    report = run_gate(corp_code, year)
    _print_report(report)
    sys.exit(0 if report.get("gate_passed") else 1)


if __name__ == "__main__":
    main()
