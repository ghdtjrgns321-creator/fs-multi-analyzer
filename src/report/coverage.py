"""커버리지 원장 — 분석 모집단 대조(근본구조 C).

§10 population-first·negative-space-proof를 런타임에 박는다. 분석 대상을 "골라 담기"가 아니라
"전체 셀 = 분석한 셀 + 제외사유 셀 + 미설명 셀"로 정합 강제한다. 미설명(이유 없이 빠진 셀)이
1건이라도 있으면 = 조용한 드롭 → 출력에 "미분석 N건"으로 드러나고 테스트가 실패한다.

이번 씨앗의 모집단 = normalized_financials 본문 셀(정규화 frame). 주석·SCE 2D는 별도 저장소라
이 원장 밖이며, SCE 본문행은 "제외: SCE 2D 별도표"로 분류한다(미설명 아님).
"""

from __future__ import annotations

from typing import Any

# 분석 명단(account_level_series)이 다루는 본문 statement. SCE는 메인에서 제외(2D 별도표 담당).
_BODY_STATEMENTS = ("BS", "IS", "CIS", "CF")
_FS_DIVS = ("CFS", "OFS")


def _base_key(canonical: Any, label: Any) -> str:
    """series_key 베이스 — _account_level_series와 동일 규칙(canonical 우선, 없으면 label)."""

    canon = "" if canonical is None else str(canonical)
    return canon if canon.strip() else ("" if label is None else str(label))


def _series_key(fs_div: Any, canonical: Any, label: Any) -> str:
    return f"{fs_div}:{_base_key(canonical, label)}"


def _real_amount(amount: Any) -> float | None:
    """실값(셀이 실재)만 통과 — None·NaN·0은 '값 없음'으로 본다. account_level_series의
    abs>0 키 선정과 같은 기준이라 NaN placeholder 행이 모집단/분석에 불일치로 새지 않는다."""

    if amount is None:
        return None
    try:
        value = float(amount)
    except (TypeError, ValueError):
        return None
    if value != value or value == 0:  # NaN 또는 0
        return None
    return value


def build_coverage_ledger(
    frame: Any,
    account_series: list[dict],
    years: list[int],
) -> dict[str, object]:
    """본문 셀 모집단을 분석셀과 대조한다. 반환 항등식:
    population_n == analyzed_n + len(excluded) + len(unaccounted).
    """

    window = {int(y) for y in years}

    # 모집단: frame 본문 셀(fs CFS/OFS, 윈도우 연도, 잔액>0). 셀 = (fs, sj, series_key, year).
    population: dict[tuple[str, str, str, int], str] = {}  # cell -> sj_div
    if hasattr(frame, "to_dict") and not frame.empty:
        for row in frame.to_dict("records"):
            fs = str(row.get("fs_div"))
            sj = str(row.get("sj_div"))
            year_raw = row.get("year")
            if fs not in _FS_DIVS or year_raw is None or _real_amount(row.get("amount")) is None:
                continue
            try:
                year = int(year_raw)
            except (TypeError, ValueError):
                continue
            if year not in window:
                continue
            key = (fs, sj, _series_key(fs, row.get("canonical"), row.get("label")), year)
            population[key] = sj

    # 분석셀: account_level_series의 잔액>0 셀.
    analyzed: set[tuple[str, str, str, int]] = set()
    for row in account_series or []:
        if _real_amount(row.get("amount")) is None:
            continue
        try:
            year = int(row.get("year"))  # type: ignore[arg-type]
        except (TypeError, ValueError):
            continue
        analyzed.add(
            (str(row.get("fs_div")), str(row.get("sj_div")), str(row.get("series_key")), year)
        )

    excluded: list[dict[str, object]] = []
    unaccounted: list[dict[str, object]] = []
    analyzed_n = 0
    for cell, sj in population.items():
        if cell in analyzed:
            analyzed_n += 1
        elif sj == "SCE":
            # SCE 본문행(붕괴 총계)은 sce_equity_components 2D 테이블이 상위 포함 → 정당제외(중복).
            excluded.append({"cell": list(cell), "reason": "SCE 2D 테이블이 상위 포함(superseded)"})
        elif sj not in _BODY_STATEMENTS:
            excluded.append({"cell": list(cell), "reason": f"본문 외 statement({sj})"})
        else:
            unaccounted.append({"cell": list(cell)})

    return {
        "population_n": len(population),
        "analyzed_n": analyzed_n,
        "excluded": excluded,
        "unaccounted": unaccounted,
        "reconciled": len(population) == analyzed_n + len(excluded) + len(unaccounted),
    }


