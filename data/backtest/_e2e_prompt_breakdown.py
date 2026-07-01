"""Phase2 프롬프트 비대 원인 분해 — 어느 키가 토큰을 먹는지 실측.

numeric/flow/change material board의 키별 JSON 크기를 재고, account_metrics_panel을
컬럼형으로 바꿨을 때 절감량을 추정한다. 설계 옵션을 수치로 근거화(§9 측정 우선).

실행: PYTHONPATH=. uv run python data/backtest/_e2e_prompt_breakdown.py [corp] [year]
"""

from __future__ import annotations

import json
import sys

CORP = sys.argv[1] if len(sys.argv) > 1 else "00126380"
YEAR = int(sys.argv[2]) if len(sys.argv) > 2 else 2024
YEARS = list(range(YEAR - 3, YEAR + 1))

from src.report.company_report import build_company_report  # noqa: E402
from src.report.materials import change_material, flow_material, numeric_material  # noqa: E402


def _chars(obj: object) -> int:
    return len(json.dumps(obj, ensure_ascii=False))


def _panel_columnar(panel: list[dict]) -> dict:
    """객체 리스트 → 컬럼형(키 이름 1회). 정보 손실 0."""
    if not panel:
        return {"columns": [], "rows": []}
    scalar_cols = [
        "account",
        "sj_div",
        "delta_over_assets",
        "trend",
        "volatility_cv",
        "mix_pct",
        "mix_shift_pp",
        "z_score",
    ]
    rows = []
    for e in panel:
        row = [e.get(c) for c in scalar_cols]
        row.append(e.get("amounts"))
        row.append(e.get("yoy_pct"))
        row.append(e.get("percentiles"))
        rows.append(row)
    return {"columns": scalar_cols + ["amounts", "yoy_pct", "percentiles"], "rows": rows}


def main() -> None:
    report = build_company_report(CORP, YEARS)
    print(
        f"company={report.get('company_name')} "
        f"series_rows={len(report.get('account_level_series', []))} "
        f"panel_entries={len(report.get('account_metrics_panel', []))}\n"
    )

    boards = {
        "numeric": numeric_material(report),
        "flow": flow_material(report),
        "change": change_material(report),
    }

    for pname, board in boards.items():
        total = _chars(board)
        print(f"=== {pname}: 전체 {total:,} chars (~{total // 3:,} tokens) ===")
        # 키별 크기 내림차순
        sizes = sorted(((k, _chars(v)) for k, v in board.items()), key=lambda x: -x[1])
        for k, sz in sizes:
            pct = sz / total * 100 if total else 0
            print(f"  {k:28s} {sz:>9,} chars ({pct:4.1f}%)")
        print()

    # 컬럼형 절감 추정 (panel 기준)
    panel = report.get("account_metrics_panel", [])
    cur = _chars(panel)
    col = _chars(_panel_columnar(panel))  # type: ignore[arg-type]
    print("=== account_metrics_panel 컬럼형 절감 ===")
    print(f"  현재(객체리스트): {cur:,} chars")
    print(f"  컬럼형:          {col:,} chars")
    print(f"  절감:            {cur - col:,} chars ({(cur - col) / cur * 100:.1f}%)")

    # series vs panel 중복 (둘 다 amounts 보유)
    series = report.get("account_level_series", [])
    print("\n=== account_level_series vs panel 중복 ===")
    print(f"  account_level_series: {_chars(series):,} chars")
    print(f"  panel.amounts만:      {_chars([e.get('amounts') for e in panel]):,} chars")  # type: ignore[union-attr]


if __name__ == "__main__":
    main()
