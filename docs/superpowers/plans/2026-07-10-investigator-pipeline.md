# 조사원 파이프라인 (조사 단계) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 카드별 조사원(도구 루프)으로 "왜 이 발견이 나왔고 원인이 뭔지"의 결론을 만들고, 브리지 병합·연속 점수로 카드 구조를 정리한다 (PLAN.md §5 "조사 단계" 설계의 1단계 범위 4항목).

**Architecture:** 발견 5관점(기존 유지) → grounding → 카드 조립 시 **브리지 병합**(부모-자식 한 카드) → 카드마다 **결정론 게이트**(분해 잔차·leaf 집중도)로 분기: 설명완료→종합 1호출 / 미해결→**도구 루프**(결정론 도구, 왕복 캡) → 구조화 결론을 카드에 부착 → 반박·외부검증이 결론을 입력으로 받음 → **연속 점수**(코드 산정)가 High/Medium/Low를 대체.

**Tech Stack:** PydanticAI(Agent tools + UsageLimits), pyyaml(config), pytest, Streamlit(카드 렌더).

## Global Constraints

- 파일 100줄 내외 모듈화, SRP (전역 CLAUDE.md §4).
- 계산은 코드, LLM은 해석만 — 조사 도구는 전부 결정론 함수 (프로젝트 원칙 1).
- 임계·가중치 하드코딩 금지 → `config/investigation.yaml` 외부화 (프로젝트 원칙 3).
- 테스트: `uv run pytest tests/ -v`. 각 태스크 종료 시 전체 무회귀 확인.
- 한글 파일: PowerShell 라운드트립·bulk 치환 금지, U+FFFD 0 (전역 CLAUDE.md §5).
- 커밋 메시지: Conventional Commits, AI/Claude 문구 절대 금지, main 직접 커밋 금지 (전역 §6).
- LLM 실패는 삼키지 않고 None/미수행으로 명시 표기 (silent drop 0 — §9).
- 기존 실LLM 실행 테스트는 없음 — LLM 경로는 전부 fake agent_factory 주입으로 테스트한다
  (기존 `tests/test_rebuttal*.py` 패턴 참조).

---

### Task 1: 설정 파일 + 로더 (config/investigation.yaml)

**Files:**
- Create: `config/investigation.yaml`
- Create: `src/report/investigation_config.py`
- Test: `tests/test_investigation_config.py`

**Interfaces:**
- Produces: `load_investigation_config(path: Path = INVESTIGATION_PATH) -> dict` — 전체 yaml dict. 파일 부재는 `{}`(graceful, `load_bridges` 패턴 동일).

- [ ] **Step 1: 실패하는 테스트 작성**

```python
# tests/test_investigation_config.py
from pathlib import Path

from src.report.investigation_config import INVESTIGATION_PATH, load_investigation_config


def test_load_real_config_has_gate_and_weights():
    cfg = load_investigation_config()
    gate = cfg["investigation"]["gate"]
    assert gate["residual_pct_max"] > 0
    assert gate["top_leaf_pct_min"] > 0
    assert cfg["investigation"]["loop"]["max_requests"] >= 1
    weights = cfg["priority"]["weights"]
    assert set(weights) == {"materiality", "votes", "anomaly", "confidence"}


def test_missing_file_returns_empty(tmp_path: Path):
    assert load_investigation_config(tmp_path / "none.yaml") == {}
```

- [ ] **Step 2: 실패 확인**

Run: `uv run pytest tests/test_investigation_config.py -v`
Expected: FAIL — `ModuleNotFoundError: src.report.investigation_config`

- [ ] **Step 3: 구현**

```yaml
# config/investigation.yaml
# 조사원(investigator) 설정 — PLAN.md §5 조사 단계. 임계·가중치는 코드에 박지 않는다(원칙 3).
investigation:
  gate: # 결정론 게이트 — 아래 둘 다 충족하면 "분해가 원인 설명 완료" → 도구 루프 생략
    residual_pct_max: 20.0 # |미설명 잔차%| 상한
    top_leaf_pct_min: 60.0 # 최대 leaf |기여율| 하한
  loop:
    max_requests: 8 # 도구 루프 LLM 왕복 상한(비용 가드)
priority:
  weights: # 연속 점수 성분 가중치(합으로 정규화) — High/Medium/Low 라벨 대체
    materiality: 0.35
    votes: 0.30
    anomaly: 0.15
    confidence: 0.20
```

```python
# src/report/investigation_config.py
"""조사원·연속점수 설정 로더 — config/investigation.yaml (PLAN §5 조사 단계).

임계(게이트)·가중치(점수)를 코드에 박지 않는다(원칙 3). 파일 부재는 빈 dict(graceful).
"""

from __future__ import annotations

from pathlib import Path

import yaml

INVESTIGATION_PATH = Path("config/investigation.yaml")


def load_investigation_config(path: Path = INVESTIGATION_PATH) -> dict:
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


__all__ = ["INVESTIGATION_PATH", "load_investigation_config"]
```

- [ ] **Step 4: 통과 확인**

Run: `uv run pytest tests/test_investigation_config.py -v`
Expected: 2 PASS

- [ ] **Step 5: 커밋**

```bash
git add config/investigation.yaml src/report/investigation_config.py tests/test_investigation_config.py
git commit -m "feat(investigate): 조사원 게이트·점수 가중치 설정 외부화"
```

---

### Task 2: 연속 우선순위 점수 (③ 등급 폐지의 산정부)

**Files:**
- Create: `src/report/priority.py`
- Modify: `src/schemas/findings.py` (AccountFinding에 `priority_score`·`merged_children` 추가, `risk_level`을 optional로)
- Modify: `src/report/card_builder.py` (`build_cards` 끝에서 `apply_priority`, `_max_risk` 삭제)
- Test: `tests/test_priority.py`

**Interfaces:**
- Consumes: Task 1의 `load_investigation_config`.
- Produces: `compute_priority(card: AccountFinding, weights: dict[str, float]) -> float` (0..1, round 4) / `apply_priority(cards: list[AccountFinding], weights: dict[str, float]) -> None` (in-place `card.priority_score` 세팅).
- Produces(스키마): `AccountFinding.priority_score: float = 0.0`, `AccountFinding.merged_children: list[str] = []`, `AccountFinding.risk_level: RiskLevel | None = None`.

- [ ] **Step 1: 실패하는 테스트 작성**

```python
# tests/test_priority.py
from src.report.priority import apply_priority, compute_priority
from src.schemas.findings import AccountFinding, IssueType

WEIGHTS = {"materiality": 0.35, "votes": 0.30, "anomaly": 0.15, "confidence": 0.20}


def _card(**kw) -> AccountFinding:
    base = dict(
        account="CFS:영업이익",
        issue_type=IssueType.EARNINGS_TAX,
        materiality_score=1.0,
        anomaly_score=1.0,
        confidence="High",
        vote_count=4,
        internal_total=4,
    )
    base.update(kw)
    return AccountFinding(**base)


def test_full_signals_score_one():
    assert compute_priority(_card(), WEIGHTS) == 1.0


def test_zero_signals_score_zero():
    card = _card(materiality_score=0.0, anomaly_score=0.0, confidence="Low", vote_count=0)
    assert compute_priority(card, WEIGHTS) == 0.0


def test_monotonic_in_votes():
    low = compute_priority(_card(vote_count=1), WEIGHTS)
    high = compute_priority(_card(vote_count=3), WEIGHTS)
    assert high > low


def test_apply_priority_sets_field():
    cards = [_card(vote_count=0), _card(vote_count=4)]
    apply_priority(cards, WEIGHTS)
    assert cards[1].priority_score > cards[0].priority_score


def test_risk_level_now_optional_default_none():
    assert _card().risk_level is None
```

- [ ] **Step 2: 실패 확인**