# ── 주석(note) 차원 원장 ────────────────────────────────────────────────────
# 포함-기본값 원칙(제외규칙 단일화): 분석 모집단 = 전 fact. 정당제외는 **완전중복·비fact 2종뿐**.
# note_facts_classified는 적재(select_for_load) 단계서 이미 무차원흡수(완전중복)·메타를 제외했으므로,
# DB에 남은 fact(detail·기타주석·차원흡수)는 전부 net-new → 분석에 전량 투입(흡수도 차원 breakdown).


def build_note_ledger(note_facts: list[dict]) -> dict[str, object]:
    """주석 fact 모집단 대조. 적재본은 이미 정당제외(완전중복·메타) 상위적용 → surfaced=population.

    population == surfaced + excluded + unaccounted. (load 단계 제외는 상위 정당이라 여기선 0.)
    """

    population_n = len(note_facts or [])
    return {
        "population_n": population_n,
        "surfaced_n": population_n,  # 적재본 전량 surface(load가 정당제외 상위적용)
        "excluded": [],
        "excluded_by_reason": {},
        "unaccounted": [],
        "reconciled": True,
    }


def surfaced_note_facts(note_facts: list[dict]) -> list[dict]:
    """분석 투입 = 적재 note fact 전량. 차원흡수(부문·지역 breakdown=net-new)도 포함.
    무차원흡수(완전중복)·메타는 적재 단계서 이미 제외됨 — 분석층에서 추가로 자르지 않는다."""

    return list(note_facts or [])


def build_sce_ledger(sce_cells: list[dict]) -> dict[str, object]:
    """자본변동표(SCE) 2D 셀 원장. 본문 ledger가 'SCE 2D가 상위 대체'로 미뤄둔 실데이터를
    여기서 전량 surface(정당제외 없음 — 변동×구성요소 셀은 전부 net-new 재무정보)."""

    population_n = len(sce_cells or [])
    return {
        "population_n": population_n,
        "surfaced_n": population_n,
        "excluded": [],
        "unaccounted": [],
        "reconciled": True,
    }


# ── 파생 계산층 fs_div 커버리지 원장(③) ─────────────────────────────────────
# raw 계정층은 CFS+OFS 열렸는데(사각#1) 파생층(비율·주석)이 fs_div="CFS" 고정으로 빠졌다.
# "fs_div에 계정이 있으면 비율도 산출·표면화돼야 한다"는 음의공간 대조로 CFS-고정 누락을 전수 포착.


def _is_number(value: Any) -> bool:
    """None/NaN이 아닌 실수인가(비율 0도 유효하므로 _real_amount와 달리 0 허용)."""

    if value is None:
        return False
    try:
        number = float(value)
    except (TypeError, ValueError):
        return False
    return number == number  # not NaN


