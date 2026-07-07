# 사업보고서 해체 엔진 — 구현 플랜

> **For agentic workers:** 이 플랜은 TDD 태스크 단위로 구현한다. 설계 단일출처:
> [DISCLOSURE_DECOMPOSITION_DESIGN.md](DISCLOSURE_DECOMPOSITION_DESIGN.md). 스텝은 `- [ ]` 체크박스로 추적.

**Goal:** raw 사업보고서(business_report.xml)를 결정론으로 해체해 "주제 폴더 + 커버리지 장부"로 만든다.

**Architecture:** report_parts가 PART를 자르고(기존), 새 splitter가 PART를 subsection으로 쪼갠다. section_router가
subsection 제목을 config YAML 패턴으로 주제에 라우팅하고, 매칭 실패·"해당없음"을 커버리지 장부 항등식으로 감시한다.
판단(LLM)은 없다 — 전부 결정론. UI·수집·Phase2 배선은 Plan B(후속).

**Tech Stack:** Python 3.11, PyYAML, pytest, 기존 `src/notes/report_parts.py`(BeautifulSoup PART 슬라이스).

## Global Constraints

- 스코프 = 제조업 한정. 금융업 비범위.
- 하드코딩 금지 — 주제 매핑은 `config/playbooks/report_section_routing.yaml`(ripple-search 대상).
- 한글 파일 U+FFFD 0(mojibake 금지). YAML은 `allow_unicode=True`.
- include-by-default: 매칭 실패 subsection은 버리지 말고 "기타"로 surface. "무시"는 내용이 "해당없음"인 것만.
- 실측 표본 = 대주(00112457)·삼성(00126380) 2024 `data/companies/{corp}/2024/raw/report_doc/business_report.xml`.
- 계산-LLM 분리: 이 플랜은 전부 결정론(LLM 호출 0).

---

## File Structure

| 파일                                                  | 책임                                                                            |
| ----------------------------------------------------- | ------------------------------------------------------------------------------- |
| `config/playbooks/report_section_routing.yaml` (생성) | 주제→제목패턴 매핑 데이터(§6 표 operational)                                    |
| `src/notes/report_parts.py` (수정)                    | `split_subsections(part)` 추가 — PART 텍스트를 "N. 제목" 경계로 subsection 분할 |
| `src/report/section_router.py` (생성)                 | 라우팅 로직 + 커버리지 장부(loader·route·ledger)                                |
| `tests/test_section_router.py` (생성)                 | 단위 + 실데이터 2사 통합 테스트                                                 |

**데이터 구조(Produces — 후속 태스크가 의존):**
- `SubSection` = dataclass(numeral:str, index:int, title:str, text:str) — 예: ("II", 2, "주요 제품 및 서비스", "...")
- `RoutingResult` = dataclass(routed:dict[str,list[SubSection]], ignored:list[SubSection], other:list[SubSection], ledger:dict)
- `route_report(parts:list[ReportPart]) -> RoutingResult`

---

### Task 1: 주제 라우팅 config YAML + 로더

**Files:**
- Create: `config/playbooks/report_section_routing.yaml`
- Create: `src/report/section_router.py`
- Test: `tests/test_section_router.py`

**Interfaces:**
- Produces: `load_routing(path=DEFAULT_ROUTING_PATH) -> dict`, `DEFAULT_ROUTING_PATH: Path`

- [ ] **Step 1: config YAML 생성**

`config/playbooks/report_section_routing.yaml`:

