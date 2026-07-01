"""커버리지 원장 실데이터 검증 — 삼성·대주에서 미설명 셀(unaccounted)이 0인지.

근본구조 C: 분석 모집단(본문 셀) = 분석셀 + 제외사유셀 + 미설명셀. 미설명>0이면 조용한 드롭.
산출물: _LEDGER_PROBE.txt
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.report.company_report import build_company_report  # noqa: E402

CASES = [("00126380", "삼성전자"), ("00112457", "대주산업")]


def main() -> None:
    out: list[str] = ["# 커버리지 원장 probe — 본문 셀 모집단 대조"]
    ok = True
    for corp, name in CASES:
        report = build_company_report(
            corp_code=corp,
            company_provider=lambda c, n=name: {"stock_name": n, "corp_code": c},
        )
        led = report["coverage_ledger"]
        out.append("")
        out.append(f"## {name} ({corp}) target={report['target_year']} 윈도우={report['years']}")
        out.append(
            f"- 모집단(분모) N={led['population_n']} = 분석 {led['analyzed_n']} "
            f"+ 제외(사유) {len(led['excluded'])} + 미설명 {len(led['unaccounted'])}"
        )
        out.append(f"- 항등식 reconciled={led['reconciled']}")
        # 제외 사유별 집계
        reasons: dict[str, int] = {}
        for e in led["excluded"]:
            reasons[e["reason"]] = reasons.get(e["reason"], 0) + 1
        out.append(f"- 제외 사유: {reasons}")
        if led["unaccounted"]:
            out.append(f"- ⚠ 미설명 셀 {len(led['unaccounted'])}건:")
            for u in led["unaccounted"][:20]:
                out.append(f"    {u['cell']}")
        else:
            out.append("- ✅ 미설명 0")
        if not led["reconciled"] or led["unaccounted"]:
            ok = False

    text = "\n".join(out)
    path = Path(__file__).parent / "_LEDGER_PROBE.txt"
    path.write_text(text, encoding="utf-8")
    print(text)
    print(f"\n[written] {path}")
    print(f"\n[VERDICT] 전 케이스 항등식 성립·미설명 0 = {ok}")


if __name__ == "__main__":
    main()