def build_fs_div_coverage(
    frame: Any,
    account_series: list[dict],
    years: list[int],
    target_year: int,
    report_ratio_fs_divs: set[str] | None = None,
    ratio_fn: Any = None,
) -> dict[str, object]:
    """파생층(비율) fs_div 커버리지. 각 fs_div에 계정이 있고 비율이 산출 가능(computable)한데
    리포트가 표면화 안 하면(surfaced=False) = gap. report_ratio_fs_divs=현재 리포트가 비율을 낸
    fs_div 집합(현재 파이프라인은 {CFS}). ratio_fn 주입으로 테스트."""

    if ratio_fn is None:
        from src.signals.ratios import build_ratio_report

        ratio_fn = build_ratio_report
    surfaced = report_ratio_fs_divs if report_ratio_fs_divs is not None else {"CFS"}
    target = int(target_year)

    population: set[str] = set()
    if hasattr(frame, "to_dict") and not frame.empty:
        for row in frame.to_dict("records"):
            fs = str(row.get("fs_div"))
            if fs in _FS_DIVS and _real_amount(row.get("amount")) is not None:
                population.add(fs)

    accounts_by_fs: dict[str, int] = {}
    for row in account_series or []:
        if _real_amount(row.get("amount")) is None:
            continue
        try:
            if int(row.get("year")) != target:  # type: ignore[arg-type]
                continue
        except (TypeError, ValueError):
            continue
        fs = str(row.get("fs_div"))
        accounts_by_fs[fs] = accounts_by_fs.get(fs, 0) + 1

    per: dict[str, dict] = {}
    gaps: list[dict] = []
    for fs in sorted(population):
        report = ratio_fn(frame, years, fs_div=fs)
        computable = 0
        if hasattr(report, "to_dict"):
            for row in report.to_dict("records"):
                try:
                    if int(row.get("year", -1)) != target:
                        continue
                except (TypeError, ValueError):
                    continue
                if _is_number(row.get("value")):
                    computable += 1
        accounts_n = accounts_by_fs.get(fs, 0)
        surfaced_fs = fs in surfaced
        per[fs] = {
            "accounts_n": accounts_n,
            "ratios_computable_n": computable,
            "ratios_surfaced": surfaced_fs,
        }
        if accounts_n > 0 and computable > 0 and not surfaced_fs:
            gaps.append({"fs_div": fs, "engine": "ratios", "computable": computable})

    return {"population_fs_div": sorted(population), "per_fs_div": per, "gaps": gaps}


# ── 파생층(관계사슬·재무비율) 원장 ──────────────────────────────────────────
# 계정층 원장은 "모든 셀이 패널에 들어갔나"만 잰다. 미매핑 계정도 원문 라벨을 키로 패널에는
# 들어가므로 거기선 '분석됨'으로 세어진다. 그런데 관계사슬·재무비율은 **표준 계정명**을 키로
# 조회하므로 미매핑 계정은 진입 자체가 불가능하다 → 계정층 원장만 보면 이 누락이 안 보인다
# (조용한 드롭). 여기서 그 몫을 따로 센다.


def derived_layer_accounts(chains: list[dict] | None, ratios: list[dict] | None) -> set[str]:
    """관계사슬·재무비율이 이름으로 조회하는 표준 계정 집합(파생층 진입 자격)."""

    names: set[str] = set()
    for chain in chains or []:
        for account in chain.get("chain") or []:
            name = str(account).strip()
            if name:
                names.add(name)
    for ratio in ratios or []:
        for account in ratio.get("accounts") or []:
            name = str(account).strip()
            if name:
                names.add(name)
    return names


def _is_unmapped(row: dict) -> bool:
    """미매핑 판정 — canonical이 비었거나 포괄버킷이거나 mapping_status가 미매핑."""

    from src.normalize.mapper import OTHER_CANONICAL, UNMAPPED

    canonical = str(row.get("canonical") or "").strip()
    return (
        not canonical
        or canonical == OTHER_CANONICAL
        or str(row.get("mapping_status") or "") == UNMAPPED
    )


def _derived_identity(row: dict) -> str:
    """파생층 모집단의 계정 정체성 — 미매핑은 원문 라벨로 복원해 병합을 푼다."""

    if _is_unmapped(row):
        label = str(row.get("label") or "").strip()
        if label:
            return f"{row.get('fs_div')}:{row.get('sj_div')}:{label}"
    return str(row.get("series_key") or "")


def no_std_code_identities(frame: Any) -> set[str]:
    """표준계정코드가 없는(별칭 제안 대상) 행의 파생층 정체성 집합.

    판정 기준은 alias_suggest.unmapped_accounts와 동일 — account_id가 '표준계정코드 미사용'
    이거나 빈 값. 표준코드를 가진 미매핑은 사전 누락이 아니라 강등이므로 여기 안 들어간다.
    """

    out: set[str] = set()
    if not hasattr(frame, "to_dict") or frame.empty:
        return out
    for row in frame.to_dict("records"):
        account_id = str(row.get("account_id") or "").strip()
        if account_id and "미사용" not in account_id:
            continue
        identity = _derived_identity(row)
        if identity:
            out.add(identity)
    return out


