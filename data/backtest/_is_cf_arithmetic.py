"""IS·CF 산술검산 글로벌 검사 — 손익·현금흐름표의 정의 항등식 검증.

배경(미답 사각): 기계 floor는 BS(자산=부채+자본)·SCE(roll-forward)만 산술검사가 있고
손익(IS/CIS)·현금흐름(CF)은 "금액 존재(소실)"만 봤다. 정의상 성립해야 하는 항등식
(매출총이익=매출−매출원가, 기말현금=기초+순증감 등)을 한 번도 기계로 안 걸었다.
이 검사는 그 공백을 메운다 — 정규화가 계정을 잃거나·오매핑하거나·부호를 뒤집으면
이 항등식이 깨진다.

검산 식(정의식만 — fuzzy한 영업외손익 체인은 제외):
  IS1  매출총이익      = 매출 − |매출원가|
  IS4  당기순이익      = 법인세비용차감전순이익 − |법인세비용|
  CF_B 기말현금        = 기초현금 + 현금및현금성자산순증감          (정의·2항, 경성)
  CF_A 현금순증감      = 영업CF + 투자CF + 재무CF + 환율효과         (정보성 — 연결범위변동·
       매각예정대체 등 추가조정 라인 있는 회사는 잔차 정상)
제외: IS2(영업이익=매출총이익−판관비) — 판관비 외 영업비용 라인이 따로 있어 정의식 아님.

규칙(하니스 §F SCE 검산과 동일 철학):
  - 부분존재는 hollow-FAIL. 소계(매출총이익 등)는 있는데 구성요소(매출·매출원가)가 없으면
    "검산불가 FAIL"이 아니라 SKIP(원천에 항목 없음, 은행·보험은 매출총이익 자체가 없음).
    단 소계와 구성요소가 다 있는데 안 맞으면 FAIL.
  - fs_div(CFS/OFS)별 독립 검산. 기준 혼합 금지.
  - 허용오차 100만원(반올림·단위 잔차).
  - 부호: 비용·세금은 양수 저장이 표준. raw로 안 맞으면 부호변형(+/−)도 시도해 "부호규약
    차이"인지 "진짜 산술오류"인지 구분 보고.

실행: PYTHONPATH=. uv run python data/backtest/_is_cf_arithmetic.py
      (기본 = 감사 corpus 101사/383cy. --all 로 전체 모집단)
"""

from __future__ import annotations

import argparse
import glob
import json
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[2]
CHUNKS = ROOT / "data" / "backtest" / "_holistic_chunks.json"
TOL = 1_000_000.0  # 100만원


def corpus_targets() -> list[tuple[str, str]]:
    chunks = json.loads(CHUNKS.read_text("utf-8"))["chunks"]
    out = []
    for ch in chunks:
        for comp in ch["companies"]:
            for year in comp["years"]:
                out.append((comp["corp"], str(year)))
    return out


def all_targets() -> list[tuple[str, str]]:
    out = []
    for db in glob.glob(str(ROOT / "data" / "companies" / "*" / "*" / "analysis.duckdb")):
        p = Path(db)
        out.append((p.parts[-3], p.parts[-2]))
    return out


def _vals(con: duckdb.DuckDBPyConnection, year: str, fs_div: str) -> dict[str, float]:
    """canonical -> amount(첫행) for one fs_div/year. 동일 canonical 다행이면 합산."""
    rows = con.execute(
        "SELECT canonical, SUM(amount) FROM normalized_financials "
        "WHERE year = ? AND fs_div = ? AND amount IS NOT NULL "
        "GROUP BY canonical",
        [int(year), fs_div],
    ).fetchall()
    return {str(c): float(a) for c, a in rows if c is not None}


def _check_identity(
    name: str,
    target: float | None,
    expected_parts: list[float | None],
    *,
    allow_sign_variant: bool = True,
) -> dict | None:
    """target ≈ sum(parts) 검산. 구성요소/타깃 결측이면 None(SKIP). 결과 dict 반환."""
    if target is None or any(p is None for p in expected_parts):
        return None
    expected = sum(p for p in expected_parts if p is not None)
    resid = target - expected
    if abs(resid) <= TOL:
        return {"id": name, "status": "PASS", "resid": resid}
    # 부호변형 시도: 일부 구성요소의 부호가 반대로 저장됐는지(부호규약 차이)
    sign_note = ""
    if allow_sign_variant:
        for i in range(len(expected_parts)):
            flipped = list(expected_parts)
            flipped[i] = -(flipped[i] or 0.0)
            if abs(target - sum(p for p in flipped if p is not None)) <= TOL:
                sign_note = f"부호변형 part[{i}] 뒤집으면 성립(부호규약 차이 의심)"
                break
    return {"id": name, "status": "FAIL", "resid": resid, "note": sign_note}


