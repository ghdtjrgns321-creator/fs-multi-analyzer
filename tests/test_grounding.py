"""S2 — 근거검증 모듈 (PHASE2_DESIGN §4 ①·§7 S2).

인용수치가 계정 실값과 맞는지(스케일·억/조 단위 무관 유효숫자 대조)로 환각을 탈락시키고,
계정 존재만 확인되는 추세/비율 인용은 살리되 value_verified=False로 표시한다.
외부는 출처 URL 존재만 확인. 탈락 건도 reason과 함께 전부 반환(silent drop 0).
"""

from __future__ import annotations

from src.report.grounding import (
    build_account_index,
    verify_company_suspicion,
    verify_suspicions,
)
from src.schemas.findings import IssueType
from src.schemas.suspicion import SuspicionItem


def _index():
    series = [
        {
            "year": "2024",
            "fs_div": "CFS",
            "sj_div": "BS",
            "series_key": "매출채권",
            "canonical": "매출채권",
            "label": "매출채권 및 기타채권",
            "amount": 196_100_000_000.0,
            "mapping_status": "exact",
        }
    ]
    unmapped = [
        {
            "year": "2024",
            "fs_div": "CFS",
            "sj_div": "IS",
            "label": "순이자손익",
            "account_id": "dart_NetInterest",
            "amount": 123_456_000_000.0,
        }
    ]
    return build_account_index(series, unmapped)


def _account_item(**ov) -> SuspicionItem:
    base = dict(
        perspective="numeric",
        scope="account",
        issue_type=IssueType.REVENUE_RECEIVABLES,
        account_id="매출채권",
        sj_div="BS",
        year="2024",
        cited_value="196,100,000,000",
        description="매출채권이 매출 증가율을 상회한다.",
    )
    base.update(ov)
    return SuspicionItem(**base)


def test_exact_amount_verified() -> None:
    g = verify_suspicions([_account_item()], _index())[0]
    assert g.grounded is True
    assert g.value_verified is True


def test_scale_unit_amount_verified() -> None:
    # 1,961억 == 196,100,000,000 (유효숫자 1961 동일)
    g = verify_suspicions([_account_item(cited_value="1,961억")], _index())[0]
    assert g.grounded is True
    assert g.value_verified is True


def test_hallucinated_amount_dropped() -> None:
    g = verify_suspicions([_account_item(cited_value="777,777,777")], _index())[0]
    assert g.grounded is False
    assert "불일치" in g.reason or "환각" in g.reason


def test_missing_account_dropped() -> None:
    g = verify_suspicions([_account_item(account_id="존재하지않는계정")], _index())[0]
    assert g.grounded is False


def test_non_amount_citation_kept_unverified() -> None:
    g = verify_suspicions([_account_item(cited_value="전년 대비 47% 급증")], _index())[0]
    assert g.grounded is True
    assert g.value_verified is False


def test_external_with_url_low_confidence() -> None:
    item = SuspicionItem(
        perspective="external",
        scope="company",
        issue_type=IssueType.CONTINGENCY_RELATED_PARTY,
        account_id=None,
        year="2024",
        cited_value=None,
        description="감사보고서 계속기업 불확실성 문단.",
        source_url="https://dart.fss.or.kr/x",
    )
    g = verify_company_suspicion(item)
    assert g.grounded is True
    assert g.value_verified is False


def test_external_without_url_dropped() -> None:
    item = SuspicionItem(
        perspective="external",
        scope="company",
        issue_type=IssueType.CONTINGENCY_RELATED_PARTY,
        account_id=None,
        year="2024",
        cited_value=None,
        description="출처 없는 외부 주장.",
    )
    g = verify_company_suspicion(item)
    assert g.grounded is False


def test_same_account_name_different_statement_not_cross_matched() -> None:
    # 동명이계(P2-1): 법인세비용이 IS=523억, CF=317억(라운드 아님 — 유효숫자 보존).
    # sj_div 미분리 시엔 합쳐진 풀로 CF 금액이 IS 인용에 오통과했음.
    series = [
        {
            "year": "2024",
            "fs_div": "CFS",
            "sj_div": "IS",
            "series_key": "법인세비용",
            "canonical": "법인세비용",
            "label": "법인세비용",
            "amount": 52_300_000_000.0,
            "mapping_status": "exact",
        },
        {
            "year": "2024",
            "fs_div": "CFS",
            "sj_div": "CF",
            "series_key": "법인세비용",
            "canonical": "법인세비용",
            "label": "법인세비용",
            "amount": 31_700_000_000.0,
            "mapping_status": "exact",
        },
    ]
    index = build_account_index(series, [])
    # IS 관점이 CF 금액(317억)을 인용 → IS 풀에 없으므로 환각 탈락
    wrong = _account_item(account_id="법인세비용", sj_div="IS", cited_value="31,700,000,000")
    g_wrong = verify_suspicions([wrong], index)[0]
    assert g_wrong.grounded is False
    # IS 관점이 IS 금액(523억)을 인용 → 통과
    right = _account_item(account_id="법인세비용", sj_div="IS", cited_value="52,300,000,000")
    g_right = verify_suspicions([right], index)[0]
    assert g_right.grounded is True and g_right.value_verified is True