```yaml
# 사업보고서 subsection 제목 → 주제 폴더 라우팅. 설계 §6(2사 전수판정 근거).
# 순서 = 우선순위(먼저 매칭되는 주제 채택). 패턴 = 제목 부분문자열(소문자·공백무시 비교).
# 미매칭 subsection은 "기타"로 surface(버리지 않음). 스코프: 제조업.
topics:
  audit_opinion_icfr: ["감사의견", "내부통제", "회계감사인"]
  sanctions_regulatory: ["제재"]
  contingency_related_party:
    ["우발", "특수관계", "대주주", "계열회사", "채무보증", "지급보증", "최대주주", "주주에 관한", "이사회", "임원", "연혁"]
  liability_liquidity: ["위험관리", "파생", "유동성", "자금조달", "차입"]
  equity_capital: ["자본금 변동", "주식의 총수", "자기주식", "정관"]
  revenue_receivables: ["매출", "수주", "주요 제품", "제품 및 서비스"]
  cost_inventory: ["원재료", "생산설비", "생산 및 설비"]
  asset_valuation: ["연구개발", "무형자산", "손상"]
  earnings_tax: ["법인세", "손익"]
  cash_flow: ["현금흐름"]
  mgmt_discussion: ["경영진단", "재무상태 및 영업실적", "예측정보"]
  company_topic: ["회사의 개요", "신용평가", "사업의 개요"]
# 무시(정당제외)는 내용이 "해당없음"일 때 코드가 판정 — 제목 기반 아님(§9).
```

- [ ] **Step 2: 실패 테스트 작성**

`tests/test_section_router.py`:

```python
from pathlib import Path
from src.report.section_router import load_routing, DEFAULT_ROUTING_PATH


def test_load_routing_has_topics():
    routing = load_routing()
    assert "topics" in routing
    assert "revenue_receivables" in routing["topics"]
    assert "매출" in routing["topics"]["revenue_receivables"]
    assert DEFAULT_ROUTING_PATH.exists()
```

- [ ] **Step 3: 테스트 실패 확인**

Run: `uv run pytest tests/test_section_router.py::test_load_routing_has_topics -v`
Expected: FAIL (ModuleNotFoundError: section_router)

- [ ] **Step 4: 최소 구현**

`src/report/section_router.py`:

```python
"""사업보고서 subsection을 주제 폴더로 결정론 라우팅 + 커버리지 장부.

판단(LLM) 없음 — 제목 패턴(config YAML) 매칭만. 미매칭은 "기타"로 surface, "해당없음"은 정당제외.
설계 §6·§8·§9(DISCLOSURE_DECOMPOSITION_DESIGN.md).
"""

from __future__ import annotations

from pathlib import Path

import yaml

DEFAULT_ROUTING_PATH = Path("config/playbooks/report_section_routing.yaml")


def load_routing(path: Path = DEFAULT_ROUTING_PATH) -> dict:
    """주제→제목패턴 매핑 YAML 로드(없으면 빈 topics)."""

    if not path.exists():
        return {"topics": {}}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {"topics": {}}
```

- [ ] **Step 5: 테스트 통과 확인**

Run: `uv run pytest tests/test_section_router.py::test_load_routing_has_topics -v`
Expected: PASS

- [ ] **Step 6: 커밋**

```bash
git add config/playbooks/report_section_routing.yaml src/report/section_router.py tests/test_section_router.py
git commit -m "feat(decomp): 섹션→주제 라우팅 config YAML + 로더"
```

---

### Task 2: PART → subsection 분할기 (report_parts 확장)

**Files:**
- Modify: `src/notes/report_parts.py`
- Test: `tests/test_section_router.py`

**Interfaces:**
- Consumes: `ReportPart(numeral, title, text)` (기존)
- Produces: `SubSection(numeral:str, index:int, title:str, text:str)`, `split_subsections(part:ReportPart) -> list[SubSection]`

- [ ] **Step 1: 실패 테스트 작성** (`tests/test_section_router.py`에 추가)

