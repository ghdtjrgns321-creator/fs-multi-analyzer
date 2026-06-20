"""O4 가용성 선검증: 기존 삼성 XBRL zip을 Arelle로 로드해
비금융 주석(무형자산·차입금·관계기업 등) 개념·사실(fact)이 실제로 들어있는지 측정.

빈 PASS 금지: 주석 개념 검색 결과를 수치로 보고. 추출 가능하면 표본 fact를 덤프.
재현: PYTHONPATH=. uv run python data/backtest/_dg_arelle_probe.py <zip_path>
"""

from __future__ import annotations

import sys
import tempfile
import zipfile
from collections import Counter
from pathlib import Path

from arelle import Cntlr

# 비금융 주석 핵심 개념 키워드(IFRS 표준 영문명 + 한글 라벨 양쪽으로 탐색)
NOTE_KEYWORDS = {
    "무형자산": ["IntangibleAssets", "무형자산", "개발비", "영업권", "Goodwill"],
    "차입금": ["Borrowings", "차입금", "사채", "BondsIssued", "단기차입", "장기차입"],
    "관계기업": [
        "AssociatesAndJointVentures",
        "관계기업",
        "지분법",
        "InvestmentsInAssociates",
        "JointVentures",
    ],
    "리스": ["Lease", "리스", "사용권자산", "RightofuseAssets"],
    "충당부채": ["Provisions", "충당부채"],
    "금융상품": ["FinancialInstruments", "금융상품", "FairValue", "공정가치"],
}


def probe(zip_path: Path) -> dict:
    # Arelle는 zip 직접 로드 시 IOerror → 추출 후 .xbrl 인스턴스를 직접 지정해야 한다.
    tmp = tempfile.mkdtemp()
    with zipfile.ZipFile(zip_path) as zf:
        zf.extractall(tmp)
    entries = list(Path(tmp).glob("*.xbrl"))
    if not entries:
        return {"zip": str(zip_path), "loaded": False, "fact_count": 0, "reason": "no .xbrl in zip"}

    cntlr = Cntlr.Cntlr(logFileName="logToBuffer")
    model = cntlr.modelManager.load(str(entries[0]))
    if model is None or not getattr(model, "facts", None):
        return {"zip": str(zip_path), "loaded": False, "fact_count": 0}

    facts = list(model.facts)
    # 개념 로컬명 분포
    concept_names = Counter()
    label_hits: dict[str, list] = {k: [] for k in NOTE_KEYWORDS}

    for f in facts:
        if f.concept is None:
            continue
        local = f.concept.qname.localName if f.concept.qname else ""
        concept_names[local] += 1
        # 한글 라벨
        try:
            ko_label = f.concept.label(lang="ko") or ""
        except Exception:
            ko_label = ""
        hay = f"{local} {ko_label}"
        for cat, kws in NOTE_KEYWORDS.items():
            if any(kw in hay for kw in kws):
                if len(label_hits[cat]) < 5:
                    val = (f.value or "")[:40] if f.value else ""
                    label_hits[cat].append(
                        {"concept": local, "label_ko": ko_label[:40], "value": val}
                    )

    result = {
        "zip": str(zip_path),
        "loaded": True,
        "fact_count": len(facts),
        "distinct_concepts": len(concept_names),
        "note_category_hits": {k: len(v) for k, v in label_hits.items()},
        "note_samples": label_hits,
        "top_concepts": concept_names.most_common(15),
    }
    cntlr.modelManager.close()
    return result


def main() -> None:
    zip_path = (
        Path(sys.argv[1])
        if len(sys.argv) > 1
        else Path("data/companies/00126380/2024/raw/financial_statement_xbrl.zip")
    )
    res = probe(zip_path)
    print(f"\n=== Arelle probe: {res['zip']} ===")
    print(
        f"loaded={res['loaded']} facts={res.get('fact_count')} "
        f"concepts={res.get('distinct_concepts')}"
    )
    if not res["loaded"]:
        print("로드 실패 — XBRL 추출 불가")
        return
    print("\n[비금융 주석 개념 적중수]")
    for cat, n in res["note_category_hits"].items():
        print(f"  {cat:8s}: {n}")
    print("\n[표본 fact (카테고리별 최대 5)]")
    for cat, samples in res["note_samples"].items():
        if samples:
            print(f"  -- {cat} --")
            for s in samples:
                print(f"     {s['concept']:45s} | {s['label_ko']:30s} | {s['value']}")
    print("\n[최다 개념 15]")
    for name, cnt in res["top_concepts"]:
        print(f"  {name:50s} {cnt}")


if __name__ == "__main__":
    main()