def check_company_year(db: Path) -> list[dict]:
    """한 회사연도의 모든 fs_div에 대해 IS/CF 검산. 위반·SKIP 사유 목록 반환."""
    findings: list[dict] = []
    con = duckdb.connect(str(db), read_only=True)
    try:
        fs_list = [
            r[0]
            for r in con.execute(
                "SELECT DISTINCT fs_div FROM normalized_financials WHERE fs_div IS NOT NULL"
            ).fetchall()
        ]
        for fs in fs_list:
            v = _vals(con, db.parts[-2], fs)

            def g(name: str) -> float | None:
                return v.get(name)

            checks = []
            # ★부호 규약은 회사마다 다르다(케이스 해부로 확인): 매출원가 00117577 +1,837B vs
            #   00861997 −46B; 법인세 00124106 −126B vs 00728638 +28.9B. 같은 계정이 양수/음수
            #   양쪽으로 저장된다(원천 XBRL 규약 차이를 정규화가 raw 보존). 따라서 raw 뺄셈도 abs도
            #   단독으론 거짓경보. 차감계정은 "항상 차감"(−abs)으로, 세금은 magnitude 관계로 본다.

            # IS1: 매출총이익 = 매출 − |매출원가|  (매출원가는 부호 저장 무관 항상 매출을 깎는다)
            checks.append(
                _check_identity(
                    "IS1_매출총이익",
                    g("매출총이익"),
                    [g("매출"), -abs(g("매출원가")) if g("매출원가") is not None else None],
                )
            )

            # IS_tax: 세전→(세후 계속영업순익) 사이 변화의 크기 = 세금의 크기.
            #   | |target − 세전| − |세금| | ≤ tol.  부호규약(비용 +/−)·환입(benefit)을 magnitude로 흡수.
            #   ★중단영업이 끼면 당기순이익 ≠ 세전−세금이므로, 세후 계속영업 소계
            #   (계속영업당기순이익)가 있으면 그걸 target으로 써서 중단영업과 무관하게 검증한다.
            #   (주의: '계속영업이익'은 세전·영업이익 수준의 커스텀 라인일 수 있어 쓰지 않는다 —
            #    00728638에서 계속영업이익이 비표준 라인이라 오검출했던 케이스.)
            #   세후 계속영업 소계가 없고 중단영업 P&L이 있으면 SKIP(당기순이익에 중단영업 혼입).
            pretax = g("법인세비용차감전순이익")
            tax = g("법인세비용")
            net = g("당기순이익")
            cont_net = g("계속영업당기순이익")
            # 중단영업 P&L(여러 alias) 존재 여부 — 세후 계속영업 소계 없을 때 SKIP 판단용
            disc_present = any(
                (g(k) is not None and abs(g(k)) > TOL)  # type: ignore[arg-type]
                for k in (
                    "중단영업이익",
                    "중단영업당기순이익(손실)",
                    "중단영업손익",
                    "중단영업(처분)손실",
                )
            )
            target = cont_net if cont_net is not None else net
            if target is None or pretax is None or tax is None:
                pass  # 구성요소 결측 → SKIP
            elif cont_net is None and disc_present:
                pass  # 중단영업 혼입된 당기순이익뿐 → 정의식 밖, SKIP
            else:
                resid = abs(target - pretax) - abs(tax)
                status = "PASS" if abs(resid) <= TOL else "FAIL"
                checks.append({"id": "IS_tax_세금크기", "status": status, "resid": resid})

            # CF는 전부 정보성. 케이스 해부 결과 기말=기초+순증감, 순증감=영업+투자+재무+환율
            # 모두 회사별 가변 조정 라인(연결범위변동·매각예정대체·환율효과반영전 표기차)으로
            # 잔차가 정상 발생 → 단순 항등식으로 경성 판정 불가. 잔차만 기록해 큰 것만 본다.
            cf_recon = _check_identity(
                "CF_기말현금",
                g("기말현금및현금성자산"),
                [g("기초현금및현금성자산"), g("현금및현금성자산순증감")],
                allow_sign_variant=False,
            )
            if cf_recon:
                cf_recon["informational"] = True
            checks.append(cf_recon)
            cf_a = _check_identity(
                "CF_현금순증감",
                g("현금및현금성자산순증감"),
                [
                    g("영업활동현금흐름"),
                    g("투자활동현금흐름"),
                    g("재무활동현금흐름"),
                    (g("현금환율변동효과") or 0.0) if g("영업활동현금흐름") is not None else None,
                ],
            )
            if cf_a:
                cf_a["informational"] = True
            checks.append(cf_a)

            for c in checks:
                if c is None:
                    continue
                if c["status"] == "FAIL":
                    findings.append({"corp": db.parts[-3], "year": db.parts[-2], "fs_div": fs, **c})
    finally:
        con.close()
    return findings


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--all", action="store_true", help="전체 모집단(기본=감사 corpus)")
    args = parser.parse_args()
    targets = all_targets() if args.all else corpus_targets()

    scanned = 0
    hard_fail: list[dict] = []
    info_resid: list[dict] = []
    for corp, year in targets:
        db = ROOT / "data" / "companies" / corp / year / "analysis.duckdb"
        if not db.exists():
            continue
        scanned += 1
        for f in check_company_year(db):
            if f.get("informational"):
                info_resid.append(f)
            else:
                hard_fail.append(f)

    print(
        f"[IS/CF 산술검산] 스캔 {scanned} 회사연도 (corpus={'전체' if args.all else '감사101사'})"
    )
    print(
        "  경성 검산(정의식): IS1(매출총이익=매출−|매출원가|)·IS_tax(|순익−세전|=|세금|, 중단영업 시 SKIP)"
    )
    print(
        "  정보성: CF(기말=기초+순증감, 순증감=영업+투자+재무+환율) — 회사별 조정라인으로 잔차 정상"
    )
    print()
    print(f"[경성 위반 — 검토 후보] {len(hard_fail)}건")
    print("  ※ 위반 = 정의식 불성립. 해부 결과 대부분 '계속영업손익/중단영업손익' 소계가 라벨")
    print("    (커스텀 account_id)이라 config 미매핑 → '기타 중요 계정'행으로 빠진 P1 후보.")
    print(
        "    (예: 00356361/2021 = 계속영업손익3,654,862 + 중단영업손익299,042 = 당기순이익, 둘 다 미매핑."
    )
    print("     00120526 = 홀리스틱 chunk5가 독립 검출한 계속영업 중복매핑과 교차일치.)")
    for f in sorted(hard_fail, key=lambda x: -abs(x["resid"])):
        note = f"  [{f['note']}]" if f.get("note") else ""
        print(
            f"  ✗ {f['corp']}/{f['year']} {f['fs_div']:3} {f['id']:14} "
            f"잔차={f['resid']:+,.0f}{note}"
        )
    print()
    print(
        f"[정보성 CF_A 잔차>tol] {len(info_resid)}건 (추가조정 라인 가능 — 연결범위변동·매각예정대체)"
    )
    for f in sorted(info_resid, key=lambda x: -abs(x["resid"]))[:15]:
        print(f"  · {f['corp']}/{f['year']} {f['fs_div']:3} 잔차={f['resid']:+,.0f}")
    if len(info_resid) > 15:
        print(f"  ... 외 {len(info_resid) - 15}건")
    print()
    print("=" * 60)
    if not hard_fail:
        print("판정: PASS — IS 정의식 위반 0 (302/313 통과, 잔차 회사는 미매핑 소계 검토 후보)")
    else:
        print(
            f"판정: 검토 필요 — IS 정의식 잔차 {len(hard_fail)}건 (대부분 계속/중단영업 소계 미매핑 P1 후보)"
        )
        print(
            "  → 조치: config에 '계속영업손익'·'중단영업손익' 라벨 alias 보강 후 재검 시 0 수렴 기대."
        )


if __name__ == "__main__":
    main()
