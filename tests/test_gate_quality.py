"""G8 번역 품질 — 차단(분석 불가)과 경고(품질 저하)의 경계를 고정."""

from __future__ import annotations

import duckdb

from src.normalize.gate_quality import quality_report

B = 1_000_000_000.0
MAPPED = "exact_taxonomy_match"
UNMAPPED = "unmapped_extension_account"
CONFLICT = "id_label_conflict"


def _make_db(tmp_path, rows, *, notes=1, extracts=1):
    """rows = [(sj_div, canonical, amount, mapping_status)]."""

    db = tmp_path / "analysis.duckdb"
    with duckdb.connect(str(db)) as con:
        con.execute(
            "CREATE TABLE normalized_financials (corp_code VARCHAR, year VARCHAR, fs_div VARCHAR, "
            "sj_div VARCHAR, canonical VARCHAR, amount DOUBLE, mapping_status VARCHAR)"
        )
        for sj, canonical, amount, status in rows:
            con.execute(
                "INSERT INTO normalized_financials VALUES (?,?,?,?,?,?,?)",
                ["00000001", "2024", "CFS", sj, canonical, amount, status],
            )
        con.execute("CREATE TABLE note_facts_classified (x INTEGER)")
        for i in range(notes):
            con.execute("INSERT INTO note_facts_classified VALUES (?)", [i])
        con.execute("CREATE TABLE report_extracts (x INTEGER)")
        for i in range(extracts):
            con.execute("INSERT INTO report_extracts VALUES (?)", [i])
    return db


HEALTHY = [
    ("BS", "자산총계", 1000 * B, MAPPED),
    ("BS", "부채총계", 300 * B, MAPPED),
    ("IS", "매출", 500 * B, MAPPED),
]


def test_healthy_company_passes_without_warnings(tmp_path):
    report = quality_report(_make_db(tmp_path, HEALTHY))
    assert report["passed"] is True
    assert report["blockers"] == []


def test_missing_core_statement_blocks(tmp_path):
    """손익계산서가 없으면 분석 자체가 성립하지 않는다 — 차단."""

    rows = [r for r in HEALTHY if r[0] != "IS"]
    report = quality_report(_make_db(tmp_path, rows))
    assert report["passed"] is False
    assert any("핵심 표 결손" in b for b in report["blockers"])


def test_negative_total_blocks(tmp_path):
    """자산총계가 음수 = 부호를 잘못 옮긴 것."""

    rows = [("BS", "자산총계", -1000 * B, MAPPED), ("IS", "매출", 500 * B, MAPPED)]
    report = quality_report(_make_db(tmp_path, rows))
    assert report["passed"] is False
    assert any("부호 이상" in b for b in report["blockers"])


def test_large_unmapped_amount_blocks(tmp_path):
    """자산 대비 미매핑 금액이 20%를 넘으면 절반만 읽은 회사다 — 차단."""

    rows = [*HEALTHY, ("BS", "정체불명자산", 300 * B, UNMAPPED)]
    report = quality_report(_make_db(tmp_path, rows))
    assert report["passed"] is False
    assert any("미매핑 금액 비중" in b for b in report["blockers"])


def test_small_unmapped_warns_but_passes(tmp_path):
    """소액 미매핑은 차단이 아니라 경고 — '기타 중요 계정'으로 게시되기 때문."""

    rows = [*HEALTHY, ("BS", "정체불명자산", 80 * B, UNMAPPED)]
    report = quality_report(_make_db(tmp_path, rows))
    assert report["passed"] is True
    assert any("미매핑 금액 비중" in w for w in report["warnings"])


def test_statement_level_unmapped_share_warns(tmp_path):
    """금액이 작아도 한 표의 절반 이상이 미매핑이면 그 표를 못 읽은 것 — 표별로 경고."""

    rows = [*HEALTHY] + [("CF", f"현금흐름{i}", 1 * B, UNMAPPED) for i in range(3)]
    report = quality_report(_make_db(tmp_path, rows))
    assert any("CF 미매핑" in w for w in report["warnings"])


def test_sce_measured_on_2d_table_not_body_rows(tmp_path):
    """자본변동표는 분석이 쓰는 2D 테이블 기준 — 본문 SCE 행으로 재면 거짓 경고가 난다.

    본문 SCE 행이 전부 미매핑이어도(안 쓰는 표), 2D 테이블이 전부 매핑이면 경고 없어야 한다."""

    rows = [*HEALTHY] + [("SCE", f"자본변동{i}", 1 * B, UNMAPPED) for i in range(3)]
    db = _make_db(tmp_path, rows)
    with duckdb.connect(str(db)) as con:
        con.execute(
            "CREATE TABLE sce_equity_components (change_label VARCHAR, change_status VARCHAR)"
        )
        con.execute("INSERT INTO sce_equity_components VALUES ('배당', 'exact_taxonomy_match')")
    report = quality_report(db)
    assert not any("자본변동표" in w or "SCE" in w for w in report["warnings"])
    assert report["sce_2d"]["share"] == 0.0


def test_sce_2d_unmapped_majority_warns(tmp_path):
    """2D 테이블 기준으로 자본거래 절반 이상이 표준분류 밖이면 경고(원문 라벨로는 흐름)."""

    db = _make_db(tmp_path, HEALTHY)
    with duckdb.connect(str(db)) as con:
        con.execute(
            "CREATE TABLE sce_equity_components (change_label VARCHAR, change_status VARCHAR)"
        )
        for label, status in [
            ("자기주식 매입", UNMAPPED),
            ("전환사채의 조기상환", UNMAPPED),
            ("배당", "exact_taxonomy_match"),
        ]:
            con.execute("INSERT INTO sce_equity_components VALUES (?, ?)", [label, status])
    report = quality_report(db)
    assert any("표준분류 밖" in w for w in report["warnings"])


def test_conflict_rows_warn(tmp_path):
    rows = [*HEALTHY, ("BS", "발행사채", 10 * B, CONFLICT)]
    report = quality_report(_make_db(tmp_path, rows))
    assert any("ID-한글명 충돌" in w for w in report["warnings"])


def test_empty_sources_warn_not_block(tmp_path):
    """주석·본문이 비면 서술형 분석이 죽지만, 숫자 분석은 성립하므로 경고."""

    report = quality_report(_make_db(tmp_path, HEALTHY, notes=0, extracts=0))
    assert report["passed"] is True
    assert any("주석 XBRL 0행" in w for w in report["warnings"])
    assert any("서술 추출 0건" in w for w in report["warnings"])


def test_absent_db_is_not_pass(tmp_path):
    assert quality_report(tmp_path / "nope.duckdb")["passed"] is False
