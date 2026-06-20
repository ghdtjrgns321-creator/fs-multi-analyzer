"""E2E 감사 — 6사 Phase1 material 덤프(= LLM에 넘기는 것).

build_company_report + numeric/flow/change/note material을 회사별 JSON으로 저장.
이게 "Phase1이 Phase2 LLM에 건네는 것"의 전부다. 원본 통독과 대조할 좌변.

실행: PYTHONPATH=. uv run python -m data.backtest._e2e_material
"""

from __future__ import annotations

import json
from pathlib import Path

from src.report.company_report import build_company_report
from src.report.materials import change_material, flow_material, note_material, numeric_material

OUT = Path("data/backtest/_e2e_material")

TARGETS = [
    ("대형다각화", "00126380", 2024),
    ("금융지주", "00688996", 2023),
    ("자본거래多", "00258801", 2024),
    ("정정본", "00117212", 2024),
    ("구포맷", "00356361", 2017),
    ("소형단순", "00160375", 2024),
]


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    index = []
    for dim, corp, target_year in TARGETS:
        rec: dict = {"dim": dim, "corp": corp, "target_year": target_year}
        try:
            report = build_company_report(corp)
            bundle = {
                "_report_keys": sorted(report.keys()),
                "target_year": report.get("target_year"),
                "years_available": report.get("years", report.get("years_available")),
                "review_queue_len": len(report.get("review_queue", [])),
                "unmapped_material_accounts": report.get("unmapped_material_accounts", []),
                "numeric_material": numeric_material(report),
                "flow_material": flow_material(report),
                "change_material": change_material(report),
                "note_material_CFS": note_material(corp, target_year, "CFS"),
                "note_material_OFS": note_material(corp, target_year, "OFS"),
            }
            (OUT / f"{corp}_{dim}.json").write_text(
                json.dumps(bundle, ensure_ascii=False, indent=1, default=str), encoding="utf-8"
            )
            rec["status"] = "ok"
            rec["review_queue_len"] = bundle["review_queue_len"]
            rec["note_CFS"] = len(bundle["note_material_CFS"]["note_sections"])
            rec["note_OFS"] = len(bundle["note_material_OFS"]["note_sections"])
            rec["chunks_CFS"] = len(bundle["note_material_CFS"]["report_review_chunks"])
        except Exception:
            import traceback

            rec["status"] = "error"
            rec["error"] = traceback.format_exc()[-1200:]
        index.append(rec)
        print(json.dumps(rec, ensure_ascii=False)[:400], flush=True)
    (OUT / "_index.json").write_text(
        json.dumps(index, ensure_ascii=False, indent=1), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
