"""G9 연도 간 대사 — 작년 보고서와 올해 보고서가 같은 말을 하나(합성 2개년 DB)."""

from __future__ import annotations

import duckdb

from src.normalize.gate_yoy import yoy_tieout

B = 1_000_000_000.0


def _make_db(path, rows):
    """rows = [(fs_div, sj_div, canonical, amount, prior_amount)]."""

    with duckdb.connect(str(path)) as con:
        con.execute(
            "CREATE TABLE normalized_financials (fs_div VARCHAR, sj_div VARCHAR, "
            "canonical VARCHAR, amount DOUBLE, prior_amount DOUBLE)"
        )
        for fs, sj, canonical, amount, prior in rows:
            con.execute(
                "INSERT INTO normalized_financials VALUES (?,?,?,?,?)",
                [fs, sj, canonical, amount, prior],
            )
    return path


def test_match_and_restated_split(tmp_path):
    prior_db = _make_db(
        tmp_path / "prior.duckdb",
        [("CFS", "BS", "재고자산", 100 * B, None), ("CFS", "BS", "무형자산", 50 * B, None)],
    )
    current_db = _make_db(
        tmp_path / "current.duckdb",
        [
            ("CFS", "BS", "재고자산", 110 * B, 100 * B),  # 올해 전기 칸 == 작년 당기
            ("CFS", "BS", "무형자산", 45 * B, 40 * B),  # 작년 50 → 올해 전기 40 = 재표시
        ],
    )
    r = yoy_tieout(current_db, prior_db)
    assert r["available"] is True
    assert r["match"] == 1
    assert len(r["restated"]) == 1
    assert r["restated"][0]["canonical"] == "무형자산"
    assert r["restated"][0]["diff"] == -10 * B


def test_sign_flip_is_presentation_not_restated(tmp_path):
    """절대값 동일·부호 반대는 표시 방법 변경 — 재표시로 세지 않는다(series_normalize 규칙)."""

    prior_db = _make_db(tmp_path / "p.duckdb", [("CFS", "CF", "투자활동현금흐름", -80 * B, None)])
    current_db = _make_db(
        tmp_path / "c.duckdb", [("CFS", "CF", "투자활동현금흐름", -90 * B, 80 * B)]
    )
    r = yoy_tieout(current_db, prior_db)
    assert r["presentation"] == 1
    assert r["restated"] == []


def test_prior_db_absent_is_unavailable_not_pass(tmp_path):
    """작년 DB 없음 = 대사 불가 — 통과로 둔갑 금지."""

    current_db = _make_db(tmp_path / "c.duckdb", [("CFS", "BS", "재고자산", 1 * B, 1 * B)])
    r = yoy_tieout(current_db, tmp_path / "nope.duckdb")
    assert r["available"] is False
    assert r["compared"] == 0


def test_other_canonical_bucket_excluded(tmp_path):
    """'기타 중요 계정'은 해마다 구성이 다른 버킷 — 합계 대사는 잡음이라 제외."""

    prior_db = _make_db(tmp_path / "p.duckdb", [("CFS", "BS", "기타 중요 계정", 100 * B, None)])
    current_db = _make_db(tmp_path / "c.duckdb", [("CFS", "BS", "기타 중요 계정", 5 * B, 3 * B)])
    r = yoy_tieout(current_db, prior_db)
    assert r["compared"] == 0


def test_account_only_in_one_year_skipped(tmp_path):
    """한 해에만 있는 계정은 교집합 밖 — 대사 대상 아님(신규/소멸은 occurrence 축 소관)."""

    prior_db = _make_db(tmp_path / "p.duckdb", [("CFS", "BS", "재고자산", 100 * B, None)])
    current_db = _make_db(tmp_path / "c.duckdb", [("CFS", "BS", "전환사채", 20 * B, 10 * B)])
    r = yoy_tieout(current_db, prior_db)
    assert r["compared"] == 0
    assert r["restated"] == []
