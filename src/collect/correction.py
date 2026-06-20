"""S9 — 정정공시 이력 수집(데이터 출처: 원본/정정본 + 무엇이 바뀌었나).

분식 탐지가 아니라 **데이터 출처 정직성**이 목적이다. 우리가 가진 그 연도 재무가 나중에
재작성된 정정본인지, 무엇이 바뀌었는지를 메타로 남긴다.

A(list): `filings`에서 재무류 정정([기재정정]/[첨부정정] 사업/반기/분기보고서)을 파싱 → 어느 연도·
  언제·정정유형·과거연도 여부.
B(헤더): 정정 문서를 fetch해 맨 앞 정정신고 헤더(정정사유·정정 전/후)만 추출(본문 보고서는 버림).

저장: data/companies/{corp}/raw/corrections.json
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from pathlib import Path

import pandas as pd

from src.collect.opendart import DartCollector
from src.collect.storage import write_json

_FS_REPORT = re.compile(r"(사업보고서|반기보고서|분기보고서)")
_CORRECTION = re.compile(r"\[(기재정정|첨부정정|기타정정)\]")
_PERIOD = re.compile(r"\((\d{4})\.\d{2}\)")
# 정정 헤더 경계: 정정신고 섹션은 본문(대표이사 등의 확인) 직전까지.
# "사업보고서"는 정정대상/정정사유 텍스트에도 나오므로 경계로 쓰면 안 된다(조기 절단).
_HEADER_END = re.compile(r"대표이사\s*등의\s*확인|【\s*대표이사")
# 정정사유: "정정사항" 앞까지, 없으면 헤더 끝까지(헤더는 이미 본문 직전으로 bounded).
# "정정사유"/"정정 사유"(띄어쓰기 변형) 모두 허용.
_REASON = re.compile(r"정정\s*사유\s*:?\s*(.+?)(?:\s*(?:\d+\s*\.\s*)?정정\s*사항|$)", re.S)


@dataclass(frozen=True)
class Correction:
    """재무류 정정 1건(데이터 출처 메타)."""

    corp_code: str
    report_kind: str  # 사업보고서 | 반기보고서 | 분기보고서
    period_year: int  # 정정 대상 보고서의 사업연도
    period_label: str  # 예: 2021.12
    rcept_no: str
    rcept_dt: str  # 정정 재제출일 YYYYMMDD
    correction_type: str  # 기재정정 | 첨부정정 | 기타정정
    is_past_year: bool  # 재제출일 기준 2년+ 경과(과거연도 재작성 후보)
    correction_reason: str = ""  # B: 정정사유
    change_summary: str = ""  # B: 정정 전/후 요약(헤더 텍스트)


def parse_corrections(filings: pd.DataFrame | None, corp_code: str) -> list[Correction]:
    """filing 목록(DataFrame)에서 재무류 정정 레코드를 파싱한다(B 상세 없이)."""

    if filings is None or filings.empty:
        return []
    out: list[Correction] = []
    for _, row in filings.iterrows():
        name = str(row.get("report_nm", ""))
        ctype_match = _CORRECTION.search(name)
        fs_match = _FS_REPORT.search(name)
        if not ctype_match or not fs_match:
            continue
        kind = fs_match.group(1)
        rcept_dt = str(row.get("rcept_dt", ""))
        rcept_year = int(rcept_dt[:4]) if rcept_dt[:4].isdigit() else 0
        period_match = _PERIOD.search(name)
        period_year = int(period_match.group(1)) if period_match else 0
        period_label = period_match.group(0).strip("()") if period_match else ""
        is_past = bool(period_year and rcept_year and period_year <= rcept_year - 2)
        out.append(
            Correction(
                corp_code=corp_code,
                report_kind=kind,
                period_year=period_year,
                period_label=period_label,
                rcept_no=str(row.get("rcept_no", "")),
                rcept_dt=rcept_dt,
                correction_type=ctype_match.group(1),
                is_past_year=is_past,
            )
        )
    return out


def extract_correction_header(doc_text: str) -> dict[str, str]:
    """정정 문서 텍스트에서 정정신고 헤더(정정사유·정정 전/후 요약)만 추출.

    본문 보고서(대표이사 확인 이후)는 버린다. 헤더가 없으면 빈 값.
    """

    no_tags = re.sub(r"<[^>]+>", " ", doc_text)
    no_entities = re.sub(r"&[a-zA-Z]+;|&#\d+;", " ", no_tags)  # &cr; 등 DSD 엔티티 제거
    text = re.sub(r"\s+", " ", no_entities)
    start = text.find("정정대상")
    if start < 0:
        return {"correction_reason": "", "change_summary": ""}
    boundary = _HEADER_END.search(text, start + 4)
    header = text[start : boundary.start()] if boundary else text[start : start + 3000]
    reason_match = _REASON.search(header)
    reason = reason_match.group(1).strip()[:200] if reason_match else ""
    change_match = re.search(r"정정\s*사항", header)
    change = header[change_match.start() :].strip()[:2000] if change_match else ""
    return {"correction_reason": reason, "change_summary": change}


def load_corrections(corp_code: str, data_dir: Path) -> list[dict]:
    """저장된 corrections.json을 읽는다(없으면 빈 리스트)."""

    path = data_dir / corp_code / "raw" / "corrections.json"
    if not path.exists():
        return []
    import json

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    return list(payload.get("corrections", []) or [])


def restated_years(corp_code: str, data_dir: Path) -> set[int]:
    """재무제표가 재작성된(정정사유에 '재작성') 사업연도 집합.

    데이터 출처 플래그용: 이 연도 재무는 나중에 재작성된 정정본이다.
    """

    years: set[int] = set()
    for rec in load_corrections(corp_code, data_dir):
        reason = str(rec.get("correction_reason", ""))
        year = rec.get("period_year")
        if "재작성" in reason and isinstance(year, int) and year > 0:
            years.add(year)
    return years


def collect_corrections(
    collector: DartCollector,
    corp_code: str,
    start: str = "2016-01-01",
    end: str = "2024-12-31",
    with_detail: bool = True,
    past_year_only: bool = False,
    data_dir: Path | None = None,
) -> list[dict]:
    """A(list 정정 이력) + B(정정 헤더 상세) 수집 → corrections.json 저장.

    past_year_only=True면 과거연도 재작성만 B 상세 fetch(비용 절제).
    """

    corrections = parse_corrections(collector.filings(corp_code, start, end), corp_code)
    records: list[dict] = []
    for c in corrections:
        rec = asdict(c)
        want_detail = with_detail and (c.is_past_year or not past_year_only)
        if want_detail and c.rcept_no:
            header = extract_correction_header(collector.document(c.rcept_no))
            rec["correction_reason"] = header["correction_reason"]
            rec["change_summary"] = header["change_summary"]
        records.append(rec)

    if data_dir is not None:
        path = data_dir / corp_code / "raw" / "corrections.json"
        write_json({"corp_code": corp_code, "corrections": records}, path)
    return records