def test_cfs_ofs_same_account_not_cross_matched() -> None:
    # OFS 개방: 차입금이 연결(CFS)=111,110억·별도(OFS)=222,642억. 같은 sj_div(BS)라 sj_div만으론
    # 못 가르지만 series_key 접두(OFS:차입금)로 별도 풀이 격리돼 교차환각이 차단된다.
    # (유효숫자 3+ 금액 — 라운드 붕괴 회피.)
    series = [
        {
            "year": "2024",
            "fs_div": "CFS",
            "sj_div": "BS",
            "series_key": "CFS:차입금",
            "canonical": "차입금",
            "label": "차입금",
            "amount": 11_111_000_000_000.0,
            "mapping_status": "exact",
        },
        {
            "year": "2024",
            "fs_div": "OFS",
            "sj_div": "BS",
            "series_key": "OFS:차입금",
            "canonical": "차입금",
            "label": "차입금",
            "amount": 22_264_200_000_000.0,
            "mapping_status": "exact",
        },
    ]
    index = build_account_index(series, [])
    # 별도(OFS) 정당 금액 인용 → 통과(OFS 개방으로 안 탈락)
    right = _account_item(account_id="OFS:차입금", sj_div="BS", cited_value="22,264,200,000,000")
    g_right = verify_suspicions([right], index)[0]
    assert g_right.grounded is True and g_right.value_verified is True
    # 별도 계정에 연결 금액 인용 → OFS 풀에 없어 교차환각 탈락
    wrong = _account_item(account_id="OFS:차입금", sj_div="BS", cited_value="11,111,000,000,000")
    g_wrong = verify_suspicions([wrong], index)[0]
    assert g_wrong.grounded is False


def _note_index():
    note_facts = [
        {
            "label": "매출 등, 특수관계자거래",
            "value": "195674381000000",
            "category": "특수관계자거래",
        },
        {"label": "소송", "value": "당사는 손해배상 소송에 피소되었다", "category": "약정_우발"},
    ]
    return build_account_index([], [], note_facts)


def _note_item(**ov) -> SuspicionItem:
    base = dict(
        perspective="note",
        scope="account",
        issue_type=IssueType.CONTINGENCY_RELATED_PARTY,
        account_id="매출 등, 특수관계자거래",
        year="2024",
        cited_value="195,674,381,000,000",
        description="특수관계자 거래 규모가 과다하다.",
    )
    base.update(ov)
    return SuspicionItem(**base)


def test_note_numeric_fact_grounded_and_verified() -> None:
    g = verify_suspicions([_note_item()], _note_index())[0]
    assert g.grounded is True
    assert g.value_verified is True  # 195조 정확 인용 → 검증


def test_note_narrative_grounded_unverified() -> None:
    item = _note_item(account_id="소송", cited_value="소송 진행 중", description="소송 우발.")
    g = verify_suspicions([item], _note_index())[0]
    assert g.grounded is True  # 서술형 — 존재 확인
    assert g.value_verified is False  # 금액 비교불가


def test_note_only_account_not_in_body_still_grounds() -> None:
    # 특수관계자거래는 본문(account_series)에 없다 — note 색인 없으면 환각 탈락하던 것.
    body_only_index = build_account_index([], [], None)  # note 미색인
    g_dropped = verify_suspicions([_note_item()], body_only_index)[0]
    assert g_dropped.grounded is False  # note 색인 없으면 탈락(회귀 대조용)
    g_ok = verify_suspicions([_note_item()], _note_index())[0]
    assert g_ok.grounded is True  # note 색인 있으면 통과


def test_body_suspicion_does_not_match_note_pool() -> None:
    # 본문(numeric) 의심건이 note: 풀로 교차환각 통과하면 안 됨.
    idx = _note_index()
    body = _account_item(
        perspective="numeric",
        account_id="매출 등, 특수관계자거래",
        cited_value="195,674,381,000,000",
    )
    g = verify_suspicions([body], idx)[0]
    assert g.grounded is False  # numeric은 note: 네임스페이스 조회 안 함 → 환각 탈락


def test_sce_change_perspective_grounds() -> None:
    # SCE 2D 셀 인용(trend 관점)이 sce: 네임스페이스로 grounded.
    sce = [{"change": "자기주식취득", "component": "기타자본", "amount": -1_811_800_000_000.0}]
    idx = build_account_index([], [], None, sce)
    item = _account_item(
        perspective="trend", account_id="자기주식취득", cited_value="1,811,800,000,000"
    )
    g = verify_suspicions([item], idx)[0]
    assert g.grounded is True and g.value_verified is True


def test_verify_returns_all_with_reasons_no_silent_drop() -> None:
    items = [
        _account_item(),
        _account_item(cited_value="777,777,777"),
        _account_item(account_id="없는계정"),
    ]
    results = verify_suspicions(items, _index())
    assert len(results) == len(items)
    assert all(r.reason for r in results)
    assert sum(1 for r in results if not r.grounded) == 2
