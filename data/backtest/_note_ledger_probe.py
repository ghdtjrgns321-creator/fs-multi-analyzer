"""주석 차원 원장·비용 실측 — 삼성·대주.

주석 모집단 대조(흡수·메타 제외 후 surfaced 전량) + note 관점 입력 토큰·증분비용.
산출물: _NOTE_LEDGER_PROBE.txt
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.analysis_tools import load_notes_classified, load_sce_equity_components  # noqa: E402
from src.report.company_report import _compact_note_facts, _compact_sce_cells  # noqa: E402
from src.report.coverage import (  # noqa: E402
    build_note_ledger,
    build_sce_ledger,
    surfaced_note_facts,
)

CASES = [("00126380", "삼성전자"), ("00112457", "대주산업")]


def main() -> None:
    out: list[str] = ["# 주석 차원 원장 + 비용 probe"]
    ok = True
    for corp, name in CASES:
        facts = load_notes_classified(corp, [2024]).to_dict("records")
        led = build_note_ledger(facts)
        surfaced = _compact_note_facts(surfaced_note_facts(facts))
        blob = json.dumps(surfaced, ensure_ascii=False)
        chars = len(blob)
        tok_lo, tok_hi = chars / 2.5, chars / 2.0
        cost_lo = tok_lo / 1e6 * 2.5 * 1380
        cost_hi = tok_hi / 1e6 * 2.5 * 1380
        out.append("")
        out.append(f"## {name} ({corp})")
        out.append(
            f"- 모집단 N={led['population_n']} = surfaced {led['surfaced_n']} "
            f"+ 제외 {len(led['excluded'])} + 미설명 {len(led['unaccounted'])}"
        )
        out.append(
            f"- 항등식 reconciled={led['reconciled']} / 제외사유 {led['excluded_by_reason']}"
        )
        out.append(f"- surfaced compact {chars:,}자 ≈ 입력토큰 {int(tok_lo):,}~{int(tok_hi):,}")
        out.append(f"- note 관점 증분비용 ≈ {cost_lo:.0f}~{cost_hi:.0f}원")
        # SCE 2D
        sce_raw = load_sce_equity_components(corp, [2024]).to_dict("records")
        sce_led = build_sce_ledger(sce_raw)
        sce_compact = _compact_sce_cells(sce_raw)
        sblob = len(json.dumps(sce_compact, ensure_ascii=False))
        out.append(
            f"- SCE 2D: surfaced {sce_led['surfaced_n']}/{sce_led['population_n']} "
            f"reconciled={sce_led['reconciled']} · compact {sblob:,}자"
        )
        if led["unaccounted"]:
            out.append(f"- ⚠ 미설명 {len(led['unaccounted'])}건: {led['unaccounted'][:5]}")
            ok = False
        if not led["reconciled"]:
            ok = False

    text = "\n".join(out)
    path = Path(__file__).parent / "_NOTE_LEDGER_PROBE.txt"
    path.write_text(text, encoding="utf-8")
    print(text)
    print(f"\n[written] {path}")
    print(f"\n[VERDICT] 전 케이스 항등식·미설명0 = {ok}")


if __name__ == "__main__":
    main()