```python
from src.notes.report_parts import ReportPart, SubSection, split_subsections


def test_split_subsections_by_numbered_heading():
    part = ReportPart(numeral="I", title="I. 회사의 개요",
                      text="1. 회사의 개요\n가나다 본문\n2. 회사의 연혁\n라마바 본문\n3. 자본금 변동사항\n사아자")
    subs = split_subsections(part)
    assert [s.index for s in subs] == [1, 2, 3]
    assert subs[0].title == "회사의 개요"
    assert "가나다" in subs[0].text
    assert subs[1].title == "회사의 연혁"
    assert subs[2].numeral == "I"


def test_split_subsections_ignores_table_number_cells():
    # 표 셀의 순수 숫자("1", "2,000")는 heading으로 오인하지 않는다.
    part = ReportPart(numeral="X", title="X", text="1. 진짜 제목\n1\n2,000,000\n내용")
    subs = split_subsections(part)
    assert len(subs) == 1
    assert subs[0].title == "진짜 제목"
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `uv run pytest tests/test_section_router.py -k split_subsections -v`
Expected: FAIL (ImportError: SubSection)

- [ ] **Step 3: 최소 구현** (`src/notes/report_parts.py`에 추가)

```python
# 파일 상단 import에 추가할 것: (이미 re, dataclass 있음)

# 최상위 subsection 헤더 = 줄 시작 "N. " + 한글/영문 제목(숫자만인 표 셀 제외).
_SUBSECTION_HEADER = re.compile(r"^(\d+)\.\s+([가-힣A-Za-z].*)$")


@dataclass(frozen=True)
class SubSection:
    """PART 하위 subsection 한 개(예: II.2 주요 제품)."""

    numeral: str
    index: int
    title: str
    text: str


def split_subsections(part: "ReportPart") -> list["SubSection"]:
    """PART 본문을 최상위 'N. 제목' 경계로 subsection 분할.

    헤더 없으면 전체를 index=0 단일 subsection으로(graceful). 표 셀의 순수 숫자는 헤더 아님.
    """

    lines = part.text.splitlines()
    marks: list[tuple[int, int, str]] = []  # (line_idx, sub_index, title)
    for i, line in enumerate(lines):
        m = _SUBSECTION_HEADER.match(line.strip())
        if m:
            marks.append((i, int(m.group(1)), m.group(2).strip()))
    if not marks:
        return [SubSection(part.numeral, 0, part.title, part.text)]

    subs: list[SubSection] = []
    for k, (line_idx, sub_index, title) in enumerate(marks):
        end = marks[k + 1][0] if k + 1 < len(marks) else len(lines)
        body = "\n".join(lines[line_idx + 1 : end]).strip()
        subs.append(SubSection(part.numeral, sub_index, title, body))
    return subs
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `uv run pytest tests/test_section_router.py -k split_subsections -v`
Expected: PASS (2 passed)

- [ ] **Step 5: 커밋**

```bash
git add src/notes/report_parts.py tests/test_section_router.py
git commit -m "feat(decomp): PART→subsection 분할기(N. 제목 경계)"
```

---

### Task 3: subsection → 주제 라우팅 + "해당없음" 정당제외

**Files:**
- Modify: `src/report/section_router.py`
- Test: `tests/test_section_router.py`

**Interfaces:**
- Consumes: `SubSection`, `load_routing()`
- Produces: `route_title(title:str, routing:dict) -> str | None`, `is_empty_section(text:str) -> bool`

- [ ] **Step 1: 실패 테스트 작성**

```python
from src.report.section_router import route_title, is_empty_section


def test_route_title_matches_topic():
    routing = load_routing()
    assert route_title("주요 제품 및 서비스", routing) == "revenue_receivables"
    assert route_title("자본금 변동사항", routing) == "equity_capital"
    assert route_title("우발부채 등에 관한 사항", routing) == "contingency_related_party"


def test_route_title_unmatched_returns_none():
    assert route_title("듣도보도 못한 제목", load_routing()) is None


def test_is_empty_section_detects_해당없음():
    assert is_empty_section("- 해당사항 없음") is True
    assert is_empty_section("해당사항이 없습니다.") is True
    assert is_empty_section("소송가액 100억원 계류 중") is False
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `uv run pytest tests/test_section_router.py -k "route_title or empty_section" -v`
Expected: FAIL (ImportError)

- [ ] **Step 3: 최소 구현** (`section_router.py`에 추가)

```python
import re as _re

_EMPTY_PATTERNS = ("해당사항 없음", "해당사항이 없습니다", "해당 사항 없음", "해당사항없음", "해당없음")