Run: `uv run pytest tests/test_priority.py -v`
Expected: FAIL — `ModuleNotFoundError` 및 `risk_level Field required`

- [ ] **Step 3: 구현**

`src/schemas/findings.py` — AccountFinding 필드 변경(해당 줄만):

```python
    risk_level: RiskLevel | None = Field(
        default=None, description="폐지됨 — priority_score(연속 점수)로 대체. 표시·정렬 미사용"
    )
    # 연속 우선순위(0..1, 코드 산정) — High/Medium/Low 라벨 대체(PLAN §5 조사 단계 4항).
    priority_score: float = Field(default=0.0, description="정렬·외부검증 선정 기준 연속 점수")
    # 브리지 병합(④)으로 이 카드에 흡수된 자식 계정명(예: 매출총이익).
    merged_children: list[str] = Field(default_factory=list, description="병합된 자식 계정")
```

주의: `DisclosureChangeFinding.risk_level`은 관점 LLM 출력 스키마라 그대로 둔다.
`SuspicionItem.risk_level`(suspicion.py)도 그대로 — 코드가 소비를 중단할 뿐(다음 Step 4).

```python
# src/report/priority.py
"""연속 우선순위 점수 — High/Medium/Low 라벨 폐지(PLAN §5 조사 단계 4항).

성분은 전부 코드 산정값: 유의성(0..1 정규화 금액)·표수 비율·이상신호·확신도.
임계로 자르지 않는다 — 정렬·외부검증 대상 선정에만 쓴다(등급 컷 금지, 문제⑤).
"""

from __future__ import annotations

from src.schemas.findings import AccountFinding

_CONFIDENCE_NUM = {"High": 1.0, "Medium": 0.5, "Low": 0.0}


def compute_priority(card: AccountFinding, weights: dict[str, float]) -> float:
    votes = card.vote_count / card.internal_total if card.internal_total else 0.0
    parts = {
        "materiality": min(max(card.materiality_score, 0.0), 1.0),
        "votes": min(max(votes, 0.0), 1.0),
        "anomaly": min(max(card.anomaly_score, 0.0), 1.0),
        "confidence": _CONFIDENCE_NUM.get(str(card.confidence), 0.0),
    }
    total = sum(weights.values()) or 1.0
    return round(sum(weights.get(k, 0.0) * v for k, v in parts.items()) / total, 4)


def apply_priority(cards: list[AccountFinding], weights: dict[str, float]) -> None:
    for card in cards:
        card.priority_score = compute_priority(card, weights)


__all__ = ["apply_priority", "compute_priority"]
```

`src/report/card_builder.py` 수정:
1. `_max_risk` 함수와 `_RISK_ORDER` 상수 삭제, 카드 생성부 2곳의 `risk_level=_max_risk(items),` 줄 삭제.
2. `build_cards` 반환 직전(정규화 이후)에 추가:

```python
    # 연속 우선순위(0..1) — 정규화된 유의성·표수·이상·확신도의 가중합(라벨 폐지, 원칙 1).
    from src.report.investigation_config import load_investigation_config
    from src.report.priority import apply_priority

    weights = (load_investigation_config().get("priority") or {}).get("weights") or {}
    for group in (account_cards, company_cards, relationship_cards):
        apply_priority(group, weights)
```

- [ ] **Step 4: 통과 확인 + 파급 1차 측정**

Run: `uv run pytest tests/test_priority.py tests/test_card_builder.py -v`
Expected: test_priority 5 PASS. test_card_builder는 `risk_level` 단언 테스트가 FAIL할 수 있음 —
FAIL한 테스트는 "risk_level 단언 → priority_score 단언"으로 이 태스크에서 수정한다
(예: `assert card.risk_level == "High"` → `assert card.priority_score > 0`).

- [ ] **Step 5: 커밋**

```bash
git add src/report/priority.py src/schemas/findings.py src/report/card_builder.py tests/test_priority.py tests/test_card_builder.py
git commit -m "feat(priority): 카드 위험도 라벨을 코드 산정 연속 점수로 교체"
```

---

### Task 3: risk_level 소비처 전면 교체 (ripple)

**Files:**
- Modify: `src/report/card_report.py` (렌더 표에서 위험 열 제거, 정렬은 이미 표수·금액이라 유지)
- Modify: `src/report/external_verify.py` (`select_top_cards`를 priority + 미해결 우선으로)
- Modify: `src/report/rebuttal.py` (`build_rebuttal_input` entry에서 `"risk_level"` 키 제거)
- Modify: `dashboard/card_data.py` (`sort_cards_by_risk` → `sort_cards`(priority 내림))
- Modify: `dashboard/card_view.py` (위험 pill/이모지 → 우선순위 점수 칩)
- Test: 기존 `tests/test_external_verify.py`·`tests/test_card_report.py`·`tests/test_card_data.py` 수정

**Interfaces:**
- Produces: `select_top_cards(cards, top_n=EXTERNAL_TOP_N) -> list[AccountFinding]` — 정렬키 `(조사 미해결 여부, priority_score)` 내림. Task 5 전까지 `card.investigation`은 항상 None이라 사실상 priority 내림.
- Produces: `dashboard.card_data.sort_cards(cards: list) -> list` — `priority_score` 내림, 동점 `materiality_score` 내림.

- [ ] **Step 1: 파급 전수 목록 확보 (ripple-search)**

Run: `grep -rn "risk_level\|sort_cards_by_risk\|RISK_ORDER\|RISK_BADGES" src/ dashboard/ tests/ config/ --include="*.py" --include="*.yaml"`
Expected: 소비처 전수 목록. **아래 수정 목록과 대조해 빠진 파일이 있으면 이 태스크에 추가한다**
(report_html.py·report_view.py가 나오면 같은 규칙으로: 위험 라벨 표시 제거 또는 점수 표시로 교체).
관점 LLM 출력 스키마(suspicion.py `SuspicionItem.risk_level`, findings.py `DisclosureChangeFinding`)와
perspective_prompts.yaml의 출력 지시는 **비대상**(LLM은 계속 내되 코드가 소비 안 함 — 프롬프트 churn 회피).

- [ ] **Step 2: 실패하는 테스트 수정·작성**

`tests/test_external_verify.py`의 select_top_cards 테스트를 교체:

```python
def test_select_top_cards_by_priority():
    lows = [_card(account=f"CFS:acc{i}", priority_score=0.1 * i) for i in range(6)]
    top = select_top_cards(lows, top_n=3)
    assert [c.account for c in top] == ["CFS:acc5", "CFS:acc4", "CFS:acc3"]
```

(`_card` 헬퍼는 기존 파일의 것을 재사용하되 `risk_level` 인자 제거, `priority_score` 인자 허용.)

`tests/test_card_data.py`에 추가:

```python
def test_sort_cards_priority_desc():
    from dashboard.card_data import sort_cards

    a = {"priority_score": 0.2, "materiality_score": 0.9}
    b = {"priority_score": 0.8, "materiality_score": 0.1}
    assert sort_cards([a, b])[0] is b
```

- [ ] **Step 3: 실패 확인**

Run: `uv run pytest tests/test_external_verify.py tests/test_card_data.py -v`
Expected: 새·수정 테스트 FAIL

- [ ] **Step 4: 구현**

`src/report/external_verify.py` — `_RISK_ORDER` 삭제, `select_top_cards` 교체:

```python
def select_top_cards(
    cards: list[AccountFinding], top_n: int = EXTERNAL_TOP_N
) -> list[AccountFinding]:
    """검색 대상 — 조사가 '미해결'로 남긴 카드 우선, 이후 연속 점수 내림(라벨 폐지).

    미해결(investigation.resolved=False) 카드가 외부 근거의 효용이 가장 큼 —
    내부 데이터로 못 좁힌 원인을 외부에서 찾는 단계이기 때문."""

    def _key(c: AccountFinding) -> tuple:
        unresolved = c.investigation is not None and not c.investigation.resolved
        return (unresolved, c.priority_score or 0.0)

    ranked = sorted(cards, key=_key, reverse=True)
    return ranked[: min(max(top_n, 0), EXTERNAL_HARD_CAP)]
```

