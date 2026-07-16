"""정준(canonical) 계정명 ↔ 공시 원문 라벨 전수 감사(설계3).

LG생건 결함③: 정준명 '이자비용'이 FinanceCosts(공시 라벨 '금융원가')에 매핑돼
잘못된 이름표가 서사까지 관통했다. 이 감사는 실데이터에서 각 정준명에 실제로 매핑된
공시 라벨들을 모아, 정준명이 어느 라벨과도 겹치지 않는 조합(오라벨 후보)을 전부 보고한다.

실행: uv run python -m src.normalize.label_audit  → docs/agent/CANONICAL_LABEL_AUDIT.md
"""

from __future__ import annotations

import re
from pathlib import Path


def _norm(text: str) -> str:
    """비교용 정규화 — 공백·괄호 주석 제거. '이자비용(금융원가)' ↔ '이자비용' 겹침 인정."""

    return re.sub(r"[\s()\[\]·,]", "", str(text or ""))


def _overlaps(canonical: str, label: str) -> bool:
    a, b = _norm(canonical), _norm(label)
    return bool(a and b and (a in b or b in a))


def label_mismatches(rows: list[dict]) -> list[dict]:
    """정준명이 매핑된 공시 라벨 중 어느 것과도 안 겹치는 조합 — 오라벨 후보 전수.

    rows: normalized_financials 레코드(canonical·label 필드). 판정은 후보 제시일 뿐
    확정이 아니다(동의어 매핑 '매출채권↔수취채권'도 잡히므로 사람이 최종 판단)."""

    from src.normalize.mapper import OTHER_CANONICAL

    labels_by_canonical: dict[str, set[str]] = {}
    for row in rows:
        canonical = str(row.get("canonical") or "").strip()
        label = str(row.get("label") or "").strip()
        # 포괄 버킷(기타 중요 계정)은 설계상 이름 불일치가 정상 — 감사 대상 아님.
        if canonical and label and canonical != OTHER_CANONICAL:
            labels_by_canonical.setdefault(canonical, set()).add(label)
    out = []
    for canonical, labels in sorted(labels_by_canonical.items()):
        if not any(_overlaps(canonical, label) for label in labels):
            out.append({"canonical": canonical, "labels": sorted(labels)})
    return out


def audit_all_companies(data_dir: Path | None = None) -> dict:
    """데이터 보유 전 회사·연도의 정준명-라벨 조합 전수 감사(분모 명시).

    판정은 **회사 단위** — 전 회사 합집합으로 겹침을 보면 다른 회사의 정상 라벨이
    한 회사의 오라벨을 가린다(LG생건 '이자비용←금융원가'가 타사 '이자비용' 라벨에
    가려지던 masking). 회사별로 겹침 없는 정준명을 모아 회사 수와 함께 보고한다."""

    from config.settings import settings
    from src.analysis_tools import load_normalized_financials
    from src.report.company_report import available_norm_years

    root = data_dir or settings.data_dir
    all_pairs: set[tuple[str, str]] = set()
    merged: dict[str, dict] = {}
    companies = 0
    skipped: list[str] = []  # silent drop 금지 — 테이블 없는 회사도 분모에 표기
    for corp_dir in sorted(p for p in root.iterdir() if p.is_dir() and p.name.isdigit()):
        years = available_norm_years(corp_dir.name)
        if not years:
            continue
        try:
            frame = load_normalized_financials(corp_dir.name, years)
        except Exception:
            skipped.append(corp_dir.name)
            continue
        if frame.empty or "canonical" not in frame.columns:
            skipped.append(corp_dir.name)
            continue
        companies += 1
        rows = frame[["canonical", "label"]].dropna().to_dict("records")
        all_pairs.update(
            (str(r["canonical"]).strip(), str(r["label"]).strip())
            for r in rows
            if str(r.get("canonical") or "").strip() and str(r.get("label") or "").strip()
        )
        for miss in label_mismatches(rows):
            entry = merged.setdefault(miss["canonical"], {"labels": set(), "corps": 0})
            entry["labels"].update(miss["labels"])
            entry["corps"] += 1
    mismatches = [
        {"canonical": canonical, "labels": sorted(entry["labels"]), "corps": entry["corps"]}
        for canonical, entry in sorted(merged.items())
    ]
    return {
        "companies": companies,
        "skipped": skipped,
        "canonical_label_pairs": len(all_pairs),
        "canonicals": len({p[0] for p in all_pairs}),
        "mismatches": mismatches,
    }


def render_report(audit: dict) -> str:
    lines = [
        "# 정준 계정명 ↔ 공시 라벨 전수 감사",
        "",
        "> 설계3(라벨 권위를 공시 원문으로) 부수 산출물. 정준명이 매핑된 공시 라벨과",
        "> 전혀 안 겹치는 조합 = 오라벨 후보. 동의어 매핑도 잡히므로 사람이 최종 판단한다.",
        "",
        f"- 감사 대상: 회사 {audit['companies']}개, 정준명 {audit['canonicals']}개, "
        f"정준명-라벨 조합 {audit['canonical_label_pairs']}건 (분모)",
        f"- 오라벨 후보: {len(audit['mismatches'])}건",
        f"- 본문 테이블 없어 건너뜀: {len(audit.get('skipped') or [])}개 회사",
        "",
        "| 정준명(내부) | 해당 회사 수 | 매핑된 공시 라벨(원문) |",
        "| --- | --- | --- |",
    ]
    for row in audit["mismatches"]:
        corps = row.get("corps", "-")
        lines.append(f"| {row['canonical']} | {corps} | {' · '.join(row['labels'])} |")
    return "\n".join(lines) + "\n"


def main() -> None:
    audit = audit_all_companies()
    out_path = Path("docs/agent/CANONICAL_LABEL_AUDIT.md")
    out_path.write_text(render_report(audit), encoding="utf-8")
    print(
        f"회사 {audit['companies']} · 조합 {audit['canonical_label_pairs']}건 중 "
        f"오라벨 후보 {len(audit['mismatches'])}건 → {out_path}"
    )


if __name__ == "__main__":
    main()


__all__ = ["audit_all_companies", "label_mismatches", "render_report"]