def _norm(text: str) -> str:
    """공백 제거·소문자 — 제목 부분문자열 비교용."""

    return _re.sub(r"\s+", "", text).lower()


def route_title(title: str, routing: dict) -> str | None:
    """제목이 매칭되는 첫 주제 반환(우선순위=YAML 순서). 미매칭 None."""

    norm_title = _norm(title)
    for topic, patterns in (routing.get("topics") or {}).items():
        if any(_norm(p) in norm_title for p in patterns):
            return topic
    return None


def is_empty_section(text: str) -> bool:
    """본문이 사실상 '해당없음'이면 True(정당제외 대상). 짧고 해당없음 문구면 빈 섹션."""

    stripped = text.strip()
    if not stripped:
        return True
    compact = _norm(stripped)
    return len(compact) < 40 and any(_norm(p) in compact for p in _EMPTY_PATTERNS)
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `uv run pytest tests/test_section_router.py -k "route_title or empty_section" -v`
Expected: PASS (3 passed)

- [ ] **Step 5: 커밋**

```bash
git add src/report/section_router.py tests/test_section_router.py
git commit -m "feat(decomp): 제목→주제 라우팅 + 해당없음 정당제외 판정"
```

---

### Task 4: route_report + 커버리지 장부 항등식

**Files:**
- Modify: `src/report/section_router.py`
- Test: `tests/test_section_router.py`

**Interfaces:**
- Consumes: `split_subsections`, `route_title`, `is_empty_section`, `ReportPart`
- Produces: `RoutingResult`, `route_report(parts:list[ReportPart], routing:dict|None=None) -> RoutingResult`

- [ ] **Step 1: 실패 테스트 작성**

```python
from dataclasses import dataclass as _dc
from src.notes.report_parts import ReportPart
from src.report.section_router import route_report


def _part(numeral, title, text):
    return ReportPart(numeral=numeral, title=title, text=text)


def test_route_report_ledger_identity():
    parts = [
        _part("II", "II. 사업의 내용", "2. 주요 제품 및 서비스\n매출 표\n9. 없는주제\n내용"),
        _part("XI", "XI. 투자자 보호", "1. 공시내용 진행 및 변경사항\n- 해당사항 없음"),
    ]
    result = route_report(parts)
    total = result.ledger["population"]
    accounted = result.ledger["routed"] + result.ledger["ignored"] + result.ledger["other"]
    assert total == accounted  # 항등식: 모집단 = 라우팅 + 정당제외 + 기타
    assert "revenue_receivables" in result.routed  # II.2 → 매출
    assert any(s.title.startswith("없는주제") for s in result.other)  # 미매칭 → 기타
    assert any("공시내용" in s.title for s in result.ignored)  # 해당없음 → 정당제외
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `uv run pytest tests/test_section_router.py -k route_report -v`
Expected: FAIL (ImportError: route_report)

- [ ] **Step 3: 최소 구현** (`section_router.py`에 추가)

```python
from dataclasses import dataclass, field

from src.notes.report_parts import ReportPart, SubSection, split_subsections


@dataclass
class RoutingResult:
    """해체 결과 — 주제별 폴더 + 정당제외 + 기타 + 장부."""

    routed: dict[str, list[SubSection]] = field(default_factory=dict)
    ignored: list[SubSection] = field(default_factory=list)  # 해당없음(정당제외)
    other: list[SubSection] = field(default_factory=list)  # 미매칭(기타)
    ledger: dict = field(default_factory=dict)