(주: `investigation` 필드는 Task 4에서 추가된다. Task 3을 먼저 실행하는 경우
`getattr(c, "investigation", None)`으로 써도 되고, Task 4 이후 정리해도 된다 —
subagent는 Task 4를 먼저 완료한 뒤 이 태스크를 실행하는 순서도 허용.)

`src/report/rebuttal.py` — `build_rebuttal_input`의 entry dict에서 `"risk_level": card.risk_level,` 줄 삭제.

`src/report/card_report.py` — `_card_row`에서 `card.risk_level` 셀 제거, 헤더의 `위험` 열 제거
(계정·관계 표: `| 순위 | 계정 | 유형 | 표수 | 확신도 | 금액 | 점수 | 반박 | 참고 |`로,
`점수` 셀은 `f"{card.priority_score:.2f}"`. 회사 표도 동일하게 위험→점수).

`dashboard/card_data.py` — `RISK_ORDER`·`sort_cards_by_risk` 삭제, 교체:

```python
def sort_cards(cards: list) -> list:
    """카드 정렬 — 연속 우선순위 내림, 동점이면 유의성 내림(라벨 폐지, PLAN §5)."""

    return sorted(
        cards,
        key=lambda c: (
            float(_get(c, "priority_score") or 0.0),
            float(_get(c, "materiality_score") or 0.0),
        ),
        reverse=True,
    )
```

`dashboard/card_view.py` — `RISK_BADGES` 삭제. `_header`의 pill 부분 교체:

```python
def _header(card: Any) -> None:
    fs_label, name = split_series_key(str(_get(card, "account") or ""))
    title = f"{name}" + (f" <span class='drv-chip'>{fs_label}</span>" if fs_label else "")
    score = float(_get(card, "priority_score") or 0.0)
    # 우측 배지는 연속 점수 하나만 — 등급 라벨은 폐지(근거 없는 라벨이 가장 눈에 띄던 문제③).
    st.html(
        '<div class="drv-row" style="justify-content:space-between;">'
        f'<span class="drv-card-title">{title}</span>'
        f'<span class="drv-pill">우선순위 {score:.2f}</span>'
        "</div>"
    )
```

`render_cards_section` — `sort_cards_by_risk`→`sort_cards`, 라벨 줄 교체:

```python
        score = float(_get(card, "priority_score") or 0.0)
        label = f"**{name}{fs_tag}** — {headline} · 우선순위 {score:.2f}"
```

(`risk`·`emoji`·`color` 변수 삭제. `drv-pill` 기본 클래스가 style.py에 없으면
`drv-pill-low` 클래스를 그대로 쓰되 텍스트만 점수로 — style.py 수정은 이 태스크 비범위.)

- [ ] **Step 5: 통과 + 전체 무회귀 확인**

Run: `uv run pytest tests/ -v 2>&1 | tail -20`
Expected: 전체 PASS (risk_level 단언 잔존 테스트가 있으면 Step 1 목록 기준으로 이 태스크에서 수정).
추가 확인: `grep -rn "risk_level" src/report/card_report.py src/report/external_verify.py dashboard/ --include="*.py"` → 0건.

- [ ] **Step 6: 커밋**

```bash
git add -A
git commit -m "refactor(priority): risk_level 소비처 전량을 연속 점수로 교체"
```

---

### Task 4: 브리지 병합 (④ 부모-자식 카드 한 장)

**Files:**
- Modify: `src/report/decomposition.py` (`bridge_child_map` 추가)
- Modify: `src/report/card_builder.py` (`merge_bridge_cards`, build_cards 배선)
- Test: `tests/test_card_builder.py` (병합 테스트 추가), `tests/test_decomposition.py`

**Interfaces:**
- Produces: `bridge_child_map(bridges: dict) -> dict[str, str]` — 구성 계정명(label·accounts 전 후보)→부모 계정명.
- Produces: `merge_bridge_cards(cards: list[AccountFinding], bridges: dict) -> list[AccountFinding]` — 같은 fs_div의 자식 카드를 부모 카드에 흡수(claims·evidence 합침, 표수 재계산, merged_children 기록). 부모 카드가 없으면 자식은 그대로 생존.

- [ ] **Step 1: 실패하는 테스트 작성**

```python
# tests/test_decomposition.py 에 추가
from src.report.decomposition import bridge_child_map


def test_bridge_child_map_covers_labels_and_synonyms():
    bridges = {
        "영업이익": {
            "variants": [
                {
                    "name": "표준",
                    "components": [
                        {"label": "매출총이익", "sign": 1, "accounts": ["매출총이익"]},
                        {
                            "label": "판매비와관리비",
                            "sign": -1,
                            "accounts": ["판매비와관리비", "판매 및 일반관리비"],
                        },
                    ],
                }
            ]
        }
    }
    child_map = bridge_child_map(bridges)
    assert child_map["매출총이익"] == "영업이익"
    assert child_map["판매 및 일반관리비"] == "영업이익"  # 동의 슬롯도 부모로
```

```python
# tests/test_card_builder.py 에 추가
from src.report.card_builder import merge_bridge_cards
from src.schemas.findings import AccountFinding, Claim, IssueType

_BRIDGES = {
    "영업이익": {
        "variants": [
            {
                "name": "표준",
                "components": [{"label": "매출총이익", "sign": 1, "accounts": ["매출총이익"]}],
            }
        ]
    }
}


def _mk(account: str, perspectives: list[str]) -> AccountFinding:
    return AccountFinding(
        account=account,
        issue_type=IssueType.EARNINGS_TAX,
        materiality_score=0.5,
        anomaly_score=0.0,
        confidence="Medium",
        vote_count=len(perspectives),
        internal_total=4,
        cluster_key=account,
        claims=[Claim(perspective=p, description=f"{account} 이상") for p in perspectives],
    )


def test_child_card_merges_into_parent():
    parent = _mk("CFS:영업이익", ["numeric"])
    child = _mk("CFS:매출총이익", ["trend"])
    merged = merge_bridge_cards([parent, child], _BRIDGES)
    assert len(merged) == 1
    only = merged[0]
    assert only.account == "CFS:영업이익"
    assert only.merged_children == ["매출총이익"]
    assert only.vote_count == 2  # numeric + trend 합집합 재계산
    assert len(only.claims) == 2  # 자식 주장 보존(누락 금지)


def test_child_without_parent_survives():
    child = _mk("CFS:매출총이익", ["trend"])
    assert merge_bridge_cards([child], _BRIDGES) == [child]


def test_different_fs_div_not_merged():
    parent = _mk("CFS:영업이익", ["numeric"])
    child = _mk("OFS:매출총이익", ["trend"])
    assert len(merge_bridge_cards([parent, child], _BRIDGES)) == 2
```

- [ ] **Step 2: 실패 확인**

Run: `uv run pytest tests/test_decomposition.py tests/test_card_builder.py -v -k "bridge or merge"`
Expected: FAIL — `ImportError: bridge_child_map` / `merge_bridge_cards`

- [ ] **Step 3: 구현**

`src/report/decomposition.py`에 추가:

```python
def bridge_child_map(bridges: dict[str, dict]) -> dict[str, str]:
    """구성 계정명 → 부모 계정명 (전 variant·동의 슬롯 합집합). 카드 병합(④)의 관계 사전."""

    out: dict[str, str] = {}
    for parent, spec in (bridges or {}).items():
        for variant in spec.get("variants", []) or []:
            for slot in variant.get("components", []) or []:
                label = str(slot.get("label", ""))
                if label:
                    out[label] = parent
                for name in slot.get("accounts", []) or []:
                    out[str(name)] = parent
    return out
```

