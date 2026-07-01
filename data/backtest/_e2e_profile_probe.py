"""S3 실데이터 검증 — build_account_profile이 capex·관계기업을 후보로 올리는지.

대주산업 report로 다축 self 프로파일을 만들어 유형자산취득·관계기업투자의 flagged·tail_axes·
순위를 출력한다(§9 정직 보고 — 미달도 그대로).

실행: PYTHONPATH=. uv run python data/backtest/_e2e_profile_probe.py
"""

from __future__ import annotations

from src.report.company_report import build_company_report
from src.signals.profiler import build_account_profile

CORP, YEARS = "00112457", [2021, 2022, 2023, 2024]
TARGETS = ("유형자산취득", "관계기업투자", "지분법손실")


def main() -> None:
    report = build_company_report(CORP, YEARS)
    prof = build_account_profile(report)
    rank = {p["series_key"]: (i, p) for i, p in enumerate(prof, 1)}
    flagged = sum(1 for p in prof if p["flagged"])
    print(f"leaf 계정 {len(prof)} · flagged 후보 {flagged} ({flagged / max(len(prof), 1):.0%})")
    for name in TARGETS:
        for key in [k for k in rank if name in k]:
            i, p = rank[key]
            print(
                f"[{key}] 순위 {i}/{len(prof)} flagged={p['flagged']} tail_axes={p['tail_axes']} "
                f"strength={p['strength']:.3f} "
                f"(delta_q={p['delta_q']:.2f} trend_q={p['trend_q']:.2f} "
                f"vol_q={p['volatility_q']:.2f} mix_q={p['mix_q']:.2f})"
            )


if __name__ == "__main__":
    main()
