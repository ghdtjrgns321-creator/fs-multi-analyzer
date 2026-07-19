"""Build the company-level L4 integrated report payload."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from config.settings import settings
from src.analysis_tools import (
    load_normalized_financials,
    load_notes_classified,
    load_sce_equity_components,
)
from src.collect.opendart import DartCollector
from src.db.normalized import db_path
from src.normalize.mapper import OTHER_CANONICAL
from src.report.coverage import (
    build_coverage_ledger,
    build_derived_ledger,
    derived_layer_accounts,
    no_std_code_identities,
    build_note_ledger,
    build_sce_ledger,
    surfaced_note_facts,
)
from src.report.integrated import (
    build_review_queue,
    payload_for_summary,
    summarize_ratio_categories,
)
from src.report.series_normalize import normalize_presentation
from src.schemas.findings import AccountFinding
from src.signals.metrics_panel import (
    account_metrics_panel,
    sce_change_identity,
    sce_occurrence_states,
)
from src.signals.mvp1 import build_mvp1_signal_report
from src.signals.config import load_relationship_chains
from src.signals.ratios import build_ratio_report, load_ratio_config
from src.signals.red_flags import extract_red_flags
from src.signals.universal import UNIVERSAL_STATEMENTS, scan_cfs_ofs_gaps, scan_universal_signals

DEFAULT_CORP_CODE = "00126380"
DEFAULT_YEARS = [2022, 2023, 2024, 2025]


def build_company_report(
    corp_code: str = DEFAULT_CORP_CODE,
    years: list[int] | None = None,
    finding_report_path: Path | None = None,
    company_provider: Any | None = None,
) -> dict[str, object]:
    """Assemble deterministic L4 report inputs for one company."""

    # 분석 윈도우·target은 데이터에서 도출(§3: 연도 리터럴로 계산 구동 금지).
    # years 명시 시 그 윈도우를 존중하되, target은 항상 frame에 실재하는 최신 연도.
    # 2025 리터럴 고정 시 2025 미제출사는 전 신호가 빈값→LLM에 0건이 넘어가던 회귀를 차단.
    target_years = years or _available_norm_years(corp_code) or DEFAULT_YEARS
    frame = load_normalized_financials(corp_code, target_years)
    # 설계1: 표기변경 정규화 — 이후 보고서의 재표시 전기값을 권위로 부호 아티팩트 제거.
    # frame 차원에서 고쳐 신호·패널·시계열·분해가 전부 정규화된 값을 본다.
    frame, presentation_changes = normalize_presentation(frame)
    present_years = _present_years(frame)
    target_year = max(present_years) if present_years else max(target_years)
    company_profile = _company_profile(corp_code, company_provider)
    signal_report = build_mvp1_signal_report(frame, years=target_years)
    red_flags = extract_red_flags(signal_report, target_year)
    universal_signals = scan_universal_signals(frame, target_year)
    cfs_ofs_signals = scan_cfs_ofs_gaps(frame, target_year)
    ratios = build_ratio_report(frame, target_years)
    ratio_config = load_ratio_config()
    unmapped = _top_unmapped_material_accounts(frame, target_year)
    findings = _target_year_findings(
        load_findings_from_report(finding_report_path or Path("docs/agent/FINDING_REPORT.md")),
        target_year,
    )
    all_signals = red_flags + universal_signals + cfs_ofs_signals
    queue = build_review_queue(findings, ratios, ratio_config, target_year, all_signals, unmapped)
    # phase2: 전 계정 계산값(YoY·추세·변동성·비중·z 등)을 하나도 안 고르고 패널로 전달.
    # 코드는 순위를 정하지 않는다 — 무엇이 이상인지는 관점 LLM이 직접 판단한다(PLAN §3).
    account_series = _account_level_series(frame, target_years, target_year)
    metrics_panel = account_metrics_panel(
        account_series, _asset_by_fs_div(account_series, target_year), target_year
    )
    # 근본구조 C: 본문 셀 모집단 대조. 이유 없이 빠진 셀(unaccounted)=조용한 드롭 → 표면화.
    coverage_ledger = build_coverage_ledger(frame, account_series, target_years)
    # 파생층: 사슬·비율은 표준 계정명으로 조회하므로 미매핑 계정은 진입 불가. 계정층 원장에선
    # '분석됨'으로 세어져 안 보이던 몫을 따로 센다(조용한 드롭 차단).
    coverage_ledger["derived"] = build_derived_ledger(
        account_series,
        target_year,
        derived_layer_accounts(load_relationship_chains(), ratio_config),
        no_std_code_identities(frame),
    )
    # 주석 차원: detail+기타주석 전량을 분석 투입(흡수=본문중복·메타=비fact만 사실기반 제외).
    note_facts_raw = load_notes_classified(corp_code, [target_year]).to_dict("records")
    coverage_ledger["notes"] = build_note_ledger(note_facts_raw)
    note_facts = _compact_note_facts(surfaced_note_facts(note_facts_raw))
    # SCE 2D: 본문 ledger가 'SCE 2D가 상위 대체'로 미룬 실데이터를 전량 편입(자본변동×구성요소 셀).
    # SCE는 window 전체 로드(occurrence 판정에 다년 필요). ledger·compact는 target연도 셀 대상.
    sce_window = load_sce_equity_components(corp_code, target_years).to_dict("records")
    sce_raw = [r for r in sce_window if str(r.get("year")) == str(target_year)]
    coverage_ledger["sce"] = build_sce_ledger(sce_raw)
    sce_occ = sce_occurrence_states(sce_window, target_year)
    sce_cells = _compact_sce_cells(sce_raw, sce_occ)
    ratio_summary = summarize_ratio_categories(ratios, target_year)
    payload = payload_for_summary(queue, ratio_summary)
    latest_snapshot = _latest_signal_snapshot(signal_report, target_year)
    latest_snapshot["universal_scan"] = _signal_rows(universal_signals)
    latest_snapshot["cfs_ofs_gaps"] = _signal_rows(cfs_ofs_signals)
    return {
        "corp_code": corp_code,
        "company_name": _company_name(company_profile, corp_code),
        "business_domain": company_profile,
        "years": target_years,
        "target_year": target_year,
        "review_queue": [item.to_dict() for item in queue],
        "ratio_summary": ratio_summary,
        "ratio_time_series": _ratio_time_series(frame, target_years, ["CFS", "OFS"]),
        "account_level_series": account_series,
        "account_metrics_panel": metrics_panel,
        "latest_signal_snapshot": latest_snapshot,
        "unmapped_material_accounts": unmapped,
        "coverage_ledger": coverage_ledger,
        "note_facts": note_facts,
        "sce_cells": sce_cells,
        "presentation_changes": presentation_changes,
        "llm_payload": payload,
    }


def available_norm_years(corp_code: str) -> list[int]:
    """정규화 DB가 존재하는 사업연도 전체를 오름차순으로 발견(상한 없음).

    UI 연도 드롭다운의 데이터 원천. 연도를 회사 데이터에서 도출해 리터럴 고정을 제거한다(§3).
    """

    root = settings.data_dir
    cdir = root / corp_code
    if not cdir.is_dir():
        return []
    years: list[int] = []
    for path in cdir.iterdir():
        if (
            path.is_dir()
            and path.name.isdigit()
            and db_path(corp_code, int(path.name), root).exists()
        ):
            years.append(int(path.name))
    return sorted(years)


def _available_norm_years(corp_code: str) -> list[int]:
    """분석 기본 윈도우 — 정규화 DB 존재 연도 중 최신 4개(build_company_report 기본값)."""

    return available_norm_years(corp_code)[-4:]


def _present_years(frame: Any) -> list[int]:
    """frame에 실제 행이 있는 연도(target 후보)."""

    if frame is None or getattr(frame, "empty", True) or "year" not in frame.columns:
        return []
    out: list[int] = []
    for value in frame["year"].dropna().unique():
        try:
            out.append(int(value))
        except (TypeError, ValueError):
            continue
    return sorted(out)


def _company_profile(corp_code: str, company_provider: Any | None = None) -> dict[str, object]:
    provider = company_provider
    if provider is None:
        try:
            provider = DartCollector().company
        except Exception:
            return {"source": "OpenDART company profile unavailable", "corp_code": corp_code}
    try:
        profile = dict(provider(corp_code))
    except Exception:
        return {"source": "OpenDART company profile unavailable", "corp_code": corp_code}
    profile.setdefault("source", "OpenDART company profile")
    return profile


def _company_name(profile: dict[str, object], corp_code: str) -> str:
    for key in ("stock_name", "corp_name", "corp_name_eng"):
        value = str(profile.get(key, "")).strip()
        if value:
            return value
    return corp_code


def _latest_signal_snapshot(report: dict[str, object], target_year: int) -> dict[str, object]:
    return {
        "growth_divergences": _rows_for_year(report["growth_divergences"], target_year),
        "direction_checks": _rows_for_year(report["direction_checks"], target_year),
        "primary_yoy": _rows_for_year(report["primary_yoy"], target_year),
        "reference_yoy": _rows_for_year(report["reference_yoy"], target_year),
    }


def _rows_for_year(frame: Any, target_year: int) -> list[dict[str, object]]:
    if not hasattr(frame, "to_dict"):
        return []
    latest = frame[frame["year"] == target_year]
    return latest.to_dict(orient="records")


def _signal_rows(signals: list[Any]) -> list[dict[str, object]]:
    return [
        {
            "id": signal.id,
            "year": signal.year,
            "account": signal.account,
            "signal_type": signal.signal_type,
            "description": signal.description,
            "metric_value": signal.metric_value,
            "sj_div": signal.sj_div,
            "evidence": [item.model_dump(mode="json") for item in signal.evidence],
        }
        for signal in signals
    ]


def _ratio_time_series(
    frame: Any,
    years: list[int],
    fs_divs: list[str],
    ratio_fn: Any = None,
) -> list[dict[str, object]]:
    """비율 시계열을 fs_div별로 계산·태그(①②). 연결(CFS)만 내던 것을 별도(OFS)까지 열어,
    관점이 '연결 유동비율 vs 별도 유동비율'을 구분해 본다. computed 행만 싣는다."""

    if ratio_fn is None:
        from src.signals.ratios import build_ratio_report

        ratio_fn = build_ratio_report
    rows: list[dict[str, object]] = []
    for fs in fs_divs:
        report = ratio_fn(frame, years, None, fs)
        if not hasattr(report, "to_dict") or report.empty:
            continue
        scoped = report[report["status"] == "computed"].copy()
        if scoped.empty:
            continue
        scoped["fs_div"] = fs
        rows.extend(
            scoped[["fs_div", "id", "category", "name", "year", "value", "basis"]].to_dict(
                "records"
            )
        )
    rows.sort(key=lambda r: (str(r["fs_div"]), str(r["category"]), str(r["id"]), r["year"]))
    return rows


def _account_level_series(
    frame: Any,
    years: list[int],
    target_year: int,
) -> list[dict[str, object]]:
    # 개수상한 없음(결함① 수정): 강등 많은 금융사의 유의성 큰 계정이 상위 N개 밖으로
    # 밀려 LLM material에서 누락되던 갭. PLAN §3 — 코드가 개수로 미리 자르지 않고
    # 금액>0 계정 시계열을 전부 전달, 유의성 판단은 관점 에이전트가 한다.
    if not hasattr(frame, "to_dict") or frame.empty:
        return []
    # OFS 개방(B안): 연결(CFS)·별도(OFS)를 둘 다 1급 series로 싣는다. _primary_fs_div로
    # 연결만 통과하던 사각(별도 큰 변화 통째 누락)을 닫음. fs_div를 series_key에 접두해
    # 동명계정(차입금 등)이 연결·별도에서 한 시계열로 합산되는 이질병합을 차단한다.
    scoped = frame[
        (frame["fs_div"].isin(["CFS", "OFS"])) & (frame["sj_div"].isin(UNIVERSAL_STATEMENTS))
    ].copy()
    if scoped.empty:
        return []
    base_key = scoped["canonical"].where(
        scoped["canonical"].notna() & (scoped["canonical"] != ""),
        scoped["label"],
    )
    scoped["series_key"] = scoped["fs_div"].astype(str) + ":" + base_key.astype(str)
    # 명단=합집합(근본구조 A): target_year 잔액으로만 키를 뽑으면 "작년 컸다가 올해 사라진"
    # 계정이 통째 누락(소멸 사각). 윈도우 내 **어느 해든** 잔액>0이면 명단에 넣어, 신규·소멸을
    # 둘 다 살린다. 정렬은 연도별 최대 절대금액 내림차순(규모 큰 계정 우선).
    window_years = [int(year) for year in years]
    in_window = scoped[scoped["year"].astype(int).isin(window_years)].copy()
    in_window["abs_amount"] = in_window["amount"].abs()
    keys = (
        in_window[in_window["abs_amount"] > 0]
        .sort_values("abs_amount", ascending=False)["series_key"]
        .dropna()
        .drop_duplicates()
    )
    result = scoped[
        (scoped["series_key"].isin(keys)) & (scoped["year"].astype(int).isin(window_years))
    ].copy()
    result = result.sort_values(["sj_div", "series_key", "year"])
    columns = [
        "year",
        "fs_div",
        "sj_div",
        "series_key",
        "canonical",
        "label",
        "amount",
        "mapping_status",
    ]
    # 설계1 플래그(표기변경 정규화·재표시 후보)를 하류(패널·조사)로 전파.
    columns += [c for c in ("presentation_change", "restated_later") if c in result.columns]
    return result[columns].to_dict("records")


def _slim_dimensions(dimensions: object) -> str:
    """XBRL 축 문자열을 무손실 축약 — '...Axis=SeparateMember|...=SubsidiariesMember'
    → 'Separate·Subsidiaries'. 변별 토큰(member)은 보존, boilerplate(Axis=·Member)만 제거
    (panel_columnar식 표현 압축, 정보 손실 0). 대형사 note 토큰 ~34% 절감."""

    text = str(dimensions or "").strip()
    if not text:
        return ""
    parts: list[str] = []
    for segment in text.split("|"):
        token = segment.split("=", 1)[1] if "=" in segment else segment
        token = token.strip()
        if token.endswith("Member"):
            token = token[: -len("Member")]
        if token:
            parts.append(token)
    return "·".join(parts)


def _compact_note_facts(facts: list[dict]) -> list[dict[str, object]]:
    """주석 fact를 관점 LLM·근거검증용 compact 형태로(label·value·category·dimensions).
    concept(영문 local name)는 label_ko가 있어 제외 — 토큰 절감. dimensions는 무손실 축약."""

    compact: list[dict[str, object]] = []
    for fact in facts:
        compact.append(
            {
                "label": str(fact.get("label_ko", "")),
                "value": str(fact.get("value", "")),
                "category": str(fact.get("category", "")),
                "dimensions": _slim_dimensions(fact.get("dimensions")),
            }
        )
    return compact


def _compact_sce_cells(
    cells: list[dict], occurrence: dict[tuple[str, str], str] | None = None
) -> list[dict[str, object]]:
    """SCE 2D 셀을 관점·검증용 compact로(변동×구성요소×금액×fs_div). change=자본변동 사건
    (당기순이익·배당·유상증자·자기주식 등), component=자본 구성요소(자본금·이익잉여금 등).

    occurrence: (fs_div, change)별 신규/소멸 상태(사각#2·D18). 각 셀에 occurrence_state 부착하고,
    소멸(disappeared)한 변동종류는 target 셀이 없으므로 synthetic 셀로 표면화한다(§9 silent drop 금지)."""

    occ = occurrence or {}
    compact: list[dict[str, object]] = []
    present_keys: set[tuple[str, str]] = set()
    for cell in cells:
        amount = cell.get("amount")
        if amount is None:
            continue
        fs = str(cell.get("fs_div", ""))
        # 미매핑 강등행은 canonical이 '기타 중요 계정' 상수라 라벨로 복원해야 거래가 식별된다.
        change = sce_change_identity(cell)
        present_keys.add((fs, change))
        compact.append(
            {
                "fs_div": fs,
                "change": change,
                "component": str(cell.get("component_std") or cell.get("component_raw") or ""),
                "amount": amount,
                "prior_amount": cell.get("prior_amount"),
                "occurrence_state": occ.get((fs, change), "present"),
            }
        )
    # 소멸 변동종류(과거엔 있었으나 당기 셀 없음)를 synthetic으로 표면화 — 조용히 드롭 금지.
    for (fs, change), state in occ.items():
        if state == "disappeared" and (fs, change) not in present_keys:
            compact.append(
                {
                    "fs_div": fs,
                    "change": change,
                    "component": "(당기 소멸)",
                    "amount": 0.0,
                    "prior_amount": None,
                    "occurrence_state": "disappeared",
                }
            )
    return compact


def _asset_by_fs_div(rows: list[dict[str, object]], target_year: int) -> dict[str, float]:
    """fs_div별 자산총계(target 연도). OFS 계정 delta를 OFS 자산으로 나누기 위함
    (별도 계정을 연결 자산으로 정규화하는 스케일 오류 차단)."""

    out: dict[str, float] = {}
    for row in rows:
        if str(row.get("canonical")) == "자산총계" and int(row.get("year")) == int(target_year):  # type: ignore[arg-type]
            amount = row.get("amount")
            if amount is not None:
                out[str(row.get("fs_div", ""))] = abs(float(amount))  # type: ignore[arg-type]
    return out


def _top_unmapped_material_accounts(frame: Any, target_year: int) -> list[dict[str, object]]:
    if not hasattr(frame, "to_dict"):
        return []
    # 연결 없는 단일실체(OFS 전용)도 미매핑을 게시한다(§3: fs_div 리터럴 금지).
    # SCE(자본변동표)는 전용 2D 테이블이 담당(AGENDA_DD_SCE2D) → 합계행(기초·자본총계)이
    # "기타 중요 계정" 노이즈로 새지 않게 메인 unmapped material에서 제외.
    # 결함① 수정: ① mapping_status='unmapped_extension_account'만 보던 조건을
    #   canonical=='기타 중요 계정' 전체로 확대 — id_label_conflict로 강등된 핵심 계정
    #   (순이자손익 등 canonical='기타'인데 status가 달라 빠지던 케이스) 포함.
    # ② head(5) 개수상한 제거 — 강등 많은 금융사의 유의성 큰 계정이 상위 5개 밖으로
    #   밀려 누락되던 갭. 금액>0 전부 게시(유의성 판단은 관점 에이전트가 한다).
    # OFS 개방(B안): 별도(OFS) 미매핑 핵심계정도 게시한다(연결만 보던 사각 차단).
    scoped = frame[
        (frame["year"].astype(str) == str(target_year))
        & (frame["fs_div"].isin(["CFS", "OFS"]))
        & (frame["sj_div"] != "SCE")
        & (
            (frame["mapping_status"] == "unmapped_extension_account")
            | (frame["canonical"] == OTHER_CANONICAL)
        )
    ].copy()
    if scoped.empty:
        return []
    scoped["abs_amount"] = scoped["amount"].abs()
    scoped = scoped[scoped["abs_amount"] > 0].sort_values("abs_amount", ascending=False)
    return scoped[["year", "fs_div", "sj_div", "label", "account_id", "amount"]].to_dict("records")


def load_findings_from_report(path: Path) -> list[AccountFinding]:
    """Load AccountFinding JSON blocks from an existing markdown report."""

    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8")
    findings = []
    for block in re.findall(r"```json\s*(\{.*?\})\s*```", text, flags=re.S):
        try:
            findings.append(AccountFinding.model_validate(json.loads(block)))
        except Exception:
            continue
    return findings


def _target_year_findings(findings: list[AccountFinding], target_year: int) -> list[AccountFinding]:
    latest = []
    for finding in findings:
        evidence = finding.numeric_evidence + finding.note_evidence + finding.flow_evidence
        if any(item.year == str(target_year) for item in evidence):
            latest.append(finding)
    return latest


def render_markdown(report: dict[str, Any], summary: str | None = None) -> str:
    """Render the deterministic report for CLI/docs."""

    lines = ["# INTEGRATED_REPORT — L4 통합 리포트", ""]
    lines.append("## 검토 우선순위 큐")
    lines.append("| 순위 | 대상 | 유형 | risk | score | 핵심 근거 | 근거 | 출처 |")
    lines.append("|---:|---|---|---|---:|---|---|---|")
    for idx, item in enumerate(report["review_queue"][:10], start=1):
        basis = ", ".join(item["audit_basis"])
        source = item.get("source_url") or "-"
        lines.append(
            f"| {idx} | {item['subject']} | {item['item_type']} | {item['risk_level']} | "
            f"{float(item['materiality_score']):.2f} | {item['key_evidence']} | "
            f"{basis} | {source} |"
        )
    lines.extend(["", "## 회사 전체 지표 요약"])
    for category, values in report["ratio_summary"].items():
        joined = ", ".join(f"{name} {value:.2f}" for name, value in values.items())
        lines.append(f"- {category}: {joined}")
    lines.extend(["", "## 한 단락 종합"])
    lines.append(summary or "LLM 종합 문단은 보류했다.")
    return "\n".join(lines)


def main() -> None:
    report = build_company_report()
    print(render_markdown(report))


if __name__ == "__main__":
    main()