`src/report/card_builder.py`에 추가 + 배선:

```python
def merge_bridge_cards(
    cards: list[AccountFinding], bridges: dict[str, dict]
) -> list[AccountFinding]:
    """브리지 부모-자식 계정 카드를 한 카드로(같은 사건 두 장 방지, PLAN §5 조사 단계 1항).

    자식(예: 매출총이익)은 부모(영업이익) 카드에 흡수: claims·evidence 합침, 표수는 병합
    후 관점 합집합으로 재계산, merged_children에 기록. 조상까지 올라가며 존재하는 가장
    가까운 부모를 찾는다(GP→OP→세전 다단). 부모 카드가 없으면 자식은 그대로 생존(드롭 0).
    """

    from src.report.decomposition import bridge_child_map

    child_map = bridge_child_map(bridges)
    by_account = {card.account: card for card in cards}

    def _find_parent(account: str) -> AccountFinding | None:
        fs_div, _, name = str(account).partition(":")
        seen: set[str] = set()
        while name in child_map and name not in seen:  # 조상 사슬 추적(순환 가드)
            seen.add(name)
            name = child_map[name]
            parent = by_account.get(f"{fs_div}:{name}")
            if parent is not None:
                return parent
        return None

    survivors: list[AccountFinding] = []
    for card in cards:
        parent = _find_parent(card.account)
        if parent is None or parent is card:
            survivors.append(card)
            continue
        _, child_name = str(card.account).partition(":")[::2]
        parent.merged_children.append(child_name)
        parent.claims.extend(card.claims)
        parent.numeric_evidence.extend(card.numeric_evidence)
        parent.materiality_score = max(parent.materiality_score, card.materiality_score)
        parent.anomaly_score = max(parent.anomaly_score, card.anomaly_score)
        votes = {c.perspective for c in parent.claims if c.perspective in INTERNAL_PERSPECTIVES}
        parent.vote_count = len(votes)
    return survivors
```

주의: `str(card.account).partition(":")[::2]`는 `(앞, 뒤)` 튜플 — 가독을 위해 실제 구현은
`fs_div, _, child_name = str(card.account).partition(":")`로 풀어 쓴다.

`build_cards` 배선 — materiality 정규화·apply_priority **이전**에 (raw 금액 기준 병합):

```python
    # 브리지 병합(④): 부모-자식 계정(GP↔OP)은 같은 사건 — 한 카드로(정규화·점수 산정 전).
    from src.report.decomposition import load_bridges

    account_cards = merge_bridge_cards(account_cards, load_bridges())
    raw_materiality = [c.materiality_score for c in account_cards]
```

(기존 `raw_materiality` 누적 리스트는 병합 후 재수집으로 교체 — 병합으로 카드 수가 줄기 때문.)

- [ ] **Step 4: 통과 + 전체 무회귀**

Run: `uv run pytest tests/test_card_builder.py tests/test_decomposition.py tests/ -x -q`
Expected: 전체 PASS

- [ ] **Step 5: 커밋**

```bash
git add src/report/decomposition.py src/report/card_builder.py tests/test_card_builder.py tests/test_decomposition.py
git commit -m "feat(cards): 브리지 부모-자식 카드 병합 — 같은 사건 한 카드"
```

---

### Task 5: 조사 결론 스키마 + 결정론 게이트

**Files:**
- Create: `src/schemas/investigation.py`
- Create: `src/report/investigator.py` (이 태스크는 게이트만)
- Modify: `src/schemas/findings.py` (AccountFinding에 `investigation` 필드)
- Test: `tests/test_investigator.py`

**Interfaces:**
- Produces: `InvestigationConclusion` (pydantic) — `headline: str`, `cause_path: list[str]`, `anomaly_points: list[str]`, `open_questions: list[str]`, `resolved: bool`, `method: Literal["gate_summary","tool_loop"]`(코드 세팅), `tool_requests: int = 0`(코드 세팅).
- Produces: `needs_tool_loop(decomposition: dict | None, gate: dict) -> bool`.
- Produces(스키마): `AccountFinding.investigation: InvestigationConclusion | None = None`.

- [ ] **Step 1: 실패하는 테스트 작성**

```python
# tests/test_investigator.py
from src.report.investigator import needs_tool_loop

GATE = {"residual_pct_max": 20.0, "top_leaf_pct_min": 60.0}


def _decomp(residual_pct: float, rows: list[dict], delta: float = -100.0) -> dict:
    return {
        "parent": "CFS:영업이익",
        "delta": delta,
        "residual": delta * residual_pct / 100,
        "residual_pct": residual_pct,
        "rows": rows,
    }


def test_no_decomposition_needs_loop():
    assert needs_tool_loop(None, GATE) is True


def test_clean_single_driver_skips_loop():
    rows = [
        {"account": "매출총이익", "delta": -90.0},
        {"account": "판매비와관리비", "delta": -8.0},
    ]
    assert needs_tool_loop(_decomp(residual_pct=2.0, rows=rows), GATE) is False


def test_large_residual_needs_loop():
    rows = [{"account": "매출총이익", "delta": -60.0}]
    assert needs_tool_loop(_decomp(residual_pct=40.0, rows=rows), GATE) is True


def test_dispersed_contributions_need_loop():
    rows = [
        {"account": "매출총이익", "delta": -35.0},
        {"account": "판매비와관리비", "delta": -33.0},
        {"account": "기타영업수익", "delta": -30.0},
    ]
    assert needs_tool_loop(_decomp(residual_pct=2.0, rows=rows), GATE) is True


def test_conclusion_attaches_to_card():
    from src.schemas.findings import AccountFinding, IssueType
    from src.schemas.investigation import InvestigationConclusion

    card = AccountFinding(
        account="CFS:영업이익",
        issue_type=IssueType.EARNINGS_TAX,
        materiality_score=0.5,
        anomaly_score=0.0,
        confidence="Medium",
        investigation=InvestigationConclusion(
            headline="매출 이탈 주도", resolved=True, method="gate_summary"
        ),
    )
    assert card.investigation.resolved is True
```

- [ ] **Step 2: 실패 확인**

Run: `uv run pytest tests/test_investigator.py -v`
Expected: FAIL — 모듈 없음

- [ ] **Step 3: 구현**

```python
# src/schemas/investigation.py
"""조사원 산출 스키마 — 카드 최상단 '그래서 결론'(PLAN §5 조사 단계 2·3항).

조사원(도구 루프 또는 게이트 요약)이 채우고, 반박·외부검증이 이 결론을 입력으로 받는다.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class InvestigationConclusion(BaseModel):
    headline: str = Field(description="핵심 결론 1~2문장 — 원인이 어디까지 좁혀졌는가")
    cause_path: list[str] = Field(
        default_factory=list, description="원인 경로(상위→하위 순 단계 서술, 수치 인용)"
    )
    anomaly_points: list[str] = Field(
        default_factory=list, description="이상 지점 — 데이터로 정상 설명이 안 되는 것"
    )
    open_questions: list[str] = Field(
        default_factory=list, description="남은 확인사항 — 내부 데이터로 못 좁힌 것"
    )
    resolved: bool = Field(description="원인 규명이 내부 데이터에서 완결됐는지")
    # 아래 둘은 LLM이 아니라 코드가 세팅한다(경로·비용 관찰용).
    method: Literal["gate_summary", "tool_loop"] = "tool_loop"
    tool_requests: int = 0


__all__ = ["InvestigationConclusion"]
```

`src/schemas/findings.py` — import 추가 + AccountFinding 필드 추가:

```python
from src.schemas.investigation import InvestigationConclusion
```

