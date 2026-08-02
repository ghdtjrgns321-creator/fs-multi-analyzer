"""이관 원장 — 원본 항목이 전부 설명되는지(적재+사유제외+미설명 0) 판정하는 계약."""

from __future__ import annotations

import csv

import duckdb

from src.normalize.ledger_financials import financial_ledger, sce_transfer
from src.normalize.transfer_ledger import transfer_ledger

RAW_HEADER = ["sj_div", "account_id", "account_nm", "thstrm_amount"]


def _write_raw(ydir, rows, name="finstate_all_CFS.csv") -> None:
    raw = ydir / "raw"
    raw.mkdir(parents=True, exist_ok=True)
    with (raw / name).open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=RAW_HEADER)
        writer.writeheader()
        writer.writerows(rows)


def _write_db(ydir, rows, *, sce_cells=0) -> None:
    ydir.mkdir(parents=True, exist_ok=True)
    with duckdb.connect(str(ydir / "analysis.duckdb")) as con:
        con.execute(
            "CREATE TABLE normalized_financials (year INTEGER, fs_div VARCHAR, sj_div VARCHAR, "
            "account_id VARCHAR, label VARCHAR)"
        )
        for sj_div, account_id, label in rows:
            con.execute(
                "INSERT INTO normalized_financials VALUES (2024, 'CFS', ?, ?, ?)",
                [sj_div, account_id, label],
            )
        con.execute("CREATE TABLE sce_equity_components (x INTEGER)")
        for i in range(sce_cells):
            con.execute("INSERT INTO sce_equity_components VALUES (?)", [i])


def test_row_loaded_in_same_statement(tmp_path) -> None:
    ydir = tmp_path / "00000001" / "2024"
    _write_raw(
        ydir,
        [{"sj_div": "BS", "account_id": "a1", "account_nm": "자산총계", "thstrm_amount": "100"}],
    )
    _write_db(ydir, [("BS", "a1", "자산총계")])
    ledger = financial_ledger("00000001", "2024", tmp_path)
    assert ledger["total"] == 1
    assert ledger["loaded"] == 1
    assert ledger["unexplained"] == []


def test_row_moved_to_other_statement_is_explained(tmp_path) -> None:
    """포괄손익(CIS)에 실린 매출액이 손익계산서(IS)로 옮겨 담긴 것은 손실이 아니라 사유 있는 이관."""

    ydir = tmp_path / "00000002" / "2024"
    _write_raw(
        ydir,
        [{"sj_div": "CIS", "account_id": "rev", "account_nm": "매출액", "thstrm_amount": "500"}],
    )
    _write_db(ydir, [("IS", "rev", "매출액")])
    ledger = financial_ledger("00000002", "2024", tmp_path)
    assert ledger["loaded"] == 0
    assert sum(ledger["excluded"].values()) == 1
    assert ledger["unexplained"] == []


def test_row_absent_everywhere_is_unexplained(tmp_path) -> None:
    """원본에 있는데 어디에도 안 실린 행 = 미설명. 이게 1건이면 이관이 깨진 것이다."""

    ydir = tmp_path / "00000003" / "2024"
    _write_raw(
        ydir,
        [
            {"sj_div": "BS", "account_id": "a1", "account_nm": "자산총계", "thstrm_amount": "100"},
            {
                "sj_div": "BS",
                "account_id": "ghost",
                "account_nm": "사라진계정",
                "thstrm_amount": "70",
            },
        ],
    )
    _write_db(ydir, [("BS", "a1", "자산총계")])
    ledger = financial_ledger("00000003", "2024", tmp_path)
    assert [row["label"] for row in ledger["unexplained"]] == ["사라진계정"]
    assert transfer_ledger("00000003", "2024", tmp_path)["passed"] is False


def test_missing_raw_is_not_a_pass(tmp_path) -> None:
    """원본이 없으면 '이상 없음'이 아니라 '대조 못 함' — 빈 검사를 통과로 세지 않는다."""

    ydir = tmp_path / "00000004" / "2024"
    _write_db(ydir, [("BS", "a1", "자산총계")])
    ledger = transfer_ledger("00000004", "2024", tmp_path)
    assert ledger["passed"] is False
    assert "재무제표" in ledger["uncheckable"]


def test_sce_rows_need_2d_cells(tmp_path) -> None:
    """자본변동표 원본 행이 있는데 2D 셀이 0이면 분석 경로로 이관되지 않은 것 = 미설명."""

    ydir = tmp_path / "00000005" / "2024"
    _write_raw(
        ydir,
        [{"sj_div": "SCE", "account_id": "s1", "account_nm": "기초자본", "thstrm_amount": "10"}],
    )
    _write_db(ydir, [("SCE", "s1", "기초자본")], sce_cells=0)
    assert sce_transfer("00000005", "2024", tmp_path)["unexplained"] == 1

    filled = tmp_path / "00000006" / "2024"
    _write_raw(
        filled,
        [{"sj_div": "SCE", "account_id": "s1", "account_nm": "기초자본", "thstrm_amount": "10"}],
    )
    _write_db(filled, [("SCE", "s1", "기초자본")], sce_cells=3)
    assert sce_transfer("00000006", "2024", tmp_path)["unexplained"] == 0