def route_report(parts: list[ReportPart], routing: dict | None = None) -> RoutingResult:
    """PART들을 subsection으로 쪼개 주제 폴더에 라우팅 + 커버리지 장부 항등식 산출."""

    routing = routing if routing is not None else load_routing()
    result = RoutingResult()
    population = 0
    for part in parts:
        for sub in split_subsections(part):
            population += 1
            if is_empty_section(sub.text):
                result.ignored.append(sub)
                continue
            topic = route_title(sub.title, routing)
            if topic is None:
                result.other.append(sub)
            else:
                result.routed.setdefault(topic, []).append(sub)
    routed_count = sum(len(v) for v in result.routed.values())
    result.ledger = {
        "population": population,
        "routed": routed_count,
        "ignored": len(result.ignored),
        "other": len(result.other),
        "identity_ok": population == routed_count + len(result.ignored) + len(result.other),
    }
    return result
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `uv run pytest tests/test_section_router.py -k route_report -v`
Expected: PASS

- [ ] **Step 5: 커밋**

```bash
git add src/report/section_router.py tests/test_section_router.py
git commit -m "feat(decomp): route_report + 커버리지 장부 항등식"
```

---

### Task 5: 실데이터 2사 통합 검증 (ripple — 대주·삼성)

**Files:**
- Test: `tests/test_section_router.py`

**Interfaces:**
- Consumes: `extract_parts`(report_parts), `route_report`

- [ ] **Step 1: 통합 테스트 작성** (실데이터 존재 시만 실행, skip 아님)

```python
import pytest
from src.notes.report_parts import extract_parts
from src.report.section_router import route_report

_REPORTS = {
    "대주": "data/companies/00112457/2024/raw/report_doc/business_report.xml",
    "삼성": "data/companies/00126380/2024/raw/report_doc/business_report.xml",
}


@pytest.mark.integration
@pytest.mark.parametrize("name,path", list(_REPORTS.items()))
def test_route_report_real_identity_and_routing(name, path):
    from pathlib import Path

    p = Path(path)
    if not p.exists():
        pytest.skip(f"{name} 원문 미보유")
    parts = extract_parts(p.read_text(encoding="utf-8"))
    result = route_report(parts)
    # 항등식: 조용한 누락 0
    assert result.ledger["identity_ok"], f"{name} 장부 불일치: {result.ledger}"
    # 매출·특수관계는 양사 모두 라우팅돼야(2사 전수판정 근거 §6)
    assert "revenue_receivables" in result.routed, f"{name} 매출 미라우팅"
    assert "contingency_related_party" in result.routed, f"{name} 특수관계 미라우팅"
    # 기타 비율이 과반이면 매핑 부실(경고 임계) — 실패조건
    other_ratio = result.ledger["other"] / max(result.ledger["population"], 1)
    assert other_ratio < 0.5, f"{name} 기타 과다 {other_ratio:.0%} — 매핑 보강 필요"
```

- [ ] **Step 2: 통합 테스트 실행 (실패 시 패턴 튜닝)**

Run: `uv run pytest tests/test_section_router.py -k real_identity -v`
Expected: PASS (대주·삼성 2사). 실패 시 `report_section_routing.yaml` 패턴을 산출물(scratchpad/sections_*.txt)의 실제 제목에 맞춰 보강 후 재실행. other_ratio·라우팅 분포를 로그로 확인.

- [ ] **Step 3: 라우팅 분포 산출물 기록**

Run(수동 확인용):
```bash
uv run python -c "
from pathlib import Path
from src.notes.report_parts import extract_parts
from src.report.section_router import route_report
for name,path in {'대주':'data/companies/00112457/2024/raw/report_doc/business_report.xml','삼성':'data/companies/00126380/2024/raw/report_doc/business_report.xml'}.items():
    r=route_report(extract_parts(Path(path).read_text(encoding='utf-8')))
    print(name, r.ledger, {k:len(v) for k,v in r.routed.items()})
"
```
Expected: 항등식 True, 주제별 분포 출력. 결과를 `scratchpad/routing_dist.txt`에 저장.

- [ ] **Step 4: 전체 회귀 확인**

Run: `uv run pytest tests/ -q`
Expected: 기존 443 passed 유지 + 신규 통과(회귀 0).

- [ ] **Step 5: 커밋**

```bash
git add tests/test_section_router.py config/playbooks/report_section_routing.yaml
git commit -m "test(decomp): 대주·삼성 2사 실데이터 라우팅·장부 항등식 검증"
```