```python
    # 조사원 결론(PLAN §5 조사 단계) — None이면 '조사 미수행'으로 표시(둔갑 금지).
    investigation: InvestigationConclusion | None = Field(
        default=None, description="카드별 조사 결론(원인 경로·이상 지점·남은 확인사항)"
    )
```

```python
# src/report/investigator.py (이 태스크 분량 — 게이트)
"""카드별 조사원 — 결정론 게이트 + 도구 루프(PLAN §5 조사 단계).

게이트: 분해가 이미 원인을 설명(잔차 작고 단일 leaf 지배)했으면 도구 루프를 생략하고
종합 1호출만 한다. 배제가 아니라 경로 차이 — 모든 카드가 결론을 받는다.
"""

from __future__ import annotations


def needs_tool_loop(decomposition: dict | None, gate: dict) -> bool:
    """True = 도구 루프 필요(분해 없음·잔차 큼·기여 분산). False = 종합 1호출로 충분."""

    if not decomposition:
        return True
    residual_pct = decomposition.get("residual_pct")
    if residual_pct is None or abs(residual_pct) > float(gate.get("residual_pct_max", 20.0)):
        return True
    from dashboard.card_data import waterfall_leaves  # 기존 평탄화 재사용(external_verify 선례)

    delta = abs(float(decomposition.get("delta") or 0.0))
    if not delta:
        return True
    leaves = [(n, d) for n, d in waterfall_leaves(decomposition) if n != "미설명 잔차"]
    if not leaves:
        return True
    top_share = max(abs(d) for _, d in leaves) / delta * 100
    return top_share < float(gate.get("top_leaf_pct_min", 60.0))


__all__ = ["needs_tool_loop"]
```

- [ ] **Step 4: 통과 확인**

Run: `uv run pytest tests/test_investigator.py -v`
Expected: 5 PASS

- [ ] **Step 5: 커밋**

```bash
git add src/schemas/investigation.py src/schemas/findings.py src/report/investigator.py tests/test_investigator.py
git commit -m "feat(investigate): 조사 결론 스키마 + 결정론 게이트(잔차·기여 집중도)"
```

---

### Task 6: 조사 도구 + 조사원 에이전트 실행기

**Files:**
- Modify: `src/report/investigator.py` (도구·에이전트·`run_investigation`)
- Modify: `config/playbooks/perspective_prompts.yaml` (`investigator` 섹션 추가)
- Test: `tests/test_investigator.py` (fake agent 주입 테스트 추가)

**Interfaces:**
- Consumes: Task 5 `needs_tool_loop`·`InvestigationConclusion`, Task 1 `load_investigation_config`, `src.agents.model_retry.make_agent`(기존), `src.report.decomposition.decompose_change/load_bridges`(기존).
- Produces: `run_investigation(card: AccountFinding, report: dict, decomposition: dict | None, config: dict | None = None, agent_factory: Callable | None = None, prompts: dict | None = None) -> InvestigationConclusion | None` — 키 없음/에러는 None(카드는 '조사 미수행'으로 생존).
- Produces: `build_investigator_agent(model_name=..., prompts=None, with_tools=True) -> Agent[InvestigationDeps, InvestigationConclusion]`.

- [ ] **Step 1: 실패하는 테스트 작성** (`tests/test_investigator.py`에 추가)

```python
import asyncio

from src.report.investigator import InvestigationDeps, run_investigation
from src.schemas.findings import AccountFinding, IssueType
from src.schemas.investigation import InvestigationConclusion


def _card() -> AccountFinding:
    return AccountFinding(
        account="CFS:영업이익",
        issue_type=IssueType.EARNINGS_TAX,
        materiality_score=0.5,
        anomaly_score=0.0,
        confidence="Medium",
        cluster_key="CFS:영업이익",
    )


class _FakeResult:
    def __init__(self, output):
        self.output = output

    def usage(self):
        class _U:
            requests = 3

        return _U()


class _FakeAgent:
    def __init__(self, output):
        self._output = output
        self.last_prompt = None

    async def run(self, prompt, **kw):
        self.last_prompt = prompt
        return _FakeResult(self._output)


def test_run_investigation_returns_conclusion_and_sets_method():
    conclusion = InvestigationConclusion(headline="매출 이탈", resolved=True)
    fake = _FakeAgent(conclusion)
    out = asyncio.run(
        run_investigation(
            _card(),
            {"account_level_series": [], "target_year": 2025},
            decomposition=None,  # 분해 없음 → 도구 루프 경로
            config={"investigation": {"gate": {}, "loop": {"max_requests": 8}}},
            agent_factory=lambda **kw: fake,
        )
    )
    assert out.headline == "매출 이탈"
    assert out.method == "tool_loop"  # 게이트 미통과 → 루프 경로 표기
    assert "CFS:영업이익" in fake.last_prompt  # 카드가 프롬프트에 들어감


def test_run_investigation_failure_returns_none():
    class _Boom:
        async def run(self, prompt, **kw):
            raise RuntimeError("api down")

    out = asyncio.run(
        run_investigation(
            _card(),
            {"account_level_series": [], "target_year": 2025},
            decomposition=None,
            config={},
            agent_factory=lambda **kw: _Boom(),
        )
    )
    assert out is None  # 실패 = None — '조사 미수행' 표기(둔갑 금지)


def test_tools_read_report_deterministically():
    deps = InvestigationDeps(
        series_rows=[
            {"series_key": "CFS:매출", "year": 2024, "amount": 100.0},
            {"series_key": "CFS:매출", "year": 2025, "amount": 80.0},
        ],
        target_year=2025,
        bridges={},
        note_facts=[{"label": "반도체 부문", "value": "12345"}],
    )
    from src.report.investigator import _get_series, _find_notes, _top_changes

    assert _get_series(deps, "CFS:매출") == {2024: 100.0, 2025: 80.0}
    assert _find_notes(deps, "반도체") == [{"label": "반도체 부문", "value": "12345"}]
    movers = _top_changes(deps)
    assert movers[0]["series_key"] == "CFS:매출" and movers[0]["delta"] == -20.0
```

- [ ] **Step 2: 실패 확인**

Run: `uv run pytest tests/test_investigator.py -v -k "run_investigation or tools_read"`
Expected: FAIL — 미구현 import

- [ ] **Step 3: 구현** (`src/report/investigator.py`에 추가 — 파일이 100줄을 크게 넘으면 도구를 `src/report/investigation_tools.py`로 분리)

