"""변동 분해 엔진 검증 — 변형 선택·잔차 항등식·결측 graceful + 실데이터 잔차율."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.report.decomposition import decompose_change, load_bridges

BRIDGES = load_bridges()  # config/decomposition.yaml 실물 사용(존재≠사용 방지)


def _rows(spec: dict[str, dict[int, float]], fs_div: str = "CFS") -> list[dict]:
    return [
        {"series_key": f"{fs_div}:{name}", "year": y, "amount": a}
        for name, years in spec.items()
        for y, a in years.items()
    ]


# ── (A) 표준형 선택 — GP-판관비만으로 정확히 맞는 회사 ─────────────────────
def test_standard_variant_selected_when_exact():
    rows = _rows(
        {
            "영업이익": {2023: 100.0, 2024: 40.0},
            "매출총이익": {2023: 300.0, 2024: 260.0},
            "판매비와관리비": {2023: 200.0, 2024: 220.0},
            # 기타포함형을 쓰면 잔차가 커지도록 기타 계정 존재
            "기타수익": {2023: 5.0, 2024: 50.0},
            "기타비용": {2023: 1.0, 2024: 2.0},
        }
    )
    out = decompose_change(rows, "CFS:영업이익", 2024, BRIDGES)
    assert out is not None and out["variant"] == "표준"
    assert out["delta"] == -60.0
    assert out["residual"] == 0.0
    by_acct = {r["account"]: r for r in out["rows"]}
    assert by_acct["매출총이익"]["delta"] == -40.0  # GP 하락 기여
    assert by_acct["판매비와관리비"]["delta"] == -20.0  # 판관비 증가 → 음의 기여
    assert by_acct["판매비와관리비"]["contribution_pct"] == pytest.approx(-33.3, abs=0.1)


# ── (B) 기타포함형 선택 — 기타손익까지 넣어야 맞는 회사 ────────────────────
def test_other_included_variant_selected_when_better():
    rows = _rows(
        {
            "영업이익": {2023: 104.0, 2024: 88.0},
            "매출총이익": {2023: 300.0, 2024: 260.0},
            "판매비와관리비": {2023: 200.0, 2024: 220.0},
            "기타수익": {2023: 5.0, 2024: 50.0},
            "기타비용": {2023: 1.0, 2024: 2.0},
        }
    )
    out = decompose_change(rows, "CFS:영업이익", 2024, BRIDGES)
    assert out is not None and out["variant"] == "기타포함"
    assert out["residual"] == 0.0


# ── (C) 구성 결측 graceful — 결측 행은 None으로 표기, 크래시 없음 ───────────
def test_missing_component_kept_as_none_row():
    rows = _rows(
        {
            "영업이익": {2023: 100.0, 2024: 40.0},
            "매출총이익": {2023: 300.0, 2024: 260.0},
            # 판관비 자체가 없는 회사(비용성격별 분류)
        }
    )
    out = decompose_change(rows, "CFS:영업이익", 2024, BRIDGES)
    assert out is not None
    by_acct = {r["account"]: r for r in out["rows"]}
    assert by_acct["판매비와관리비"]["delta"] is None  # 결측 은폐 금지
    assert out["residual"] != 0.0  # 미설명 잔차로 정직 표시


# ── (D) 잔차 항등식 — sum(기여) + 잔차 == Δ부모 ────────────────────────────
def test_residual_identity_holds():
    rows = _rows(
        {
            "영업이익": {2023: 100.0, 2024: 37.0},
            "매출총이익": {2023: 300.0, 2024: 270.0},
            "판매비와관리비": {2023: 200.0, 2024: 225.0},
        }
    )
    out = decompose_change(rows, "CFS:영업이익", 2024, BRIDGES)
    assert out is not None
    explained = sum(r["delta"] for r in out["rows"] if r["delta"] is not None)
    assert explained + out["residual"] == pytest.approx(out["delta"], abs=1.0)  # ≤1원


# ── (F) 동의 canonical 슬롯 — '판매 및 일반관리비'(ifrs id계)로 신고한 회사 ──
def test_synonym_canonical_slot_absorbed():
    rows = _rows(
        {
            "영업이익": {2023: 100.0, 2024: 40.0},
            "매출총이익": {2023: 300.0, 2024: 260.0},
            "판매 및 일반관리비": {2023: 200.0, 2024: 220.0},  # 동의 canonical
        }
    )
    out = decompose_change(rows, "CFS:영업이익", 2024, BRIDGES)
    assert out is not None
    by_acct = {r["account"]: r for r in out["rows"]}
    # 표시 라벨은 슬롯 label(판매비와관리비), 값은 동의 canonical에서 흡수 — 결측 아님
    assert by_acct["판매비와관리비"]["delta"] == -20.0
    assert out["residual"] == 0.0


# ── (G) 재귀 펼침 — 매출총이익 행이 매출·매출원가 children을 갖는다 ──────────
FULL_CHAIN = {
    "영업이익": {2023: 100.0, 2024: 40.0},
    "매출총이익": {2023: 300.0, 2024: 260.0},
    "판매비와관리비": {2023: 200.0, 2024: 220.0},
    "매출": {2023: 1000.0, 2024: 930.0},
    "매출원가": {2023: 700.0, 2024: 670.0},
}


def test_expand_gp_children_deltas():
    out = decompose_change(_rows(FULL_CHAIN), "CFS:영업이익", 2024, BRIDGES)
    assert out is not None
    gp = next(r for r in out["rows"] if r["account"] == "매출총이익")
    children = {c["account"]: c for c in gp.get("children") or []}
    assert set(children) == {"매출", "매출원가"}
    assert children["매출"]["delta"] == -70.0  # 매출 감소 기여
    assert children["매출원가"]["delta"] == +30.0  # 원가 절감 기여(부호 반전)
    # 최상위(영업이익 Δ=-60) 기준 기여율
    assert children["매출"]["contribution_pct"] == pytest.approx(-116.7, abs=0.1)


def test_expand_children_identity_and_no_cycle():
    out = decompose_change(_rows(FULL_CHAIN), "CFS:영업이익", 2024, BRIDGES)
    gp = next(r for r in out["rows"] if r["account"] == "매출총이익")
    child_sum = sum(c["delta"] for c in gp["children"] if c["delta"] is not None)
    assert child_sum + gp["child_residual"] == pytest.approx(gp["delta"], abs=1.0)  # ≤1원
    # 순환 가드: 자기참조 브리지여도 크래시 없이 children 미첨부
    cyclic = {
        "영업이익": {
            "variants": [
                {
                    "name": "x",
                    "components": [{"label": "영업이익", "sign": 1, "accounts": ["영업이익"]}],
                }
            ]
        }
    }
    out2 = decompose_change(_rows(FULL_CHAIN), "CFS:영업이익", 2024, cyclic)
    assert out2 is not None and "children" not in out2["rows"][0]


# ── (H) 부모 값 필드 — 얼마→얼마·변화율이 반환에 포함 ─────────────────────
def test_parent_value_fields_identity():
    out = decompose_change(_rows(FULL_CHAIN), "CFS:영업이익", 2024, BRIDGES)
    assert out is not None
    assert out["parent_prior"] == 100.0 and out["parent_current"] == 40.0
    assert out["parent_current"] - out["parent_prior"] == pytest.approx(out["delta"], abs=1.0)
    assert out["change_pct"] == -60.0  # -60/100


# ── (I) 세전이익 브리지 — 변형(금융만/금융·기타) 선택 ──────────────────────
def test_pretax_bridge_variant_selection():
    rows = _rows(
        {
            "법인세비용차감전순이익": {2023: 90.0, 2024: 10.0},
            "영업이익": {2023: 100.0, 2024: 40.0},
            "금융수익": {2023: 10.0, 2024: 12.0},
            "이자비용": {2023: 20.0, 2024: 42.0},
            # 기타 없음 → '금융만' 변형이 잔차 0으로 선택돼야 함
        }
    )
    out = decompose_change(rows, "CFS:법인세비용차감전순이익", 2024, BRIDGES)
    assert out is not None and out["variant"] == "금융만"
    assert out["residual"] == 0.0
    by_acct = {r["account"]: r for r in out["rows"]}
    assert by_acct["금융비용"]["delta"] == -22.0  # 이자비용 증가 → 음의 기여


# ── (J) 당기순이익 브리지 + 중첩 손자(세전→영업이익) 부호·기여율 ────────────
def test_net_income_bridge_and_nested_grandchildren():
    rows = _rows(
        {
            "당기순이익": {2023: 70.0, 2024: -10.0},
            "법인세비용차감전순이익": {2023: 90.0, 2024: 10.0},
            "법인세비용": {2023: 20.0, 2024: 20.0},
            "영업이익": {2023: 100.0, 2024: 40.0},
            "금융수익": {2023: 10.0, 2024: 12.0},
            "이자비용": {2023: 20.0, 2024: 42.0},
            "매출총이익": {2023: 300.0, 2024: 260.0},
            "판매비와관리비": {2023: 200.0, 2024: 220.0},
        }
    )
    out = decompose_change(rows, "CFS:당기순이익", 2024, BRIDGES)
    assert out is not None
    pretax_row = next(r for r in out["rows"] if r["account"] == "법인세비용차감전순이익")
    children = {c["account"]: c for c in pretax_row["children"]}
    op_row = children["영업이익"]
    assert op_row["delta"] == -60.0  # 손자 부호 최상위 기준 정렬
    # 손자의 손자(영업이익→매출총이익)도 펼침 + 기여율은 최상위 Δ(-80) 기준
    gp = {c["account"]: c for c in op_row["children"]}["매출총이익"]
    assert gp["delta"] == -40.0
    assert gp["contribution_pct"] == pytest.approx(-50.0, abs=0.1)  # -40/80


# ── (E) 분해 불가 케이스 — None 반환 ──────────────────────────────────────
def test_returns_none_without_bridge_or_prior():
    rows = _rows({"영업이익": {2024: 40.0}, "매출채권": {2023: 10.0, 2024: 20.0}})
    assert decompose_change(rows, "CFS:매출채권", 2024, BRIDGES) is None  # 브리지 없음
    assert decompose_change(rows, "CFS:영업이익", 2024, BRIDGES) is None  # 전기 없음
    assert decompose_change(rows, "(회사 전체)", 2024, BRIDGES) is None  # 접두 없음


# ── 반박 입력 공급 — 카드별 decomposition 키 포함(없으면 생략) ──────────────
def test_rebuttal_input_includes_decomposition():
    from src.report.rebuttal import build_rebuttal_input
    from src.schemas.findings import AccountFinding, IssueType

    def _card(account: str, key: str) -> AccountFinding:
        return AccountFinding(
            account=account,
            issue_type=IssueType.EARNINGS_TAX,
            materiality_score=1.0,
            anomaly_score=1.0,
            confidence="High",
            risk_level="High",
            cluster_key=key,
        )

    cards = [_card("CFS:영업이익", "acct:IS:영업이익"), _card("CFS:매출채권", "acct:BS:매출채권")]
    decomp = {"acct:IS:영업이익": {"variant": "표준", "delta": -60.0, "rows": []}}
    payload = build_rebuttal_input(cards, {}, decomp)
    assert payload[0]["decomposition"]["delta"] == -60.0  # 브리지 카드에 공급
    assert "decomposition" not in payload[1]  # 브리지 없는 카드는 키 생략


# ── 실데이터 — ifrs id계(판매 및 일반관리비) 회사 분해 잔차 ≤5% ─────────────
@pytest.mark.integration
def test_synonym_company_decomposition_real_data():
    """00356370: 판관비가 '판매 및 일반관리비' canonical — 슬롯 흡수로 결측 없이 분해."""

    rows = _load_cfs_is_series("00356370")
    years = sorted({r["year"] for r in rows if r["series_key"] == "CFS:영업이익"})
    if len(years) < 2:
        pytest.skip("로컬 00356370 정규화 데이터 2개년 미만")
    out = decompose_change(rows, "CFS:영업이익", years[-1], BRIDGES)
    assert out is not None
    by_acct = {r["account"]: r for r in out["rows"]}
    assert by_acct["판매비와관리비"]["delta"] is not None  # '결측' 회귀 금지
    assert abs(out["residual_pct"]) <= 5.0
    # 재귀 펼침 — 매출총이익이 블랙박스로 남지 않는다(매출·매출원가 children).
    gp_children = {c["account"] for c in by_acct["매출총이익"].get("children") or []}
    assert gp_children == {"매출", "매출원가"}


def _load_cfs_is_series(corp: str) -> list[dict]:
    import duckdb

    corp_dir = Path("data/companies") / corp
    rows: list[dict] = []
    for ydir in sorted(corp_dir.iterdir()) if corp_dir.is_dir() else []:
        db = ydir / "analysis.duckdb"
        if not (ydir.name.isdigit() and db.exists()):
            continue
        with duckdb.connect(str(db), read_only=True) as con:
            raw = con.execute(
                """
                select 'CFS:'||canonical, year, sum(amount) from normalized_financials
                where fs_div='CFS' and sj_div in ('IS','CIS') and canonical is not null
                group by 1, 2
                """
            ).fetchall()
        rows.extend({"series_key": r[0], "year": int(r[1]), "amount": float(r[2])} for r in raw)
    return rows


# ── 실데이터 — 삼성 CFS 영업이익 분해 잔차율 ≤1% ──────────────────────────
@pytest.mark.integration
def test_samsung_operating_income_decomposition():
    corp = "00126380"
    corp_dir = Path("data/companies") / corp
    import duckdb

    rows: list[dict] = []
    for ydir in sorted(corp_dir.iterdir()) if corp_dir.is_dir() else []:
        db = ydir / "analysis.duckdb"
        if not (ydir.name.isdigit() and db.exists()):
            continue
        with duckdb.connect(str(db), read_only=True) as con:
            raw = con.execute(
                """
                select 'CFS:'||canonical, year, sum(amount) from normalized_financials
                where fs_div='CFS' and sj_div in ('IS','CIS') and canonical is not null
                group by 1, 2
                """
            ).fetchall()
        rows.extend({"series_key": r[0], "year": int(r[1]), "amount": float(r[2])} for r in raw)
    years = sorted({r["year"] for r in rows if r["series_key"] == "CFS:영업이익"})
    if len(years) < 2:
        pytest.skip("로컬 삼성 정규화 데이터 2개년 미만")
    out = decompose_change(rows, "CFS:영업이익", years[-1], BRIDGES)
    assert out is not None
    assert abs(out["residual_pct"]) <= 1.0  # 미설명 잔차 ≤1%
