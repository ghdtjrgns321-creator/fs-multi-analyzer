"""SCE 과수축(뭉개기) 독립 감사 — 우리 검산(grand-total)이 못 보는 masking을 per-component로 잡는다.

배경(2026-06-13 사용자 의심): 라운드마다 FAIL을 없애려 행을 subtotal/restated로 재분류해
검산에서 제외해 왔다. 그 OK가 진짜 균형인지, 진짜 변동을 뭉개 상쇄로 가린 건지는 우리
검산(component_std='-' grand total)으로 확인하면 자기참조다.

독립 오라클: **component(member)별로** 기초[M]+Σrestated[M]+Σleaf_movement[M] = 기말[M] 를
따로 검산한다. 우리 leaf 분류를 쓰되 **grand-total이 아니라 각 자본 구성요소 컬럼에서** 본다.
- leaf로 잘못 남은 subtotal → 그 컬럼에서 leaf_mov 과대 → per-comp FAIL
- subtotal로 잘못 빠진 진짜 변동 → 그 컬럼에서 leaf_mov 과소 → per-comp FAIL
- grand-total에선 +오차/-오차가 상쇄돼 OK여도 per-comp는 못 숨김.

기초/기말 마커(기초자본·자본총계)는 재분류 대상이 아니었으므로 앵커로 안전.
판정: per-comp 잔차 max가 grand-total 잔차보다 유의하게 크면 = masking 후보(우리 OK가 거짓).

실행: PYTHONPATH=. uv run python data/backtest/_sce_overcollapse_audit.py [targets.json ...]
      인자 없으면 known + _round_targets*.json 전수.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import duckdb
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
COMPANIES = PROJECT_ROOT / "data/companies"
BACKTEST = PROJECT_ROOT / "data/backtest"
TOL = 1_000_000  # 1백만원 — 검산 허용오차와 동급(백만 단위 표시)


def audited_targets() -> list[tuple[str, str]]:
    """known positive + 전 라운드 표본 회사연도(중복 제거)."""
    seen: set[tuple[str, str]] = set()
    out: list[tuple[str, str]] = []
    kc = json.load((BACKTEST / "known_cases.json").open(encoding="utf-8"))
    for c in kc["cases"]:
        if c.get("label") == "positive" and c.get("runnable"):
            for y in c.get("run_years", []):
                t = (c["corp_code"], str(y))
                if t not in seen:
                    seen.add(t)
                    out.append(t)
    for p in sorted(BACKTEST.glob("_round_targets*.json")):
        payload = json.load(p.open(encoding="utf-8"))
        for c in payload.get("cases", []):
            for y in c.get("run_years", []):
                t = (c["corp_code"], str(y))
                if t not in seen:
                    seen.add(t)
                    out.append(t)
    return out


def per_component_residual(sce: pd.DataFrame, fs: str) -> tuple[float, float, dict]:
    """(grand_total_잔차, per_component_max잔차, 컬럼별 잔차). 우리 leaf 분류로 member별 검산."""
    g = sce[sce["fs_div"] == fs].copy()
    if g.empty:
        return (0.0, 0.0, {})
    g["amt"] = pd.to_numeric(g["amount"], errors="coerce")
    roles = g["change_role"].astype(str)

    def col_sum(mask: pd.Series, comp: str) -> float:
        sub = g[mask & (g["component_std"].astype(str) == comp)]
        return float(pd.to_numeric(sub["amt"], errors="coerce").dropna().sum())

    components = sorted(set(g["component_std"].astype(str)) - {"-"})
    begin_m = roles == "begin"
    total_m = roles == "total"
    restated_m = roles == "restated_begin"
    leaf_m = roles == "leaf"

    col_resid: dict[str, float] = {}
    for comp in components:
        begin = col_sum(begin_m, comp)
        end = col_sum(total_m, comp)
        restated = col_sum(restated_m, comp)
        leaf = col_sum(leaf_m, comp)
        if begin == 0 and end == 0 and leaf == 0 and restated == 0:
            continue
        resid = (begin + restated + leaf) - end
        if abs(resid) >= TOL:
            col_resid[comp] = resid

    # grand-total('-' 컬럼) 잔차 — 우리 검산이 보는 축
    gt_begin = col_sum(begin_m, "-")
    gt_end = col_sum(total_m, "-")
    gt_restated = col_sum(restated_m, "-")
    gt_leaf = col_sum(leaf_m, "-")
    gt_resid = (gt_begin + gt_restated + gt_leaf) - gt_end if (gt_begin or gt_end) else 0.0

    per_comp_max = max((abs(v) for v in col_resid.values()), default=0.0)
    return (gt_resid, per_comp_max, col_resid)


def main() -> None:
    paths = [Path(a) for a in sys.argv[1:]]
    if paths:
        seen: set = set()
        tgts: list = []
        for p in paths:
            for c in json.load(p.open(encoding="utf-8")).get("cases", []):
                for y in c.get("run_years", []):
                    t = (c["corp_code"], str(y))
                    if t not in seen:
                        seen.add(t)
                        tgts.append(t)
    else:
        tgts = audited_targets()

    print(f"=== SCE 과수축 독립 감사 — {len(tgts)} 회사연도 (per-component vs grand-total) ===")
    masking = []  # 우리 grand-total OK인데 per-comp 깨짐 = 뭉개기 masking 후보
    pipeline_fail = []  # 둘 다 깨짐 = 검산이 정직하게 FAIL 노출 중(masking 아님)
    checked = 0
    for corp, fy in tgts:
        db = COMPANIES / corp / fy / "analysis.duckdb"
        if not db.exists():
            continue
        con = duckdb.connect(str(db), read_only=True)
        if "sce_equity_components" not in {r[0] for r in con.execute("SHOW TABLES").fetchall()}:
            con.close()
            continue
        sce = con.execute("SELECT * FROM sce_equity_components").fetchdf()
        con.close()
        if sce.empty or "change_role" not in sce.columns:
            continue
        checked += 1
        for fs in ["CFS", "OFS"]:
            gt, pc_max, cols = per_component_residual(sce, fs)
            gt_ok = abs(gt) < TOL
            pc_ok = pc_max < TOL
            if gt_ok and not pc_ok:
                masking.append((corp, fy, fs, gt, pc_max, cols))
            elif not gt_ok and not pc_ok:
                pipeline_fail.append((corp, fy, fs, gt, pc_max))

    print(f"\n검사 {checked} 회사연도. ")
    print(
        f"⛔ masking 후보(우리 grand-total OK인데 per-component 깨짐) = {len(masking)}건 "
        "— 뭉개기로 진짜 불일치를 상쇄 은폐했을 후보:"
    )
    for corp, fy, fs, gt, pc, cols in masking:
        top = sorted(cols.items(), key=lambda kv: -abs(kv[1]))[:4]
        cs = "  ".join(f"{c}:{v / TOL:,.0f}" for c, v in top)
        print(f"  {corp}/{fy} [{fs}] grand={gt / TOL:,.0f} per-comp_max={pc / TOL:,.0f} | {cs}")
    if not masking:
        print("  (0건 — 우리 OK 판정 중 per-component로 깨지는 것 없음 = 과수축 masking 무혐의)")
    print(
        f"\n참고: grand-total도 FAIL(정직 노출 중, masking 아님) = {len(pipeline_fail)}건"
        " — 이미 검산 FAIL로 보이는 원공시/잔여."
    )


if __name__ == "__main__":
    main()