```python
import asyncio
import json
from collections.abc import Callable
from dataclasses import dataclass, field

from pydantic_ai import Agent, RunContext
from pydantic_ai.models.openai import OpenAIModel, OpenAIModelSettings
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.usage import UsageLimits

from config.settings import settings
from src.report.decomposition import decompose_change, load_bridges
from src.report.investigation_config import load_investigation_config
from src.report.perspective_runner import PROMPTS_PATH, load_perspective_prompts
from src.schemas.findings import AccountFinding
from src.schemas.investigation import InvestigationConclusion

OPENAI_MODEL_NAME = settings.openai_model


@dataclass
class InvestigationDeps:
    """조사 도구가 읽는 결정론 데이터 묶음 — LLM은 이 밖의 숫자를 만들 수 없다."""

    series_rows: list[dict]
    target_year: int
    bridges: dict = field(default_factory=dict)
    note_facts: list[dict] = field(default_factory=list)


# --- 도구 본체(순수 함수) — Agent 등록과 분리해 단위테스트 가능하게 둔다. ---


def _get_series(deps: InvestigationDeps, series_key: str) -> dict[int, float]:
    out: dict[int, float] = {}
    for r in deps.series_rows:
        if str(r.get("series_key")) == series_key and r.get("amount") is not None:
            out[int(r["year"])] = float(r["amount"])
    return out


def _get_decomposition(deps: InvestigationDeps, series_key: str) -> dict | None:
    return decompose_change(deps.series_rows, series_key, deps.target_year, deps.bridges)


def _find_notes(deps: InvestigationDeps, keyword: str, limit: int = 20) -> list[dict]:
    kw = str(keyword)
    return [f for f in deps.note_facts if kw in str(f)][:limit]


def _top_changes(deps: InvestigationDeps, limit: int = 15) -> list[dict]:
    """target_year 전년비 |Δ| 상위 — '같이 움직인 계정'을 조사원이 훑는 용도."""

    prior_year = deps.target_year - 1
    by_key: dict[str, dict[int, float]] = {}
    for r in deps.series_rows:
        key = str(r.get("series_key"))
        if r.get("amount") is not None:
            by_key.setdefault(key, {})[int(r["year"])] = float(r["amount"])
    rows = [
        {
            "series_key": key,
            "prior": amounts[prior_year],
            "current": amounts[deps.target_year],
            "delta": amounts[deps.target_year] - amounts[prior_year],
        }
        for key, amounts in by_key.items()
        if deps.target_year in amounts and prior_year in amounts
    ]
    return sorted(rows, key=lambda x: abs(x["delta"]), reverse=True)[:limit]


def build_investigator_agent(
    model_name: str = OPENAI_MODEL_NAME,
    prompts: dict | None = None,
    with_tools: bool = True,
) -> Agent[InvestigationDeps, InvestigationConclusion]:
    prompts = prompts or load_perspective_prompts(PROMPTS_PATH)
    block = prompts.get("investigator", {})
    system_prompt = "\n\n".join(
        p.strip() for p in (block.get("role", ""), block.get("instruction", "")) if p and p.strip()
    )
    model = OpenAIModel(model_name, provider=OpenAIProvider(api_key=settings.openai_api_key))
    model_settings = OpenAIModelSettings(timeout=settings.openai_timeout_seconds)
    if settings.openai_reasoning_effort:
        model_settings["openai_reasoning_effort"] = settings.openai_reasoning_effort
    agent: Agent[InvestigationDeps, InvestigationConclusion] = Agent(
        model,
        output_type=InvestigationConclusion,
        deps_type=InvestigationDeps,
        system_prompt=system_prompt,
        model_settings=model_settings,
        retries=2,
    )
    if with_tools:

        @agent.tool
        def get_series(ctx: RunContext[InvestigationDeps], series_key: str) -> dict[int, float]:
            """계정 연도별 금액 시계열. series_key 예: 'CFS:매출'."""

            return _get_series(ctx.deps, series_key)

        @agent.tool
        def get_decomposition(ctx: RunContext[InvestigationDeps], series_key: str) -> dict | None:
            """소계 계정의 YoY 변동을 구성 기여로 분해(항등식·재귀). 브리지 없으면 None."""

            return _get_decomposition(ctx.deps, series_key)

        @agent.tool
        def find_notes(ctx: RunContext[InvestigationDeps], keyword: str) -> list[dict]:
            """주석 fact에서 키워드 부분일치 검색(세그먼트·우발·특수관계 등)."""

            return _find_notes(ctx.deps, keyword)

        @agent.tool
        def top_changes(ctx: RunContext[InvestigationDeps]) -> list[dict]:
            """당기 전년비 변동 절대값 상위 계정 — 같이 움직인 계정 훑기."""

            return _top_changes(ctx.deps)

    return agent


def _investigation_prompt(card: AccountFinding, decomposition: dict | None) -> str:
    payload = {
        "account": card.account,
        "issue_type": card.issue_type.value,
        "claims": [c.model_dump() for c in card.claims],
        "merged_children": card.merged_children,
        "decomposition": decomposition,
    }
    return json.dumps(payload, ensure_ascii=False)


async def run_investigation(
    card: AccountFinding,
    report: dict,
    decomposition: dict | None,
    config: dict | None = None,
    agent_factory: Callable[..., object] | None = None,
    prompts: dict | None = None,
) -> InvestigationConclusion | None:
    """카드 1장 조사 — 게이트로 경로 분기, 실패는 None('조사 미수행' 표기, 둔갑 금지)."""

    if agent_factory is None and not settings.openai_api_key:
        return None
    cfg = config if config is not None else load_investigation_config()
    inv = cfg.get("investigation") or {}
    use_tools = needs_tool_loop(decomposition, inv.get("gate") or {})
    max_requests = int((inv.get("loop") or {}).get("max_requests", 8))
    deps = InvestigationDeps(
        series_rows=list(report.get("account_level_series") or []),
        target_year=int(report.get("target_year") or 0),
        bridges=load_bridges(),
        note_facts=list(report.get("note_facts") or []),
    )
    factory = agent_factory or build_investigator_agent
    agent = factory(prompts=prompts, with_tools=use_tools) if agent_factory is None else factory(
        with_tools=use_tools
    )
    try:
        result = await asyncio.wait_for(
            agent.run(
                _investigation_prompt(card, decomposition),
                deps=deps,
                usage_limits=UsageLimits(request_limit=max_requests),
            ),
            timeout=settings.openai_timeout_seconds * max_requests,
        )
    except Exception:
        return None
    conclusion: InvestigationConclusion = result.output
    conclusion.method = "tool_loop" if use_tools else "gate_summary"
    conclusion.tool_requests = getattr(result.usage(), "requests", 0)
    return conclusion
```

`config/playbooks/perspective_prompts.yaml`에 추가 (기존 rebuttal 섹션과 같은 계층):

```yaml
investigator:
  role: |
    당신은 감사 조사원이다. 발견자들이 제기한 의심 카드 1장을 받아, 제공된 도구로
    "왜 이 발견이 나왔고 원인이 무엇이며 어디가 이상한지"를 규명한다.
  instruction: |
    - 앞 도구 호출의 답이 다음 질문을 만든다: 분해(get_decomposition)로 주도 요인을 찾고,
      주도 요인이 소계면 다시 분해하고, leaf에 닿으면 주석(find_notes)·동행 계정(top_changes)
      으로 맥락을 좁혀라.
    - 숫자는 도구 결과만 인용한다. 도구 밖 수치·외부 사실(업황 등)을 지어내지 않는다.
    - resolved 판정: 원인 경로가 leaf(더 못 쪼개는 계정·주석 근거)까지 닿고 미설명 잔차가
      작으면 true. 데이터가 없어 못 좁혔으면 false로 두고 open_questions에 남겨라.
    - anomaly_points에는 "정상 설명이 안 되는 것"만 담아라(예: 매출 급감인데 재고 불변).
      정상으로 설명되면 담지 말고 headline에서 정상 설명을 언급하라.
    - 분식 확정·단정 금지 — 검토 후보와 확인사항의 언어를 유지하라(포지셔닝 원칙).
    - 도구 없이 입력만 받은 경우(분해가 이미 원인을 설명): 분해 표를 근거로 결론문만 작성하라.
```

- [ ] **Step 4: 통과 + 전체 무회귀**

Run: `uv run pytest tests/test_investigator.py tests/ -x -q`
Expected: 전체 PASS

- [ ] **Step 5: 커밋**

```bash
git add src/report/investigator.py config/playbooks/perspective_prompts.yaml tests/test_investigator.py
git commit -m "feat(investigate): 조사원 도구 루프 — 결정론 도구 4종 + 게이트 분기 실행기"
```

---

### Task 7: 파이프라인 배선 + 반박 입력에 결론 공급

**Files:**
- Modify: `src/report/card_pipeline.py` (조사 단계 삽입)
- Modify: `src/report/rebuttal.py` (`build_rebuttal_input`에 investigation 추가)
- Test: `tests/test_card_pipeline.py`, `tests/test_rebuttal.py`

