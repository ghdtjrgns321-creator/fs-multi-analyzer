"""정합성 점검 — 번역 품질·스케일·원천 적재(결정론, LLM 0회).

산술검산이 "옮긴 숫자끼리 아귀가 맞나"를 본다면 여기는 **"얼마나 못 읽었나"를 정량화**한다.
게이트가 통과/실패 이진이 아니라 번역 품질 리포트를 내도록 하는 축이다.

- 미매핑 비중: 자산총계 대비 미매핑 계정 합계. 절반만 읽은 회사를 분석하면 결론이 절반짜리다.
- ID-라벨 충돌: 영문 ID와 한글 라벨이 다른 계정을 가리키는 행 수(자본 1.4조 둔갑 사고의 유형).
- 표 커버리지: 재무제표 5종 중 실제로 적재된 표. 손익·재무상태표가 없으면 분석 자체가 불가.
- 부호 이상: 자산·부채 총계가 음수면 부호 규약을 잘못 옮긴 것이다.
- 원천 적재: 주석 XBRL·사업보고서 본문이 빈 껍데기인가(서술형 분석이 통째로 죽는 조건).

차단은 "분석이 성립하지 않는 상태"에만 건다. 나머지는 경고로 표면화한다(조용한 통과 금지).
"""

from __future__ import annotations

from pathlib import Path

import duckdb

CORE_STATEMENTS = ("BS", "IS")  # 없으면 분석 불가
ALL_STATEMENTS = ("BS", "IS", "CIS", "CF", "SCE")
UNMAPPED_STATUS = "unmapped_extension_account"
CONFLICT_STATUS = "id_label_conflict"


def _scalar(con: duckdb.DuckDBPyConnection, sql: str, params: list | None = None) -> float:
    row = con.execute(sql, params or []).fetchone()
    return float(row[0]) if row and row[0] is not None else 0.0


def unmapped_ratio(con: duckdb.DuckDBPyConnection) -> dict:
    """미매핑 계정 금액 / 자산총계. 자산총계가 없으면 비율 산정 불가(None)."""

    total = _scalar(
        con,
        "SELECT MAX(amount) FROM normalized_financials WHERE canonical = '자산총계' AND fs_div = 'CFS'",
    ) or _scalar(con, "SELECT MAX(amount) FROM normalized_financials WHERE canonical = '자산총계'")
    unmapped = _scalar(
        con,
        "SELECT SUM(ABS(amount)) FROM normalized_financials "
        "WHERE mapping_status = ? AND sj_div = 'BS' AND amount IS NOT NULL",
        [UNMAPPED_STATUS],
    )
    count = int(
        _scalar(
            con,
            "SELECT COUNT(*) FROM normalized_financials WHERE mapping_status = ?",
            [UNMAPPED_STATUS],
        )
    )
    # 금액 비중은 재무상태표 기준이라, 미매핑이 다른 표(특히 자본변동표)에 몰리면 안 보인다.
    # 표별 행 비중을 함께 낸다 — "이 표를 우리가 얼마나 못 읽었나".
    by_statement = {
        str(sj): {"unmapped": int(u), "rows": int(n), "share": (u / n) if n else None}
        for sj, u, n in con.execute(
            "SELECT sj_div, SUM(CASE WHEN mapping_status = ? THEN 1 ELSE 0 END), COUNT(*) "
            "FROM normalized_financials WHERE sj_div IS NOT NULL GROUP BY sj_div",
            [UNMAPPED_STATUS],
        ).fetchall()
    }
    ratio = (unmapped / total) if total else None
    return {
        "count": count,
        "amount": unmapped,
        "asset_total": total,
        "ratio": ratio,
        "by_statement": by_statement,
    }


def statement_coverage(con: duckdb.DuckDBPyConnection) -> dict:
    """적재된 재무제표 종류. 핵심 표(BS·IS) 결손은 분석 불가."""

    present = {
        str(r[0])
        for r in con.execute(
            "SELECT DISTINCT sj_div FROM normalized_financials WHERE sj_div IS NOT NULL"
        ).fetchall()
    }
    return {
        "present": sorted(present),
        "missing": [s for s in ALL_STATEMENTS if s not in present],
        "core_missing": [s for s in CORE_STATEMENTS if s not in present],
    }


def sign_anomalies(con: duckdb.DuckDBPyConnection) -> list[dict]:
    """총계 계정이 음수인 경우 — 부호 규약을 잘못 옮긴 신호(자본총계는 결손기업에서 정상 음수)."""

    rows = con.execute(
        "SELECT fs_div, canonical, SUM(amount) FROM normalized_financials "
        "WHERE canonical IN ('자산총계', '부채총계', '자본과부채총계') AND amount IS NOT NULL "
        "GROUP BY fs_div, canonical HAVING SUM(amount) < 0"
    ).fetchall()
    return [{"fs_div": str(f), "canonical": str(c), "amount": float(a)} for f, c, a in rows]


