"""전수 홀리스틱 재검용 무겹침 분할 — 감사한 101개사/383 회사연도를 회사 단위로 ~10건씩 묶음.

깊이우선: 한 묶음 ≈ 10 회사연도(±)면 단일 컨텍스트가 주의력 유지하며 깊게 읽는다. 회사는 쪼개지
않는다(한 회사의 전 연도를 한 묶음에서 추세·재작성·이야기로 함께 봄). 결정론(corp 정렬) 재현.

실행: PYTHONPATH=. uv run python data/backtest/_build_holistic_chunks.py
산출: data/backtest/_holistic_chunks.json + data/backtest/_holistic_targets.json(현행화 배치용 전수)
"""

from __future__ import annotations

import json
from pathlib import Path

B = Path("data/backtest")
TARGET_PER_CHUNK = 10  # 회사연도 목표(깊이우선)


def audited() -> dict[str, list[str]]:
    """corp -> 정렬된 연도 리스트 (known positive + 전 라운드, 중복 제거)."""
    out: dict[str, set[str]] = {}
    kc = json.load((B / "known_cases.json").open(encoding="utf-8"))
    for c in kc["cases"]:
        if c.get("label") == "positive" and c.get("runnable"):
            out.setdefault(c["corp_code"], set()).update(str(y) for y in c.get("run_years", []))
    for p in sorted(B.glob("_round_targets*.json")):
        for c in json.load(p.open(encoding="utf-8")).get("cases", []):
            out.setdefault(c["corp_code"], set()).update(str(y) for y in c.get("run_years", []))
    return {k: sorted(v) for k, v in sorted(out.items())}


def main() -> None:
    companies = audited()
    total_cy = sum(len(v) for v in companies.values())

    chunks: list[dict] = []
    cur: list[dict] = []
    cur_cy = 0
    for corp, years in companies.items():
        cur.append({"corp": corp, "years": years})
        cur_cy += len(years)
        if cur_cy >= TARGET_PER_CHUNK:
            chunks.append({"id": len(chunks) + 1, "companies": cur, "company_years": cur_cy})
            cur, cur_cy = [], 0
    if cur:
        chunks.append({"id": len(chunks) + 1, "companies": cur, "company_years": cur_cy})

    payload = {
        "total_companies": len(companies),
        "total_company_years": total_cy,
        "n_chunks": len(chunks),
        "target_per_chunk": TARGET_PER_CHUNK,
        "chunks": chunks,
    }
    (B / "_holistic_chunks.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # 현행화 배치용 전수 타깃(_p1_review_all.py가 읽는 형식)
    flat = {
        "name": "holistic_all",
        "cases": [{"corp_code": c, "run_years": y} for c, y in companies.items()],
    }
    (B / "_holistic_targets.json").write_text(
        json.dumps(flat, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # 무겹침·전수 검증
    seen: set[tuple[str, str]] = set()
    dupes = 0
    cnt = 0
    for ch in chunks:
        for co in ch["companies"]:
            for y in co["years"]:
                cnt += 1
                if (co["corp"], y) in seen:
                    dupes += 1
                seen.add((co["corp"], y))
    print(
        f"회사 {len(companies)} / 회사연도 {total_cy} → {len(chunks)}묶음 (목표 {TARGET_PER_CHUNK}/묶음)"
    )
    print(
        f"분할 합집합 {len(seen)} / 분배 합계 {cnt} / 중복 {dupes}  (합집합==전수 & 중복0 이어야 정상)"
    )
    sizes = [ch["company_years"] for ch in chunks]
    print(
        f"묶음별 회사연도: min {min(sizes)} · max {max(sizes)} · 평균 {sum(sizes) / len(sizes):.1f}"
    )


if __name__ == "__main__":
    main()
