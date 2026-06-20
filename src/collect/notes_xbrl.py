"""XBRL 기반 주석(notes) 수집 — singlnote 웹뷰어(8종 한정·소형사 빈응답)의 대안.

OpenDART finstate_xml로 사업보고서 XBRL zip을 받아 Arelle로 전개하면 본문 5표를 넘어
무형자산·차입금·관계기업·리스·충당부채·금융상품 등 비금융 주석 fact까지 얻을 수 있다.
계산·해석은 하지 않는다(L0 수집·관찰만). 검증 근거: data/backtest/AGENDA_DG_NOTES.md §6.
"""

from __future__ import annotations

import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from src.collect.opendart import AnnualReport, DartCollector


@dataclass(frozen=True)
class NoteFact:
    """XBRL 주석 fact 한 건(개념·라벨·기간·값·차원)."""

    concept: str
    label_ko: str
    label_en: str
    period: str
    unit: str
    value: str
    # context의 세그먼트·지역·자본구성요소 등 차원("축=멤버|축=멤버"). 없으면 빈 문자열.
    dimensions: str = ""


def _context_dimensions(context: object) -> str:
    """XBRL context.qnameDims → "축=멤버|축=멤버" 문자열(분식 세그먼트축 보존)."""

    qname_dims = getattr(context, "qnameDims", None)
    if not qname_dims:
        return ""
    parts: list[str] = []
    for dim_qname, dim_value in qname_dims.items():
        axis = dim_qname.localName
        try:
            if dim_value.isExplicit:
                member = dim_value.memberQname.localName
            else:
                typed = dim_value.typedMember
                member = typed.text if typed is not None else ""
        except Exception:  # noqa: BLE001 — 비정형 차원은 문자열로 보존
            member = str(dim_value)
        parts.append(f"{axis}={member}")
    return "|".join(parts)


def find_annual_report(
    collector: DartCollector, corp_code: str, year: int, search_window: int = 4
) -> AnnualReport | None:
    """해당 사업연도(year)의 최신 사업보고서를 찾는다(정정본 포함).

    분식 회사의 사업보고서는 사업연도+1년이 아니라 수년 뒤 정정으로 다시 제출되는 일이
    잦다. year+1 한 해만 보던 opendart.annual_report와 달리, year+1..year+window 구간을
    훑고 보고서명에 "(year.12)"가 들린 사업보고서 중 가장 최근(정정) 건을 고른다.
    """

    dart = collector._dart  # noqa: SLF001 (collect 내부 어댑터 재사용)
    frames = []
    for offset in range(1, search_window + 1):
        submitted = year + offset
        rows = dart.list(
            corp=corp_code,
            start=f"{submitted}0101",
            end=f"{submitted}1231",
            kind="A",
            final=True,
        )
        if rows is not None and not rows.empty:
            frames.append(rows)
    if not frames:
        return None

    reports = pd.concat(frames, ignore_index=True)
    name = reports["report_nm"].astype(str)
    mask = name.str.contains("사업보고서", regex=False) & name.str.contains(
        f"({year}.12)", regex=False
    )
    candidates = reports[mask].copy()
    if candidates.empty:
        return None

    row = candidates.sort_values("rcept_dt").iloc[-1]
    return AnnualReport(
        corp_code=corp_code,
        business_year=year,
        rcept_no=str(row["rcept_no"]),
        report_name=str(row["report_nm"]),
    )


def find_annual_reports_for_company(
    collector: DartCollector, corp_code: str, years: list[int], window: int = 5
) -> dict[int, AnnualReport]:
    """회사의 여러 사업연도 사업보고서를 list 1회로 매칭한다(전수 수집 API 절감).

    회사연도마다 list를 4회씩 부르면 전수에서 OpenDART 일일 한도(2만)를 넘는다.
    정기공시(kind=A)는 회사당 수십 건이라 한 번의 넓은 기간 조회로 전 연도를 덮는다.
    정정본을 포함해 사업연도별 최신 사업보고서를 고른다.
    """

    if not years:
        return {}
    dart = collector._dart  # noqa: SLF001
    yrs = sorted(years)
    try:
        rows = dart.list(
            corp=corp_code,
            start=f"{min(yrs) + 1}0101",
            end=f"{max(yrs) + window}1231",
            kind="A",
            final=True,
        )
    except ValueError:  # status 013 등 = 공시 없음
        return {}
    if rows is None or rows.empty or "report_nm" not in rows:
        return {}

    name = rows["report_nm"].astype(str)
    out: dict[int, AnnualReport] = {}
    for year in yrs:
        mask = name.str.contains("사업보고서", regex=False) & name.str.contains(
            f"({year}.12)", regex=False
        )
        candidates = rows[mask]
        if candidates.empty:
            continue
        row = candidates.sort_values("rcept_dt").iloc[-1]
        out[year] = AnnualReport(
            corp_code=corp_code,
            business_year=year,
            rcept_no=str(row["rcept_no"]),
            report_name=str(row["report_nm"]),
        )
    return out


def extract_note_facts(zip_path: Path) -> list[NoteFact]:
    """XBRL zip을 전개해 모든 fact를 추출한다(주석 포함).

    Arelle는 zip 직접 로드 시 IOerror가 나므로 추출 후 .xbrl 인스턴스를 직접 로드한다.
    taxonomy(.xsd)가 zip에 동봉돼 오프라인 로드가 가능하다.
    """

    from arelle import Cntlr  # 무거운 의존성 — 호출 시점에만 로드

    tmp = tempfile.mkdtemp()
    with zipfile.ZipFile(zip_path) as zf:
        zf.extractall(tmp)
    entries = list(Path(tmp).glob("*.xbrl"))
    if not entries:
        return []

    cntlr = Cntlr.Cntlr(logFileName="logToBuffer")
    model = cntlr.modelManager.load(str(entries[0]))
    if model is None or not getattr(model, "facts", None):
        return []

    facts: list[NoteFact] = []
    for f in model.facts:
        if f.concept is None or f.concept.qname is None:
            continue
        try:
            ko = f.concept.label(lang="ko") or ""
            en = f.concept.label(lang="en") or ""
        except Exception:  # noqa: BLE001 — 라벨 누락 fact는 빈 라벨로 보존
            ko = en = ""
        ctx = f.context
        period = ctx.endDatetime.date().isoformat() if ctx is not None and ctx.endDatetime else ""
        facts.append(
            NoteFact(
                concept=f.concept.qname.localName,
                label_ko=ko,
                label_en=en,
                period=period,
                unit=str(f.unitID or ""),
                value=(f.value or "")[:500],
                dimensions=_context_dimensions(ctx) if ctx is not None else "",
            )
        )
    cntlr.modelManager.close()
    return facts


def save_note_facts(facts: list[NoteFact], out_dir: Path) -> dict[str, int]:
    """추출한 주석 fact를 TSV로 저장하고 집계를 반환한다.

    원자적 쓰기(.tmp → os.replace): 재추출 중 종료돼도 기존 파일이 잘리지 않아 재개가 안전하다.
    """

    out_dir.mkdir(parents=True, exist_ok=True)
    frame = pd.DataFrame([f.__dict__ for f in facts])
    final = out_dir / "note_facts.tsv"
    tmp = out_dir / "note_facts.tsv.tmp"
    frame.to_csv(tmp, sep="\t", index=False, encoding="utf-8-sig")
    import os

    os.replace(tmp, final)  # 같은 볼륨 내 원자적 교체
    return {
        "fact_count": len(facts),
        "distinct_concepts": int(frame["concept"].nunique()) if not frame.empty else 0,
    }