---

## Plan A 완료 기준

- `route_report(extract_parts(xml))` → 항등식 True(조용한 누락 0), 매출·특수관계 라우팅, 기타<50%.
- 2사(대주·삼성) 통합 테스트 통과. 전체 pytest 회귀 0. LLM 호출 0(전부 결정론).

> **Plan A 설계 갱신**: `route_title`·주제 YAML은 2-layer 전환으로 **은퇴**(단일주제 버킷팅 폐기). 단
> `split_subsections`·커버리지 장부·III/XII 제외는 **리더 배정 토대로 생존**. Plan B가 route_title 자리를 리더 배정으로 대체.

---

# Plan B — Layer 1 리더 + 완결성 앵커 + Layer 2 입력교체

> 설계 §4~§10(2-layer, grill 확정). Layer 1 서술 리더(LLM)로 S7 대체, 완결성 3앵커(결정론), report_extracts
> 캐시, Layer 2(6관점) 입력을 추출물로 교체. 프로토타입 실증됨(scratchpad/reader_proto.py, 삼성 ₩288).

### Task B1: ExtractedItem 스키마

**Files:** Create `src/schemas/extract.py` · Test `tests/test_extract_schema.py`
**Produces:** `ExtractedItem(part, label, statement, evidence, why_relevant)`, `ReaderOutput(items: list[ExtractedItem])` (pydantic BaseModel)

- [ ] 실패테스트: `ExtractedItem(part="XI", label="제재", statement="과징금 1,012억", evidence="XI.3", why_relevant="…")` 필드 5개 존재·빈 label 거부.
- [ ] 구현: pydantic BaseModel 5필드(statement에 원문 수치 인용, 계산 금지 docstring). ReaderOutput 봉투.
- [ ] pytest 통과 + 커밋 `feat(reader): ExtractedItem 스키마`.

### Task B2: 리더 배정 맵 (파트→매크로블록 focus, 결정론)

**Files:** Create `config/playbooks/reader_focus.yaml` (블록별 focus 프롬프트) · `src/report/reader_assign.py` · Test
**Produces:** `reader_focus(numeral) -> str|None` (III→None재무결정론, XII→None제외, I·II→②focus …)

- [ ] 실패테스트 2+케이스: `reader_focus("I")`·`reader_focus("XI")`가 각 블록 focus 반환, `reader_focus("III")`·`reader_focus("XII")` None.
- [ ] `reader_focus.yaml`: ②사업·영업(I,II) ③경영진단·감사(IV,V) ④지배구조·특수관계(VI~X) ⑤우발·제재(XI) focus 문구. 프로토타입 FOCUS 재사용·확장.
- [ ] 커밋 `feat(reader): 파트→블록 focus 배정(결정론)`.

### Task B3: 서술 리더 엔진 (LLM)

**Files:** Create `src/report/reader.py` · Test `tests/test_reader.py`
**Produces:** `run_reader(part: ReportPart, focus: str, model_name=None) -> dict{status, output: ReaderOutput, usage, latency_s}` (review_chunks 패턴, PydanticAI 구조화출력, 무키/에러 graceful)

- [ ] 실패테스트: monkeypatch로 agent 대체 → run_reader가 ReaderOutput 반환·usage 캡처. 무키 시 status="skipped".
- [ ] 구현: build_reader_agent(SYSTEM=프로토타입 시스템, output_type=ReaderOutput) + run_reader(prompt=focus+part.text). 계산금지·부정확정금지 프롬프트.
- [ ] (선택) live smoke 1건(삼성 XI) 수동 — 비용 주의, CI 아님.
- [ ] 커밋 `feat(reader): 서술 리더 엔진(PydanticAI 구조화추출)`.

### Task B4: report_extracts DuckDB 저장/로드

**Files:** Modify `src/db/normalized.py` · Test `tests/test_report_extracts_db.py`
**Produces:** `write_report_extracts(items, corp, year, root)`, `read_report_extracts(corp, year, root) -> list[dict]` (note_facts_classified 패턴)