def sce_2d_quality(con: duckdb.DuckDBPyConnection) -> dict | None:
    """자본변동표 품질 — 분석이 실제로 쓰는 2D 테이블(sce_equity_components) 기준.

    normalized_financials의 SCE 행은 분석 경로가 아니다(커버리지 원장이 'SCE 2D가 상위 포함'으로
    제외) — 거기서 재면 미매핑이 2~3배 부풀거나 완전한 거짓 경고가 난다(2026-07-18 실측:
    0%짜리 회사가 88%로 보고됨). 미매핑 자본거래는 원문 라벨로 복원돼 흐르므로(sce_change_identity)
    분석 손실이 아니라 '표준분류 밖' 표시다."""

    exists = con.execute(
        "SELECT 1 FROM information_schema.tables WHERE table_name = 'sce_equity_components'"
    ).fetchone()
    if not exists:
        return None
    # leaf(실거래 변동)만 센다 — 기초/기말/재작성 마커('기초 보고금액' 등)는 거래가 아니라
    # 구조 라벨이고 role 기계가 이미 분류한다. 마커까지 세면 비율이 과대 표시된다(실측: 셀트리온
    # 10%가 전부 restated_begin 마커였음).
    cols = {r[0] for r in con.execute("DESCRIBE sce_equity_components").fetchall()}
    role_filter = "WHERE change_role = 'leaf'" if "change_role" in cols else ""
    rows = con.execute(
        f"SELECT change_status, COUNT(DISTINCT change_label) FROM sce_equity_components "
        f"{role_filter} GROUP BY change_status"
    ).fetchall()
    by_status = {str(s): int(n) for s, n in rows}
    total = sum(by_status.values())
    unmapped = by_status.get(UNMAPPED_STATUS, 0)
    return {
        "changes_total": total,
        "changes_unmapped": unmapped,
        "share": (unmapped / total) if total else None,
    }


def source_loaded(con: duckdb.DuckDBPyConnection) -> dict:
    """숫자 아닌 원천이 실제로 들어왔나 — 주석 XBRL·사업보고서 서술 추출 행 수."""

    def table_rows(name: str) -> int | None:
        exists = con.execute(
            "SELECT 1 FROM information_schema.tables WHERE table_name = ?", [name]
        ).fetchone()
        if not exists:
            return None
        return int(_scalar(con, f"SELECT COUNT(*) FROM {name}"))

    notes = table_rows("note_facts_classified")
    extracts = table_rows("report_extracts")
    return {
        "note_facts": notes,
        "report_extracts": extracts,
        "note_empty": not notes,
        "extracts_empty": not extracts,
    }


def quality_report(db: Path) -> dict:
    """번역 품질 리포트. passed=False는 '분석이 성립하지 않는 상태'에만."""

    if not db.exists():
        return {"passed": False, "reason": "DB 없음", "warnings": []}
    con = duckdb.connect(str(db), read_only=True)
    try:
        unmapped = unmapped_ratio(con)
        coverage = statement_coverage(con)
        signs = sign_anomalies(con)
        sources = source_loaded(con)
        sce = sce_2d_quality(con)
        conflicts = int(
            _scalar(
                con,
                "SELECT COUNT(*) FROM normalized_financials WHERE mapping_status = ?",
                [CONFLICT_STATUS],
            )
        )
    finally:
        con.close()

    blockers: list[str] = []
    if coverage["core_missing"]:
        blockers.append(f"핵심 표 결손 {coverage['core_missing']}")
    if signs:
        blockers.append(f"총계 부호 이상 {len(signs)}건")

    # 미매핑은 임계로 자르지 않는다 — 표준 계정에 못 붙은 것도 '기타 중요 계정'으로 분석에
    # 흐르므로 손실이 아니라 상태다. 자의적 컷 대신 수치를 그대로 게시한다(이관 손실은
    # transfer_ledger가 판정한다).
    warnings: list[str] = []
    ratio = unmapped["ratio"]
    if unmapped["count"]:
        share = f" · 자산총계 대비 {ratio:.1%}" if ratio is not None else ""
        warnings.append(
            f"표준 계정 미연결 {unmapped['count']}계정{share} — 기타 중요 계정으로 게시됨"
        )
    if conflicts:
        warnings.append(f"ID-한글명 충돌 {conflicts}행 — ID 채택, 충돌 기록 보존")
    if sce and sce["changes_unmapped"]:
        warnings.append(
            f"자본변동표 거래 {sce['changes_unmapped']}/{sce['changes_total']}종이 표준분류 밖"
            " — 원문 라벨로 분석엔 흐르나 표준 비교는 불가"
        )
    if coverage["missing"]:
        warnings.append(f"미적재 표 {coverage['missing']}")
    if sources["note_empty"]:
        warnings.append("주석 XBRL 0행 — 주석 관점 재료 없음")
    if sources["extracts_empty"]:
        warnings.append("사업보고서 서술 추출 0건 — 소송·특수관계 등 서술형 누락")

    return {
        "passed": not blockers,
        "blockers": blockers,
        "warnings": warnings,
        "unmapped": unmapped,
        "conflicts": conflicts,
        "coverage": coverage,
        "sign_anomalies": signs,
        "sources": sources,
        "sce_2d": sce,
    }
