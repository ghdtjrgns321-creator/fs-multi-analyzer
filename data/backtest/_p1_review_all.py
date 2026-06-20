"""Phase1 전수 감사 배치 — 분식 회사연도 전수에 기계검사(바닥) + dump 생성(LLM 판단용).

전수 조사 원칙 강제: 대상은 known_cases.json의 positive·runnable run_years **전수**(대표·표본 금지).
각 회사연도: ① 데이터 완결성·항등식·주요표·순이익·주석 기계검사 PASS/FAIL ② _p1_company_review로
전체 dump를 _review_dumps/<corp>_<fy>.txt에 저장 → 에이전트가 전수로 읽고 판단. FAIL은 표에 강조.
dump 스크립트의 [기계요약](소실후보·병합)을 파싱해 표에 합산하고, 자식 크래시(returncode≠0)는
조용히 삼키지 않고 FAIL로 표기 + stderr를 dump 파일에 보존한다.

재현: PYTHONPATH=. uv run python data/backtest/_p1_review_all.py
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
from itertools import combinations
from pathlib import Path

import duckdb
import pandas as pd

from src.collect.storage import read_absence
from src.normalize.config import SceComponentMap, load_sce_components

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent  # data/backtest → 루트
REVIEW_SCRIPT = Path(__file__).resolve().parent / "_p1_company_review.py"
KC = PROJECT_ROOT / "data/backtest/known_cases.json"
DUMP_DIR = PROJECT_ROOT / "data/backtest/_review_dumps"
REQUIRED = ["normalized_financials", "sce_equity_components", "note_facts_classified"]
KNOWN_FS_ABSENCE = {"no_report", "dart_no_data"}
KNOWN_XBRL_ABSENCE = {"no_report", "dart_no_xbrl"}


@lru_cache(maxsize=1)
def _sce_component_map() -> SceComponentMap:
    return load_sce_components(PROJECT_ROOT / "config" / "canonical_accounts.yaml")


def _rounded_amount(value: object) -> int | None:
    if pd.isna(value):
        return None
    return round(float(value))


def _amounts_equal(left: float, right: float) -> bool:
    return round(float(left)) == round(float(right))


def _matches_any_component_subset(amount: float, others: pd.Series) -> bool:
    values = [
        float(value)
        for value in pd.to_numeric(others, errors="coerce").dropna().tolist()
        if not _amounts_equal(float(value), 0.0)
    ]
    if _amounts_equal(amount, 0.0) or not values:
        return False
    for size in range(1, len(values) + 1):
        for subset in combinations(values, size):
            if _amounts_equal(amount, sum(subset)):
                return True
    return False


def _drop_subtotal_like_unmatched_components(components: pd.DataFrame) -> pd.DataFrame:
    """Remove unmatched component columns that are numeric subtotals of sibling columns."""

    if components.empty:
        return components
    kept = components.copy()
    while True:
        remove_index = None
        for idx, row in kept[kept["component_role"].astype(str) == "unmatched"].iterrows():
            amount = _rounded_amount(row.get("amount"))
            if amount is None:
                continue
            sibling_components = kept.drop(index=idx)
            if _matches_any_component_subset(float(amount), sibling_components["amount"]):
                remove_index = idx
                break
        if remove_index is None:
            return kept
        kept = kept.drop(index=remove_index)


def sce_raw_conflict_count(sce_frame: pd.DataFrame) -> int:
    """Count source SCE contradictions between raw bare row and component-column sum."""

    if sce_frame.empty:
        return 0
    required = {
        "fs_div",
        "change_label",
        "account_id",
        "change_canonical",
        "component_std",
        "component_role",
        "amount",
    }
    if not required.issubset(sce_frame.columns):
        return 0
    comp_map = _sce_component_map()
    total = 0
    group_cols = ["fs_div", "change_label", "account_id"]
    for _, group in sce_frame.groupby(group_cols, dropna=False, sort=False):
        bare = group[
            (group["component_std"].astype(str) == "-")
            & (group["component_role"].astype(str) == "marker")
        ]
        components = group[
            (group["component_std"].astype(str) != "-")
            & (group["component_role"].astype(str).isin(["leaf", "unmatched", "composite"]))
        ]
        components = _drop_subtotal_like_unmatched_components(components)
        if bare.empty or components.empty:
            continue
        bare_amount = pd.to_numeric(bare["amount"], errors="coerce").dropna()
        component_amount = pd.to_numeric(components["amount"], errors="coerce").dropna()
        if bare_amount.empty or component_amount.empty:
            continue
        bare_sum = float(bare_amount.sum())
        component_sum = float(component_amount.sum())
        first = group.iloc[0]
        sign = comp_map.deduction_sign(
            str(first.get("change_canonical", "")),
            str(first.get("change_label", "")),
            str(first.get("account_id", "")),
        )
        if sign == "minus":
            matches = _amounts_equal(abs(bare_sum), abs(component_sum))
        else:
            matches = _amounts_equal(bare_sum, component_sum)
        if not matches:
            total += 1
    return total


def _data_root() -> Path:
    return PROJECT_ROOT / "data" / "companies"


def _missing_db_status(corp: str, fy: str) -> str:
    reason = read_absence(_data_root(), corp, fy).get("fs")
    if reason in KNOWN_FS_ABSENCE:
        return f"미제공({reason})"
    return "FAIL(DB없음·사유미상)"


def _missing_note_status(corp: str, fy: str) -> str | None:
    reason = read_absence(_data_root(), corp, fy).get("xbrl_zip")
    if reason in KNOWN_XBRL_ABSENCE:
        return f"미제공({reason})"
    return None


def load_targets(targets_path: Path | None = None) -> tuple[str, list[tuple[str, str]]]:
    """(이름, 회사연도 전수) — 기본은 정답지 positive·runnable, 라운드 검증은 표본 json.

    라운드 json(_round_sampler.py 산출)은 {"name", "cases": [{"corp_code", "run_years"}]} 형식.
    이름은 산출물 파일 접미사(_ALL_<name>.txt 등)로 쓰여 라운드 간 덮어쓰기를 막는다.
    """
    if targets_path is not None:
        payload = json.load(targets_path.open(encoding="utf-8"))
        out = [(c["corp_code"], str(y)) for c in payload["cases"] for y in c.get("run_years", [])]
        return str(payload.get("name", targets_path.stem)), out
    kc = json.load(KC.open(encoding="utf-8"))
    out = []
    for c in kc["cases"]:
        if c.get("label") == "positive" and c.get("runnable"):
            for y in c.get("run_years", []):
                out.append((c["corp_code"], str(y)))
    return "known", out


def _val(con, canon: str, fs: str) -> float | None:
    df = (
        con.execute(
            "SELECT amount FROM normalized_financials WHERE canonical=? AND fs_div=?",
            [canon, fs],
        )
        .fetchdf()["amount"]
        .dropna()
    )
    return float(df.iloc[0]) if not df.empty else None


def _parse_summary(dump: str) -> dict[str, int | str]:
    """dump의 [기계요약]에서 필드별 독립 파싱(순서·공백 변화에 강건). 실패는 '?'로 노출."""
    line = re.search(r"^\[기계요약\](.+)$", dump, re.MULTILINE)
    if not line:
        return {
            "소실": "?",
            "전기소실": "?",
            "병합": "?",
            "부호반전": "?",
            "원공시모순": "?",
            "SCE표준화": "?",
            "SCE검산": "?",
        }
    seg = line.group(1)

    def _int(key: str) -> int | str:
        m = re.search(rf"{key}=(\d+)", seg)
        return int(m.group(1)) if m else "?"

    def _tok(key: str) -> str:
        m = re.search(rf"{key}=(\S+)", seg)
        return m.group(1) if m else "?"

    return {
        "소실": _int("소실후보"),
        "전기소실": _int("전기소실"),
        "병합": _int("병합다중라벨"),
        "부호반전": _int("부호반전"),
        "원공시모순": _int("원공시모순"),
        "SCE표준화": _tok("SCE표준화"),
        "SCE검산": _tok("SCE검산"),
    }


# 판정 매트릭스 — LLM 통독의 산출물을 "셀 수 있는" 구조로 강제. 안 읽은 칸은 ⬜로 물리적으로
# 드러나고, _p1_verdict_gate.py가 빈칸·근거 누락을 기계로 센다(LLM 변동성 보완 1번 장치).
MATRIX_DIMS = [
    "A 완전성(§0·§0b·funnel)",
    "B 검산(§B 항등식·§F SCE)",
    "C 값정확(§D 소실·부호반전)",
    "D 분류(§C 미분류·§I 병합·오매핑)",
    "E 주석(§H 적재율·고가치축)",
    "F 시계열(§E 급변·결측)",
]


def matrix_path(name: str) -> Path:
    """라운드별 매트릭스 경로 — 기본(known)은 기존 파일명 유지, 라운드는 접미사로 격리."""
    suffix = "" if name == "known" else f"_{name}"
    return DUMP_DIR / f"_VERDICT_MATRIX{suffix}.md"


def write_matrix_template(tgts: list[tuple[str, str]], name: str = "known") -> Path:
    """회사연도×차원 판정 매트릭스 템플릿 생성(기존 작성본은 덮지 않음)."""
    path = matrix_path(name)
    if path.exists():
        # 덮지 않되 stale은 경고 — 정답지에 회사연도가 추가됐는데 매트릭스가 옛 것이면
        # 게이트 FAIL의 원인을 알 수 없게 된다(조용한 stale 금지)
        existing = set(
            re.findall(r"^## (\d{8}/\d{4})", path.read_text(encoding="utf-8"), re.MULTILINE)
        )
        missing = {f"{c}/{y}" for c, y in tgts} - existing
        if missing:
            print(f"⚠ 판정 매트릭스 stale — 누락 섹션 {sorted(missing)} (삭제 후 재생성 필요)")
        return path
    head = (
        "# Phase1 판정 매트릭스 — LLM 통독 산출물 (기계 게이트 대상)\n\n"
        "> 작성 규칙: 각 칸을 `- [x] 차원: 판정(정상/이상/관찰) — 근거: dump 인용`으로 채운다.\n"
        "> 빈 칸·근거 없는 판정은 `_p1_verdict_gate.py`가 FAIL로 센다. 전수 작성 전 통과 불가.\n"
    )
    body = []
    for corp, fy in tgts:
        body.append(f"\n## {corp}/{fy}\n")
        body.extend(f"- [ ] {dim}: \n" for dim in MATRIX_DIMS)
    path.write_text(head + "".join(body), encoding="utf-8")
    return path


def machine_checks(corp: str, fy: str) -> dict:
    """기계가 못 박는 바닥 검사(LLM 판단 이전). PASS/FAIL."""
    db = _data_root() / corp / fy / ("analysis" + ".duckdb")
    if not db.exists():
        return {"완결성": _missing_db_status(corp, fy)}
    con = duckdb.connect(str(db), read_only=True)
    tabs = {r[0] for r in con.execute("SHOW TABLES").fetchall()}
    res: dict = {}
    miss = []
    note_missing_known = None
    for t in REQUIRED:
        missing = t not in tabs or con.execute(f"SELECT count(*) FROM {t}").fetchone()[0] == 0  # noqa: S608
        if not missing:
            continue
        if t == "note_facts_classified":
            note_missing_known = _missing_note_status(corp, fy)
            if note_missing_known:
                continue
        miss.append(t)
    res["완결성"] = "OK" if not miss else f"FAIL{miss}"
    if not miss and note_missing_known:
        res["완결성"] = f"OK(주석{note_missing_known})"

    # 연결(CFS) 우선, 없으면 별도(OFS) — 별도전용 회사(세토피아) 거짓FAIL 방지
    def best(canon: str) -> float | None:
        cfs = _val(con, canon, "CFS")
        return cfs if cfs is not None else _val(con, canon, "OFS")

    a, li, eq = best("자산총계"), best("부채총계"), best("자본총계")
    res["항등식"] = "OK" if (None not in (a, li, eq) and abs(a - li - eq) < 1) else "FAIL"  # type: ignore[operator]
    sjs = {
        r[0] for r in con.execute("SELECT DISTINCT sj_div FROM normalized_financials").fetchall()
    }
    # 손익은 IS 또는 CIS(단일포괄손익계산서) 중 하나면 OK
    res["주요표"] = (
        "OK"
        if ({"BS", "CF"}.issubset(sjs) and ("IS" in sjs or "CIS" in sjs))
        else f"부분{sorted(sjs)}"
    )
    res["순이익"] = "OK" if best("당기순이익") is not None else "FAIL"
    nfc = (
        con.execute("SELECT count(*) FROM note_facts_classified").fetchone()[0]
        if "note_facts_classified" in tabs
        else note_missing_known or 0
    )
    res["주석행"] = nfc
    con.close()
    return res


def _process_one(corp: str, fy: str, env: dict[str, str]) -> tuple[str, str, dict, str]:
    c = machine_checks(corp, fy)
    # 전체 dump 생성(LLM 판단용) → 파일. 크래시는 삼키지 않는다(반쪽 dump가 정상 둔갑 금지)
    r = subprocess.run(
        [sys.executable, str(REVIEW_SCRIPT), corp, fy],
        capture_output=True,
        text=True,
        env=env,
        cwd=str(PROJECT_ROOT),
        encoding="utf-8",
    )
    dump = r.stdout or ""
    if r.returncode != 0:
        c["실행"] = f"FAIL(rc={r.returncode})"
        dump += f"\n\n⛔ dump 스크립트 비정상 종료 rc={r.returncode}\n--- stderr ---\n{r.stderr}"
    else:
        c["실행"] = "OK"
    # dump의 [기계요약] 파싱 — 소실·부호반전·병합·SCE 상태를 표로 끌어올림
    c.update(_parse_summary(dump))
    return corp, fy, c, dump


def main() -> None:
    DUMP_DIR.mkdir(parents=True, exist_ok=True)
    tpath = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    name, tgts = load_targets(tpath)
    env = {**os.environ, "PYTHONPATH": str(PROJECT_ROOT)}
    print(f"=== Phase1 전수 감사[{name}] — {len(tgts)} 회사연도 (대상 전수) ===\n")
    print(
        f"{'회사연도':16}{'완결성':>12}{'항등식':>7}{'주요표':>10}{'순이익':>10}{'주석행':>7}"
        f"{'소실':>6}{'전기소실':>10}{'반전':>6}{'병합':>6}{'원공시':>8}"
        f"{'SCE표준':>9}{'SCE검산':>16}{'실행':>12}"
    )
    fail_rows = []
    all_dumps = []
    max_workers = min((os.cpu_count() or 4), 16)
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        results = list(executor.map(lambda target: _process_one(target[0], target[1], env), tgts))
    for corp, fy, c, dump in results:
        (DUMP_DIR / f"{corp}_{fy}.txt").write_text(dump, encoding="utf-8")
        all_dumps.append(f"\n\n{'#' * 80}\n# {corp}/{fy}\n{'#' * 80}\n{dump}")
        any_fail = any(str(v).startswith("FAIL") for v in c.values())
        # 소실>0은 자동 FAIL이 아니라 정밀확인 대상(동일금액 우연일치 한계 — dump §D에서 LLM 판정).
        # 파싱실패("?")·SCE검산 불가도 조용히 넘기지 않는다(포맷 drift·hollow 위험).
        lost = c["소실"]
        prior_lost = c["전기소실"]
        if (
            any_fail
            or "부분" in str(c.get("주요표", ""))
            or lost == "?"
            or (isinstance(lost, int) and lost > 0)
            or prior_lost == "?"
            or (isinstance(prior_lost, int) and prior_lost > 0)
            or c.get("SCE검산") in ("불가", "?")
        ):
            fail_rows.append((corp, fy, c))
        print(
            f"{corp}/{fy:5}{c.get('완결성', '?'):>12}{c.get('항등식', '?'):>7}"
            f"{str(c.get('주요표', '?')):>10}{c.get('순이익', '?'):>10}{c.get('주석행', 0):>7}"
            f"{str(c.get('소실', '?')):>6}{str(c.get('전기소실', '?')):>10}"
            f"{str(c.get('부호반전', '?')):>6}{str(c.get('병합', '?')):>6}"
            f"{str(c.get('원공시모순', '?')):>8}{str(c.get('SCE표준화', '?')):>9}"
            f"{str(c.get('SCE검산', '?')):>16}"
            f"{c.get('실행', '?'):>12}"
        )
    all_name = "_ALL.txt" if name == "known" else f"_ALL_{name}.txt"
    (DUMP_DIR / all_name).write_text("".join(all_dumps), encoding="utf-8")
    matrix = write_matrix_template(tgts, name)
    print(f"\n전수 dump 저장: {DUMP_DIR}/ (개별 + {all_name})")
    if fail_rows:
        print(
            f"\n⛔ 기계검사 FAIL/부분/소실/검산불가 {len(fail_rows)}건 — 에이전트 정밀 확인 필요:"
        )
        for corp, fy, c in fail_rows:
            print(f"  {corp}/{fy}: {c}")
    else:
        print("\n기계검사 바닥 전수 PASS.")
    gate_arg = "" if tpath is None else f" {tpath}"
    print(
        f"\n[다음 단계 — LLM 통독은 주장이 아니라 산출물] {all_name}를 전수로 읽고 판정 매트릭스"
        f"({matrix})를 채운 뒤, `uv run python data/backtest/_p1_verdict_gate.py{gate_arg}`로"
        " 게이트 통과를 증명한다. 빈 칸·근거 없는 판정은 게이트가 FAIL로 센다."
    )


if __name__ == "__main__":
    main()