def build_derived_ledger(
    account_series: list[dict],
    target_year: int,
    covered_names: set[str],
    no_std_code: set[str] | None = None,
) -> dict[str, object]:
    """파생층 커버리지 — 계정층 분석 계정이 사슬·비율에 진입했나.

    모집단 = target_year 잔액>0 계정(계정층에서 이미 분석된 것). 항등식:
      population_n == entered_n + len(excluded) + len(blocked)

    blocked = **표준코드가 없어** 이름을 못 붙인 계정 — 별칭 제안기(alias_suggest)가 고칠 수
    있는 몫이라 그대로 교정 후보가 된다. no_std_code로 판별한다(alias_suggest.unmapped_accounts와
    같은 기준: account_id가 '표준계정코드 미사용'이거나 빈 값).
    excluded = ⓐ 표준 이름은 있으나 사슬·비율 정의에 없는 계정 ⓑ 표준코드는 있는데 강등된
    계정(중복 방지·표 불일치). ⓑ는 누락이 아니다 — 예: 삼성 '보통주자본금'은 '자본금' 총계가
    이미 매핑돼 이중계상을 막으려 강등된 것이고, 현금흐름표의 '당기순이익'은 손익계산서에서
    이미 진입한다. 이들을 누락으로 세면 과대계상이 된다.
    """

    from src.normalize.mapper import OTHER_CANONICAL, UNMAPPED

    # 정체성: 매핑된 계정은 series_key, **미매핑은 원문 라벨**(universal.py·metrics_panel.py와
    # 같은 규칙). series_key로 세면 미매핑이 전부 'fs:기타 중요 계정' 한 키로 병합돼 서로 다른
    # 계정 N종이 1건으로 과소 집계된다 — 원장이 재려던 바로 그 누락을 원장이 다시 숨기게 된다.
    seen: dict[str, dict] = {}
    for row in account_series or []:
        try:
            if int(row.get("year")) != int(target_year):  # type: ignore[arg-type]
                continue
        except (TypeError, ValueError):
            continue
        if _real_amount(row.get("amount")) is None:
            continue
        key = _derived_identity(row)
        if key and key not in seen:
            seen[key] = row

    entered: list[dict[str, object]] = []
    excluded: list[dict[str, object]] = []
    blocked: list[dict[str, object]] = []
    blocked_amount = 0.0
    for key, row in seen.items():
        canonical = str(row.get("canonical") or "").strip()
        if _is_unmapped(row):
            label = str(row.get("label") or "").strip()
            # 표준코드를 가진 미매핑은 사전 누락이 아니라 강등(중복 방지·표 불일치)이다.
            if no_std_code is not None and key not in no_std_code:
                excluded.append(
                    {
                        "account": key,
                        "canonical": label,
                        "reason": "표준코드 보유 — 중복 방지·표 불일치로 강등(누락 아님)",
                    }
                )
                continue
            if label in covered_names:
                excluded.append(
                    {
                        "account": key,
                        "canonical": label,
                        "reason": "동명 표준계정이 제 표에서 진입(표 간 중복 방지 강등)",
                    }
                )
                continue
            amount = abs(float(_real_amount(row.get("amount")) or 0.0))
            blocked_amount += amount
            blocked.append(
                {
                    "account": key,
                    "label": label,
                    "amount": amount,
                    "reason": "표준 계정명 없음(미매핑) — 이름 기반 조회 불가",
                }
            )
        elif canonical in covered_names:
            entered.append({"series_key": key, "canonical": canonical})
        else:
            excluded.append(
                {
                    "series_key": key,
                    "canonical": canonical,
                    "reason": "사슬·비율 정의에 없는 계정",
                }
            )

    population_n = len(seen)
    return {
        "population_n": population_n,
        "entered_n": len(entered),
        "excluded": excluded,
        "blocked": blocked,
        "blocked_amount": round(blocked_amount, 2),
        "reconciled": population_n == len(entered) + len(excluded) + len(blocked),
    }


__all__ = [
    "build_coverage_ledger",
    "build_derived_ledger",
    "build_fs_div_coverage",
    "build_note_ledger",
    "build_sce_ledger",
    "derived_layer_accounts",
    "no_std_code_identities",
    "surfaced_note_facts",
]