**Interfaces:**
- Consumes: Task 6 `run_investigation`.
- Produces: `build_suspicion_cards(..., investigation_runner: Callable = run_investigation)` — 카드마다 `card.investigation` 부착 후 반박·외부검증 실행. on_progress에 `{"phase": "investigation"}` 이벤트 추가.

- [ ] **Step 1: 실패하는 테스트 작성** (`tests/test_card_pipeline.py`에 추가 — 기존 fake runner 픽스처 재사용)

```python
def test_pipeline_attaches_investigation_and_feeds_rebuttal(monkeypatch):
    """조사원 결과가 카드에 붙고, 반박 입력 시점에 이미 붙어 있어야 한다(순서 검증)."""

    from src.schemas.investigation import InvestigationConclusion

    async def fake_investigation(card, report, decomposition, **kw):
        return InvestigationConclusion(headline=f"{card.account} 원인 규명", resolved=False)

    seen_at_rebuttal: list = []

    async def fake_rebuttal(cards, context, **kw):
        from src.schemas.suspicion import RebuttalOutput

        seen_at_rebuttal.extend(c.investigation for c in cards)
        return RebuttalOutput()

    # 기존 테스트의 fake agent_runner(의심건 1개 반환)와 report 픽스처를 그대로 사용해
    # build_suspicion_cards(..., investigation_runner=fake_investigation,
    #                        rebuttal_runner=fake_rebuttal, external_verifier=...)
    result = _run_pipeline_with(  # 기존 파일의 헬퍼 관례에 맞춰 작성
        investigation_runner=fake_investigation, rebuttal_runner=fake_rebuttal
    )
    cards = result["account_cards"] + result["company_cards"] + result["relationship_cards"]
    assert cards and all(c.investigation is not None for c in cards)
    assert all(inv is not None for inv in seen_at_rebuttal)  # 반박이 결론을 이미 봄
```

```python
# tests/test_rebuttal.py 에 추가
def test_rebuttal_input_includes_investigation():
    from src.report.rebuttal import build_rebuttal_input
    from src.schemas.investigation import InvestigationConclusion

    card = _make_card()  # 기존 파일의 카드 헬퍼
    card.investigation = InvestigationConclusion(headline="매출 이탈 주도", resolved=True)
    payload = build_rebuttal_input([card], {})
    assert payload[0]["investigation"]["headline"] == "매출 이탈 주도"
    assert "risk_level" not in payload[0]
```

- [ ] **Step 2: 실패 확인**

Run: `uv run pytest tests/test_card_pipeline.py tests/test_rebuttal.py -v -k investigation`
Expected: FAIL

- [ ] **Step 3: 구현**

`src/report/card_pipeline.py`:
- import에 `from src.report.investigator import run_investigation` 추가.
- `build_suspicion_cards` 시그니처에 `investigation_runner: Callable[..., Awaitable[Any]] = run_investigation,` 추가.
- decompositions 계산 직후·반박 실행 전에 삽입:

```python
    # 조사 단계(PLAN §5): 카드마다 결론 생성 — 반박·외부검증이 이 결론을 입력으로 받는다.
    _emit("investigation")
    conclusions = await asyncio.gather(
        *[
            investigation_runner(card, report, decompositions.get(card.cluster_key or ""))
            for card in all_cards
        ]
    )
    for card, conclusion in zip(all_cards, conclusions, strict=True):
        card.investigation = conclusion
```

- docstring의 on_progress 설명에 `'investigation'` 추가.
- 반환 dict에 관찰 지표 추가: `"investigated": sum(1 for c in conclusions if c is not None),`

`src/report/rebuttal.py` — `build_rebuttal_input`의 entry 구성에 추가 (risk_level 줄은 Task 3에서 이미 제거):

```python
        if card.investigation is not None:  # 조사 결론 — 반박의 공격 대상(없으면 키 생략)
            entry["investigation"] = card.investigation.model_dump()
```

- [ ] **Step 4: 통과 + 전체 무회귀**

Run: `uv run pytest tests/test_card_pipeline.py tests/test_rebuttal.py tests/ -x -q`
Expected: 전체 PASS

- [ ] **Step 5: 커밋**

```bash
git add src/report/card_pipeline.py src/report/rebuttal.py tests/test_card_pipeline.py tests/test_rebuttal.py
git commit -m "feat(pipeline): 조사 단계 배선 — 카드 결론 부착 후 반박·외부검증 입력 공급"
```

---

### Task 8: UI — 결론 최상단 렌더 + 영속화 확인

**Files:**
- Modify: `dashboard/card_data.py` (`conclusion_view` 순수 가공 추가)
- Modify: `dashboard/card_view.py` (`_conclusion_block` — 카드 본문 최상단)
- Test: `tests/test_card_data.py`, `tests/test_cards_store.py`

**Interfaces:**
- Produces: `conclusion_view(card: Any) -> dict | None` — `{headline, cause_path, anomaly_points, open_questions, resolved, method, tool_requests}` (전 텍스트 humanize_amounts 적용). investigation 없으면 None.

- [ ] **Step 1: 실패하는 테스트 작성**

```python
# tests/test_card_data.py 에 추가
def test_conclusion_view_humanizes_and_maps():
    from dashboard.card_data import conclusion_view

    card = {
        "investigation": {
            "headline": "매출 1,289,630,423,605 감소가 주도",
            "cause_path": ["영업이익 -62.8%", "매출총이익 기여 -84%"],
            "anomaly_points": [],
            "open_questions": ["부문별 단가 정보 없음"],
            "resolved": False,
            "method": "tool_loop",
            "tool_requests": 5,
        }
    }
    view = conclusion_view(card)
    assert "1.3조" in view["headline"]  # 12자리 원숫자 축약
    assert view["resolved"] is False and view["method"] == "tool_loop"


def test_conclusion_view_none_when_missing():
    from dashboard.card_data import conclusion_view

    assert conclusion_view({}) is None
```

```python
# tests/test_cards_store.py 에 추가 — 결론이 저장/로드 왕복에서 살아남는지
def test_store_roundtrip_preserves_investigation(tmp_path):
    # 기존 파일의 save/load 헬퍼 관례를 따르되, 카드에 investigation·priority_score·
    # merged_children을 채워 저장→로드 후 동일값 단언.
    ...  # 기존 test_cards_store의 roundtrip 테스트를 복제해 3필드 단언 추가
```

(cards_store가 `model_dump`/`AccountFinding.model_validate` 왕복이면 자동 통과 —
아니라면 이 태스크에서 직렬화 경로를 수정한다. 구현 전 `src/report/cards_store.py`를 읽고 판단.)

- [ ] **Step 2: 실패 확인**

Run: `uv run pytest tests/test_card_data.py tests/test_cards_store.py -v -k "conclusion or investigation"`
Expected: FAIL — `conclusion_view` 없음

- [ ] **Step 3: 구현**

`dashboard/card_data.py`에 추가:

```python
def conclusion_view(card: Any) -> dict | None:
    """조사 결론 → 표시 재료(금액 축약 적용). 없으면 None('조사 미수행' 캡션은 view가)."""

    inv = _get(card, "investigation")
    if not inv:
        return None
    texts = lambda key: [humanize_amounts(str(t)) for t in (_get(inv, key) or [])]  # noqa: E731
    return {
        "headline": humanize_amounts(str(_get(inv, "headline") or "")),
        "cause_path": texts("cause_path"),
        "anomaly_points": texts("anomaly_points"),
        "open_questions": texts("open_questions"),
        "resolved": bool(_get(inv, "resolved")),
        "method": str(_get(inv, "method") or ""),
        "tool_requests": int(_get(inv, "tool_requests") or 0),
    }
```

`dashboard/card_view.py` — `_card_body` 최상단(검토 포인트보다 위)에 결론 블록:

