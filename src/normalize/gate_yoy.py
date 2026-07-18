"""정합성 검문 — 연도 간 대사(작년 보고서와 올해 보고서가 같은 말을 하나).

올해 보고서의 "전기" 칸(prior_amount)과 작년 DB의 "당기"(amount)를 (fs_div, sj_div, canonical)
키로 맞댄다. 같은 값이 두 해 보고서에 적혀 있으므로 원칙적으로 일치해야 하고, 어긋남은 셋 중 하나다.

- 부호만 반대: 표시 방법 변경(presentation) — series_normalize가 최신 표기로 정규화하는 유형.
- 금액 상이: 재표시(restated) 또는 우리 정규화 드리프트 — 회사의 정당한 재작성(정정공시)일 수
  있어 **차단하지 않는다**(셀트리온 2019 연구개발비 소급·아스트 재고 정정이 실사례). 검토 재료로
  표면화만 한다(§9 — 조용히 통과도, 무고한 차단도 금지).
- 작년 DB 부재: 대사 불가 — "검산 못함"으로 구분(빈 검사 둔갑 금지).

로직 원형은 시계열 표기 정규화(src/report/series_normalize.py — LG생건 재표시 6건 포착)와 같고,
여기서는 게이트 시점에 회사 단위 요약을 낸다.
"""

from __future__ import annotations

from pathlib import Path

import duckdb

TOL = 1_000_000.0  # 100만원 — 게이트 공통 허용오차


def _amounts(db: Path, column: str) -> dict[tuple[str, str, str], float]:
    """(fs_div, sj_div, canonical) -> SUM(column). 결측 컬럼·DB 없음은 빈 dict."""

    if not db.exists():
        return {}
    with duckdb.connect(str(db), read_only=True) as con:
        cols = {r[0] for r in con.execute("DESCRIBE normalized_financials").fetchall()}
        if column not in cols:
            return {}
        rows = con.execute(
            f"SELECT fs_div, sj_div, canonical, SUM({column}) FROM normalized_financials "
            f"WHERE {column} IS NOT NULL GROUP BY fs_div, sj_div, canonical"
        ).fetchall()
    return {
        (str(f), str(s), str(c)): float(a) for f, s, c, a in rows if f is not None and c is not None
    }


def yoy_tieout(current_db: Path, prior_db: Path) -> dict:
    """올해 보고서의 전기 칸 vs 작년 DB의 당기 — 회사 단위 대사 요약.

    반환: {available, compared, match, presentation, restated:[{key, prior_db, current_prior, diff}…]}.
    작년 DB가 없으면 available=False(대사 불가 — 통과도 실패도 아님).
    """

    from src.normalize.mapper import OTHER_CANONICAL

    prior_said = _amounts(current_db, "prior_amount")  # 올해 보고서가 말하는 "전기"
    last_year = _amounts(prior_db, "amount")  # 작년 보고서가 말했던 "당기"
    if not last_year:
        return {"available": False, "compared": 0, "match": 0, "presentation": 0, "restated": []}
    # '기타 중요 계정'은 해마다 구성이 다른 버킷 — 합계 비교가 정체성 대사가 아니라 잡음이다.
    prior_said = {k: v for k, v in prior_said.items() if k[2] != OTHER_CANONICAL}

    match = presentation = 0
    restated: list[dict] = []
    for key, current_prior in prior_said.items():
        base = last_year.get(key)
        if base is None:
            continue  # 계정 구성이 해마다 달라질 수 있다 — 교집합만 대사
        diff = current_prior - base
        if abs(diff) <= TOL:
            match += 1
        elif abs(abs(current_prior) - abs(base)) <= TOL:
            presentation += 1  # 부호만 반대 — 표시 방법 변경
        else:
            restated.append(
                {
                    "fs_div": key[0],
                    "sj_div": key[1],
                    "canonical": key[2],
                    "prior_db": base,
                    "current_prior": current_prior,
                    "diff": diff,
                }
            )
    restated.sort(key=lambda r: -abs(r["diff"]))
    return {
        "available": True,
        "compared": match + presentation + len(restated),
        "match": match,
        "presentation": presentation,
        "restated": restated,
    }
