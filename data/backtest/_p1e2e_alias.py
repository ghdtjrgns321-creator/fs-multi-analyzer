"""P1 E2E 추가 — 온보딩 alias 제안(quirk) 효과 측정.

4사 무표준코드 미매핑 계정에 LLM(gpt-5.4)이 canonical 후보를 제안하는지 실행·기록.
제안은 candidate 목록 안에서만(앵커링), 밖이면 '기타 중요 계정' 강등. 적중 판정은 사람(통독).

실행: PYTHONPATH=. uv run python data/backtest/_p1e2e_alias.py
"""

from __future__ import annotations

import json
from pathlib import Path

from src.report.alias_suggest import suggest_aliases

SAMPLE = Path("data/backtest/_p1e2e_sample.json")
LOG = Path("data/backtest/_p1e2e_alias_log.json")
NO_MATCH = "기타 중요 계정"


def main() -> None:
    sample = json.loads(SAMPLE.read_text(encoding="utf-8"))
    out: list[dict] = []
    for s in sample:
        corp, year = s["corp"], int(s["year"])
        res = suggest_aliases(corp, year)
        result = res.get("result")
        sugg = result.suggestions if result else []
        matched = [x for x in sugg if x.suggested_canonical != NO_MATCH]
        conf07 = [x for x in matched if x.confidence >= 0.7]
        rec = {
            "corp": corp,
            "year": year,
            "status": res["status"],
            "total_suggested": len(sugg),
            "canonical_proposed": len(matched),
            "conf_ge_0.7": len(conf07),
            "latency_s": res.get("latency_s"),
            "suggestions": [
                {
                    "alias": x.alias,
                    "sj_div": x.sj_div,
                    "canonical": x.suggested_canonical,
                    "confidence": x.confidence,
                    "reason": x.reason,
                }
                for x in sugg
            ],
        }
        out.append(rec)
        print(
            f"[{corp}/{year}] status={res['status']} 제안={len(sugg)} "
            f"canonical제안={len(matched)} conf>=0.7={len(conf07)}",
            flush=True,
        )
    LOG.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print("DONE", flush=True)


if __name__ == "__main__":
    main()
