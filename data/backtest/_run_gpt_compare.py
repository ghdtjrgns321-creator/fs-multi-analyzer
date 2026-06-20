"""10 고위험사를 gpt-5.4(run_llm_holistic, UI와 동일 경로)로 9렌즈 통독 → _llm_compare/<corp>_gpt.md.

내 공장(세션 모델)이 회사별 다년 dump를 함께 본 것과 동일 조건으로,
회사별 전 연도 dump를 합쳐 같은 9렌즈 프롬프트로 gpt-5.4에 준다(모델만 다름).

실행: PYTHONPATH=. uv run python data/backtest/_run_gpt_compare.py
필요: OPENAI_API_KEY(이 환경 설정됨).
"""

from __future__ import annotations

import json
from pathlib import Path

from config.settings import settings
from dashboard.onboarding import run_llm_holistic

ROOT = Path(__file__).resolve().parents[2]

# 큰 dump(최대 ~44k토큰)+추론 호출 보호 — 타임아웃 천장만 상향(품질 무관).
settings.openai_timeout_seconds = 600.0

# 회사→years: _holistic_chunks.json에서 각 회사의 연도 목록.
chunks = json.loads((ROOT / "data/backtest/_holistic_chunks.json").read_text(encoding="utf-8"))[
    "chunks"
]
years: dict[str, list] = {}
for ch in chunks:
    for c in ch["companies"]:
        years[c["corp"]] = c["years"]

TARGETS = [
    "00153861",
    "00159616",
    "01091382",
    "00118345",
    "00409681",
    "00413046",
    "00657783",
    "00148504",
    "00367844",
    "00102760",
]

out = ROOT / "data/backtest/_llm_compare"
out.mkdir(exist_ok=True)

for corp in TARGETS:
    dumps = []
    for y in years.get(corp, []):
        p = ROOT / f"data/backtest/_review_dumps/{corp}_{y}.txt"
        if p.exists():
            dumps.append(p.read_text(encoding="utf-8"))
    if not dumps:
        print(corp, "NO_DUMP", years.get(corp))
        continue
    joined = "\n\n===다음 회사연도===\n\n".join(dumps)
    r = run_llm_holistic(joined)
    body = r.get("findings", "") if r["status"] == "ok" else f"[{r['status']}] {r['message']}"
    (out / f"{corp}_gpt.md").write_text(body, encoding="utf-8")
    print(corp, r["status"], "findings_len=", len(r.get("findings", "")), "n_years=", len(dumps))
