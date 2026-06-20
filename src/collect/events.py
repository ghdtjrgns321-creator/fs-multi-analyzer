"""S10 — 주요사항보고서 event(35) + 정기보고서 주요정보 report(29) 수집·라우팅.

목적: DART의 시점 있는 결정 event(자본조달·distress·구조조정)와 정기보고서 구조화 정보를
완전 추출한다. 분식 탐지가 아니라 정보 완전성.

2경계(반드시 준수):
  ① 별도 참조 저장(raw/events.json·raw/reports.json) — 재무 정규화 DB에 안 섞는다(이중집계=오염).
  ② LLM에 통째로 안 준다 — 타입→관점 라우팅으로 compact 타임라인만 투입(토큰 차단).
가치 선별 주체: 코드(타입→관점 매핑, 전 회사 동일) + 관점 LLM(판단). 설계자 임의 화이트리스트 아님.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import yaml

from src.collect.opendart import DartCollector
from src.collect.storage import write_json

# 주요사항보고서 event 35종(OpenDartReader.event 유효 key_word).
EVENT_KEYWORDS = [
    "부도발생",
    "영업정지",
    "회생절차",
    "해산사유",
    "유상증자",
    "무상증자",
    "유무상증자",
    "감자",
    "관리절차개시",
    "소송",
    "해외상장결정",
    "해외상장폐지결정",
    "해외상장",
    "해외상장폐지",
    "전환사채발행",
    "신주인수권부사채발행",
    "교환사채발행",
    "관리절차중단",
    "조건부자본증권발행",
    "자산양수도",
    "타법인증권양도",
    "유형자산양도",
    "유형자산양수",
    "타법인증권양수",
    "영업양도",
    "영업양수",
    "자기주식취득신탁계약해지",
    "자기주식취득신탁계약체결",
    "자기주식처분",
    "자기주식취득",
    "주식교환",
    "회사분할합병",
    "회사분할",
    "회사합병",
    "사채권양수",
    "사채권양도결정",
]
# 정기보고서 주요정보 report 29종(OpenDartReader.report 유효 key_word).
REPORT_KEYWORDS = [
    "조건부자본증권미상환",
    "미등기임원보수",
    "회사채미상환",
    "단기사채미상환",
    "기업어음미상환",
    "채무증권발행",
    "사모자금사용",
    "공모자금사용",
    "임원전체보수승인",
    "임원전체보수유형",
    "주식총수",
    "회계감사",
    "감사용역",
    "회계감사용역계약",
    "사외이사",
    "신종자본증권미상환",
    "증자",
    "배당",
    "자기주식",
    "최대주주",
    "최대주주변동",
    "소액주주",
    "임원",
    "직원",
    "임원개인보수",
    "임원전체보수",
    "개인별보수",
    "타법인출자",
]

ROUTING_PATH = Path("config/playbooks/event_routing.yaml")
_DATE = re.compile(r"(\d{4})[.\-]?(\d{2})[.\-]?(\d{2})")
# 결정일/접수일 우선 컬럼(없으면 날짜형 값 스캔).
_DATE_COLS = ("bddd", "rcept_dt", "ast_t", "pymd")


def collect_events(
    collector: DartCollector,
    corp_code: str,
    start: str = "2016-01-01",
    end: str = "2024-12-31",
    data_dir: Path | None = None,
) -> dict[str, list[dict]]:
    """event 35종 전수 조회 → 비어있지 않은 것만 records. raw/events.json 저장(별도 참조)."""

    out: dict[str, list[dict]] = {}
    for kw in EVENT_KEYWORDS:
        frame = collector.event(corp_code, kw, start, end)
        if frame is not None and not frame.empty:
            out[kw] = frame.to_dict("records")
    if data_dir is not None:
        write_json(
            {"corp_code": corp_code, "events": out}, data_dir / corp_code / "raw" / "events.json"
        )
    return out


def collect_reports(
    collector: DartCollector,
    corp_code: str,
    years: tuple[int, ...],
    data_dir: Path | None = None,
) -> dict[str, list[dict]]:
    """report 29종 × 연도 전수 조회 → 비어있지 않은 것만. raw/reports.json 저장(별도 참조)."""

    out: dict[str, list[dict]] = {}
    for kw in REPORT_KEYWORDS:
        rows: list[dict] = []
        for year in years:
            frame = collector.report(corp_code, kw, year)
            if frame is not None and not frame.empty:
                rows.extend(frame.to_dict("records"))
        if rows:
            out[kw] = rows
    if data_dir is not None:
        write_json(
            {"corp_code": corp_code, "reports": out}, data_dir / corp_code / "raw" / "reports.json"
        )
    return out


def load_routing(path: Path = ROUTING_PATH) -> dict[str, str]:
    """event/report 종류 → 관점 매핑을 keyword→perspective 평탄 dict로 로드."""

    if not path.exists():
        return {}
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    flat: dict[str, str] = {}
    for section in ("event_routing", "report_routing"):
        for perspective, keywords in (payload.get(section, {}) or {}).items():
            for kw in keywords or []:
                flat[str(kw)] = str(perspective)
    return flat


def _event_date(record: dict) -> str:
    """record에서 대표 날짜(결정일/접수일) 추출. 없으면 날짜형 값 스캔."""

    for col in _DATE_COLS:
        val = str(record.get(col, "")).strip()
        if _DATE.search(val):
            return val
    for val in record.values():
        if _DATE.search(str(val)):
            return str(val).strip()
    return ""


# G4: 고가치 event 조건(terms) — DART 필드코드 → 사람이 읽는 라벨. present·non-empty만 전달.
# 자본조달(발행총액·전환가·리픽싱·자금용도)·자기주식(규모·방법)·합병(비율·상대)이 핵심.
# 전체 record 덤프 금지(토큰 차단), 이 whitelist만 = compact.
TERM_LABELS: dict[str, str] = {
    "bd_fta": "발행총액",
    "cv_prc": "전환가액",
    "ex_prc": "교환가액",
    "cv_rt": "전환비율",
    "ex_rt": "교환비율",
    "act_mktprcfl_cvprc_lwtrsprc": "리픽싱최저가",
    "bd_intr_ex": "표면이자율",
    "bd_intr_sf": "만기이자율",
    "fdpp_fclt": "자금용도_시설",
    "fdpp_bsninh": "자금용도_영업양수",
    "fdpp_op": "자금용도_운영",
    "fdpp_dtrp": "자금용도_채무상환",
    "fdpp_ocsa": "자금용도_타법인취득",
    "fdpp_etc": "자금용도_기타",
    "nstk_ostk_cnt": "신주수_보통",
    "fv_ps": "액면가",
    "aqpln_stk_ostk": "취득예정수량_보통",
    "aqpln_prc_ostk": "취득예정금액_보통",
    "aq_mth": "취득방법",
    "dppln_stk_ostk": "처분예정수량_보통",
    "mg_rt": "합병비율",
    "mgptncmp_cmpnm": "합병상대회사",
    "rbsnfdtl_tast": "상대_자산총계",
    "rbsnfdtl_sl": "상대_매출액",
}

_EMPTY_VALS = {"", "-", "nan", "None"}


def _event_terms(record: dict) -> dict[str, str]:
    """record에서 고가치 조건만 compact 추출(whitelist·present·non-empty)."""

    terms: dict[str, str] = {}
    for code, label in TERM_LABELS.items():
        val = str(record.get(code, "")).strip()
        if val and val not in _EMPTY_VALS:
            terms[label] = val
    return terms


def load_collected(corp_code: str, data_dir: Path, kind: str) -> dict[str, list[dict]]:
    """저장된 events.json/reports.json 로드(kind='events'|'reports'). 없으면 빈 dict."""

    path = data_dir / corp_code / "raw" / f"{kind}.json"
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return dict(payload.get(kind, {}) or {})


def routed_timeline(
    corp_code: str, data_dir: Path, routing_path: Path = ROUTING_PATH
) -> dict[str, list[dict]]:
    """수집된 event/report를 타입→관점으로 라우팅한 compact 타임라인.

    반환: {perspective: [{"type": kw, "date": date, "source": "event"|"report"}]}.
    비어있지 않은 것만(수집 단계에서 이미 필터됨). LLM 투입용 compact(토큰 bounded).
    """

    routing = load_routing(routing_path)
    timeline: dict[str, list[dict]] = {}
    for kind in ("events", "reports"):
        collected = load_collected(corp_code, data_dir, kind)
        source = "event" if kind == "events" else "report"
        for kw, records in collected.items():
            perspective = routing.get(kw)
            if not perspective:
                continue
            bucket = timeline.setdefault(perspective, [])
            for rec in records:
                bucket.append(
                    {
                        "type": kw,
                        "date": _event_date(rec),
                        "source": source,
                        "terms": _event_terms(rec) if source == "event" else {},
                    }
                )
    return timeline
