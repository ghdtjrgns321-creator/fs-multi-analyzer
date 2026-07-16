"""검사2 오케스트레이터 — as-filed 입력 → 카드 생성 → 채점(설계 §3.6).

⚠ 실행 게이트: 카드 생성은 실LLM 배치(비용 발생), as-filed 수집은 실DART 네트워크다.
이 모듈은 **배선만** 한다 — import·정의는 무해하며, score_benchmark(execute=True)를 명시
호출할 때만 실제 실행된다. 기본(execute=False)은 준비 상태만 점검하고 아무것도 호출하지 않는다.

게이트 통과 벤치마크(우리 DB값==as-filed)는 원본 XBRL 본표 추출 없이 기존 build_company_report를
그대로 쓴다(기재정정 안 된 본표는 JSON API가 이미 as-filed). 원본 XBRL 본표 추출은 기재정정 포함
사례용 확장으로 별도(설계 §4, 미구현).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from golden.hit.build_labels import LabelSet
from golden.hit.check_hit import recall_at_k, score_report

BENCHMARKS_PATH = Path(__file__).with_name("benchmarks.yaml")


def load_benchmarks(path: Path = BENCHMARKS_PATH) -> list[dict[str, Any]]:
    """벤치마크 등록부 로드. 부재 시 빈 리스트."""

    if not path.exists():
        return []
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return list(payload.get("benchmarks", []) or [])


async def _generate_cards(corp: str, year: int) -> list[Any]:
    """as-filed 리포트 → 카드(실LLM). execute=True에서만 호출된다."""

    from src.report.card_pipeline import build_suspicion_cards
    from src.report.company_report import build_company_report

    report = build_company_report(corp, [year])
    result = await build_suspicion_cards(report, run_llm=True)
    cards: list[Any] = []
    for section in ("account_cards", "relationship_cards", "company_cards"):
        cards.extend(result.get(section) or [])
    return cards


async def score_benchmark(
    corp: str,
    year: int,
    label_set: LabelSet,
    k: int = 10,
    execute: bool = False,
) -> dict[str, Any]:
    """한 벤치마크 채점. execute=False(기본)면 실행 없이 준비상태만 반환(dry-run).

    준비상태 = 정답지 등록건수·게이트 통과여부. execute=True라야 실LLM 카드 생성 + 채점.
    """

    targets = [lbl.account_key for lbl in label_set.labels]
    if not execute:
        return {
            "corp": corp,
            "year": year,
            "executed": False,
            "registered_labels": len(label_set.labels),
            "excluded_labels": len(label_set.excluded),
            "note": "dry-run — execute=True에서 실LLM 카드 생성·채점(비용 발생)",
        }
    cards = await _generate_cards(corp, year)
    scored = recall_at_k(targets, cards, k)
    return {"corp": corp, "year": year, "executed": True, **scored}


def report_markdown(scored: dict[str, Any]) -> str:
    """채점 결과 → 채점표 md(dry-run이면 준비상태만)."""

    if not scored.get("executed"):
        return (
            f"# 검사2 준비상태 — {scored.get('corp')}/{scored.get('year')}\n\n"
            f"- 등록 정답지 {scored.get('registered_labels')}건 · "
            f"제외 {scored.get('excluded_labels')}건\n"
            f"- {scored.get('note')}\n"
        )
    return score_report(scored)


__all__ = ["BENCHMARKS_PATH", "load_benchmarks", "report_markdown", "score_benchmark"]