- [ ] 실패테스트: tmp DB write 3항목 → read 3항목 왕복 일치(회사/연도 격리).
- [ ] 구현: report_extracts 테이블 DDL + write/read. 회사/연도 컬럼.
- [ ] 커밋 `feat(reader): report_extracts DuckDB 저장`.

### Task B5: 완결성 3앵커 (결정론)

**Files:** Create `src/report/completeness.py` · Test `tests/test_completeness.py`
**Produces:** `completeness_warnings(parts, items, materiality) -> list[dict]` (섹션·가나다·물질금액 커버리지)

- [ ] 실패테스트 3케이스(합성): (1) 실질내용 subsection 0추출 → 경고. (2) 가/나 항목 0추출 → 경고. (3) 원문 material 금액이 어떤 item에도 없음 → "금액 누락 의심" 경고. 금액 없는 잔여는 경고 안 함(한계).
- [ ] 구현: split_subsections·가나다 regex·금액추출(grounding 숫자 유효숫자 재사용)·materiality 임계 필터. item.statement/evidence에서 금액 대조(grounding 역방향).
- [ ] 커밋 `feat(reader): 완결성 3중 결정론 앵커`.

### Task B6: Layer 1 오케스트레이터 (전 파트 실행→저장→경고)

**Files:** Create `src/report/layer1.py` · Test `tests/test_layer1.py`
**Produces:** `run_layer1(corp, year, root) -> dict{extracts, warnings, usage}` (파트별 run_reader + 재무는 기존 Phase1 참조 + write_report_extracts + completeness_warnings)

- [ ] 실패테스트: monkeypatch run_reader → 파트 순회·전 서술파트 호출·III/XII 제외·저장·경고 산출.
- [ ] (검증) live 2사(대주·삼성) 1회 실행 → report_extracts 적재·비용 실측 기록(scratchpad). 실패조건: 특수관계·제재 항목 0 → FAIL.
- [ ] 커밋 `feat(reader): Layer 1 오케스트레이터`.

### Task B7: Layer 2 입력 교체 (S7 청크 → report_extracts)

**Files:** Modify `src/report/materials.py`·`card_pipeline.py` · Test
**Consumes:** `read_report_extracts`
**Produces:** materials가 report_review_chunks(S7) 대신 report_extracts를 관점 재료로.

- [ ] 실패테스트: materials 조립이 report_extracts를 포함(특수관계 관점이 ④ 추출·주석 모음). content_chunks 경로 미사용.
- [ ] 구현: `load_content_chunks` 호출부 → `read_report_extracts`. grounding에 추출물 evidence 색인(양방향).
- [ ] 커밋 `refactor(phase2): Layer 2 입력을 리더 추출물로 교체`.

### Task B8: S7 제거 + route_title 은퇴 + 온보딩 재작성

**Files:** Delete `src/report/review_chunks.py` · Modify `section_router.py`(route_title/YAML 제거)·`dashboard/onboarding.py`·`report_view.py` · 관련 테스트 정리
- [ ] grep `review_chunks`·`select_review_chunks`·`route_title` src == 0.
- [ ] 온보딩 = 게이트 + run_layer1 + 별칭(기타배정 UI 제거). completeness 경고 표시.
- [ ] 커밋 `refactor(decomp): S7·단일주제라우팅 제거, 온보딩 Layer1로`.

### Task B9: 통합 회귀

- [ ] `uv run python -m pytest tests/ -q` — 회귀 0(S7 삭제 테스트 정리분 제외), 신규 통과.
- [ ] 2사 E2E: 온보딩(Layer1) → Phase2(Layer2 카드) 실행 확인.

## Plan B 완료 기준
- 서술 리더가 5블록 추출 → report_extracts 적재, 완결성 경고 산출, Layer 2가 추출물로 카드 생성.
- S7·route_title 제거(grep 0). 전체 pytest 회귀 0. 계산=코드/발견=LLM 유지(리더 계산 0).