```python
def _conclusion_block(card: Any) -> None:
    """조사 결론 — 카드의 '그래서 뭐가 문제인가'를 맨 위에(문제② 결론 주체)."""

    from dashboard.card_data import conclusion_view

    view = conclusion_view(card)
    if view is None:
        st.caption("조사 미수행 — LLM 미실행 또는 실패(결론 없음을 숨기지 않음).")
        return
    st.markdown(f"🧭 **결론** — {view['headline']}")
    if view["cause_path"]:
        st.markdown("원인 경로")
        st.markdown("\n".join(f"{i}. {s}" for i, s in enumerate(view["cause_path"], 1)))
    if view["anomaly_points"]:
        st.markdown("이상 지점")
        st.markdown("\n".join(f"- {s}" for s in view["anomaly_points"]))
    if view["open_questions"]:
        st.markdown("남은 확인사항")
        st.markdown("\n".join(f"- {s}" for s in view["open_questions"]))
    method = "분해로 설명 완료(요약 1회)" if view["method"] == "gate_summary" else (
        f"도구 조사 {view['tool_requests']}회"
    )
    status = "원인 규명 완결" if view["resolved"] else "미해결 — 외부검증 우선 대상"
    st.caption(f"{method} · {status}")
```

`_card_body` 첫 줄에 `_conclusion_block(card)` 호출 추가(기존 검토 포인트·①②③④는 유지).
카드 단추 라벨(`render_cards_section`): headline은 `conclusion_view(card)`가 있으면 그
headline을 우선 사용, 없으면 기존 `card_headline` 폴백.

- [ ] **Step 4: 통과 + 대시보드 임포트 확인**

Run: `uv run pytest tests/test_card_data.py tests/test_cards_store.py tests/ -x -q`
Run: `uv run python -c "import dashboard.card_view, dashboard.card_data"`
Expected: 전체 PASS, 임포트 무오류

- [ ] **Step 5: 커밋**

```bash
git add dashboard/card_data.py dashboard/card_view.py tests/test_card_data.py tests/test_cards_store.py
git commit -m "feat(ui): 카드 최상단 조사 결론 블록 + 결론 영속화 왕복 검증"
```

---

### Task 9: 실 LLM 프로브 (카드 2~3장 실측) — 비용 발생, 사용자 실행

**Files:**
- Create: `data/backtest/_probe_investigator.py`

**Interfaces:**
- Consumes: `src.report.cards_store`(저장된 카드 로드), `run_investigation`.

- [ ] **Step 1: 프로브 스크립트 작성**

```python
# data/backtest/_probe_investigator.py
"""조사원 프로브 — 저장된 카드 상위 N장에 실 LLM 조사를 태워 품질·비용 실측.

사용: uv run python data/backtest/_probe_investigator.py <corp_code> <year> [n_cards]
전면 배선 전 게이트 통과율·왕복 수·결론 품질을 사람이 확인하는 용도(비용 수백 원).
"""

import asyncio
import json
import sys

from src.report.cards_store import load_cards  # 실제 함수명은 cards_store.py 확인 후 맞춤
from src.report.decomposition import decompose_change, load_bridges
from src.report.investigator import needs_tool_loop, run_investigation
from src.report.investigation_config import load_investigation_config


async def main(corp: str, year: int, n_cards: int = 3) -> None:
    stored = load_cards(corp, year)  # {"cards": [...], "series_rows": [...]} 형태 가정 — 확인 후 맞춤
    cards = sorted(stored["cards"], key=lambda c: c.priority_score, reverse=True)[:n_cards]
    report = {"account_level_series": stored["series_rows"], "target_year": year}
    bridges = load_bridges()
    gate = (load_investigation_config().get("investigation") or {}).get("gate", {})
    for card in cards:
        decomp = decompose_change(stored["series_rows"], card.account, year, bridges)
        print(f"\n=== {card.account} | 게이트: {'루프' if needs_tool_loop(decomp, gate) else '요약'}")
        conclusion = await run_investigation(card, report, decomp)
        if conclusion is None:
            print("  실패/미수행")
            continue
        print(json.dumps(conclusion.model_dump(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    corp, year = sys.argv[1], int(sys.argv[2])
    n = int(sys.argv[3]) if len(sys.argv) > 3 else 3
    asyncio.run(main(corp, year, n))
```

(cards_store의 실제 로드 함수명·반환 형태는 구현 시 `src/report/cards_store.py`를 읽고 맞춘다.)

- [ ] **Step 2: 커밋**

```bash
git add data/backtest/_probe_investigator.py
git commit -m "test(probe): 조사원 실 LLM 프로브 스크립트 — 카드 N장 품질·비용 실측"
```

- [ ] **Step 3: 사용자 실행 대기** — `uv run python data/backtest/_probe_investigator.py 00126380 2024 3`
  (삼성, 저장된 카드 필요. 비용 발생이므로 사용자 승인 후 실행. 결과·비용을 STATE.md에 기록.)

---

### Task 10: 문서 갱신 + 최종 검증

**Files:**
- Modify: `docs/agent/STATE.md` (현재 위치에 이번 구현 항목 추가)
- Modify: `docs/user/UI.md`·`docs/user/FEATURES.md` (결론 블록·점수 표기 — 위험 라벨 폐지 반영)
- Modify: `docs/agent/PLAN.md` §5 조사 단계의 "구현 전" 표기 → 1단계 구현 완료로 (프로브는 별도 명시)

- [ ] **Step 1: 전체 테스트 + mojibake 확인**

Run: `uv run pytest tests/ -q 2>&1 | tail -5`
Expected: 전체 PASS (기준선: 착수 전 카운트 대비 신규 실패 0)
Run: `uv run python -c "import pathlib; bad=chr(0xFFFD); hits=[p for d in ('docs','src','dashboard','config') for p in pathlib.Path(d).rglob('*') if p.is_file() and p.suffix in {'.py','.md','.yaml'} and bad in p.read_text(encoding='utf-8', errors='ignore')]; print(hits or 'CLEAN')"`
Expected: CLEAN
(주의: 검사 문자는 chr(0xFFFD)로만 표현 — 리터럴로 넣으면 이 파일 자체가 가드에 걸린다.)

- [ ] **Step 2: 문서 편집**

STATE.md 최상단 "현재 위치"에 항목 추가: 구현 4항목(병합·조사원·결론 배선·연속 점수),
테스트 수, 프로브 실행 여부(미실행이면 "⏭ 프로브 실측 대기(비용)"), 남은 백로그
(반박 도구 승격·카드 횡단 종합). UI.md·FEATURES.md는 위험 라벨 문구를 점수·결론으로 교체.

- [ ] **Step 3: 커밋**

```bash
git add docs/
git commit -m "docs: 조사원 파이프라인 1단계 반영 — 상태·UI 문서 갱신"
```

---

## Self-Review 결과

- **스펙 커버리지**: 1단계 4항목 — ④병합=Task 4, 조사원=Task 5·6·7, 결론 최상단+반박 입력=Task 7·8, ③연속 점수=Task 2·3. 게이트=Task 5, 설정 외부화=Task 1, 프로브=Task 9. 갭 없음.
- **타입 일관성**: `priority_score`(float)·`investigation`(InvestigationConclusion|None)·`merged_children`(list[str])은 Task 2·5에서 정의, Task 3·7·8이 동일 이름으로 소비. `run_investigation` 시그니처는 Task 6 정의 = Task 7·9 소비 일치.
- **알려진 불확실 지점(구현자가 현장 확인)**: ① cards_store의 함수명·반환 형태(Task 8·9에 확인 지시 명시) ② report_html.py·report_view.py의 risk_level 잔존(Task 3 Step 1 grep이 전수 포착) ③ pydantic_ai 버전의 `UsageLimits` import 경로(`pydantic_ai.usage` 기준, 다르면 기존 코드의 사용례 검색).
