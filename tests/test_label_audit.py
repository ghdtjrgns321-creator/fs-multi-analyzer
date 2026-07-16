"""설계3 — 정준명 ↔ 공시 라벨 오라벨 후보 전수 감사."""

from __future__ import annotations

from src.normalize.label_audit import label_mismatches, render_report


def test_mismatch_detects_finance_costs_mislabel():
    # 결함③ 실사례: 정준 '이자비용' ← 공시 '금융원가'(겹침 없음) → 오라벨 후보.
    rows = [
        {"canonical": "이자비용", "label": "금융원가"},
        {"canonical": "매출", "label": "매출액"},  # 부분 겹침 — 정상
        {"canonical": "이자비용(금융원가)", "label": "이자비용"},  # 괄호 정규화 — 정상
    ]
    out = label_mismatches(rows)
    assert [m["canonical"] for m in out] == ["이자비용"]
    assert out[0]["labels"] == ["금융원가"]


def test_mismatch_cleared_if_any_label_overlaps():
    # 같은 정준명에 겹치는 라벨이 하나라도 있으면 후보에서 제외(회사별 표기 차이 허용).
    rows = [
        {"canonical": "이자비용", "label": "금융원가"},
        {"canonical": "이자비용", "label": "이자비용"},
    ]
    assert label_mismatches(rows) == []


def test_per_company_audit_not_masked_by_other_companies():
    # 결함③ 재발 방지의 핵심: 타사의 정상 라벨('이자비용')이 한 회사의 오라벨
    # ('금융원가')을 가리면 안 된다 — 판정은 회사 단위여야 한다.
    lg_rows = [{"canonical": "이자비용", "label": "금융원가"}]
    other_rows = [{"canonical": "이자비용", "label": "이자비용"}]
    # 합집합으로 보면 겹침이 생겨 0건(masking) — 회사별로 보면 LG는 여전히 후보.
    assert label_mismatches(lg_rows + other_rows) == []
    assert [m["canonical"] for m in label_mismatches(lg_rows)] == ["이자비용"]


def test_report_includes_denominator():
    audit = {
        "companies": 2,
        "canonicals": 3,
        "canonical_label_pairs": 5,
        "mismatches": [{"canonical": "이자비용", "labels": ["금융원가"], "corps": 1}],
    }
    text = render_report(audit)
    assert "조합 5건 (분모)" in text
    assert "| 이자비용 | 1 | 금융원가 |" in text
