# 6. 환각 방지 4중 장치

> **위치**: 5관점 발견과 카드 조립 사이, 그리고 LLM 출력 전 구간을 관통한다. 원칙 4("LLM은 풀되 사실에 앵커링")의 구체적 구현. LLM의 자유 추론은 1종오류(과잉지적)를 유발하므로 **네 겹**으로 막는다.

## 6.1 4중 장치 개요

```
                 LLM 관점 출력 (SuspicionItem)
                          │
   ┌──────────────────────┼──────────────────────┐
   ▼                      ▼                      ▼
① tool DSL 앵커링      ② grounding            ③ 어휘 게이트
LLM은 함수만 고름      원 단위 복원 대조      내부 식별자 반려
숫자는 코드가 계산      환각 탈락              (ModelRetry)
   │                      │                      │
   └──────────┬───────────┴──────────┬───────────┘
              ▼                       ▼
        ④ 금액 환산 병기         (반박 에이전트)
        LLM 나누기 오류 제거      근거 없는 주장 기각
```

| 장치              | 무엇을 막나                 | 출처                                       |
| ----------------- | --------------------------- | ------------------------------------------ |
| ① tool DSL 앵커링 | LLM이 숫자를 지어냄         | `analysis_tools/`·`investigation_tools.py` |
| ② grounding       | 인용 수치가 실데이터에 없음 | `grounding.py`                             |
| ③ 어휘 게이트     | 백데이터 내부 식별자 노출   | `vocab_guard.py`                           |
| ④ 금액 환산 병기  | LLM 자릿수 나누기 오독(÷10) | `amounts.py`                               |

## 6.2 ① tool DSL 앵커링

LLM에게 자유 SQL을 주지 않는다(D1). LLM은 "어떤 함수를 호출할지"만 고르고, SQL은 코드가 생성·실행한다. 안정성과 설명력(어떤 분석을 했는지 함수명에 남음)을 함께 얻는다.

`analysis_tools/__init__.py`는 "SQL stays inside this package"를 선언하고 `account_series`·`compare_growth`·`compute_ratio`·`yoy_growth_pct` 등을 노출한다. 조사원 도구(`investigation_tools.py`)의 `get_series`·`get_decomposition`·`find_notes`·`top_changes`는 전부 순수함수라 **LLM은 이 반환값 밖 숫자를 만들 수 없다**. 예: LLM이 "매출채권이 이상"이라는 가설을 세우면 `compare_growth("매출채권","매출")`을 호출하고, 엔진이 실측한 결과를 LLM이 해석만 한다.

## 6.3 ② grounding — 원 단위로 복원해 자릿수까지 대조

`grounding.py`가 가장 핵심적인 장치다. 관점 의심건의 인용 수치가 실데이터에 있는지 코드가 대조한다. 인용에 단위(조·억·백만·천원·원)가 붙어 있으면 **원 단위 절대값으로 복원해 자릿수까지** 비교하고, LLM이 반올림해 쓰는 것을 감안해 허용오차(상대 1% 또는 절대 100만원) 안에서 판정한다.

예전에는 유효숫자(trailing-zero 제거) 동일성으로 봤다. 스케일을 아예 무시했기 때문에 `1,961억`·`1,961백만`·`1,961`이 전부 같은 `"1961"`로 정규화돼, **자릿수가 8자리 틀려도 grounded로 통과**했다. 그 규칙이 필요했던 이유는 LLM이 원 단위 숫자를 받아 스스로 억으로 나눠 인용하던 시절 단위가 제각각이었기 때문인데, ④ 금액 환산 병기(`amounts.py`)가 입력 경계에서 나눗셈을 걷어낸 뒤로 근거가 사라져 제거했다.

단위 없는 짧은 맨숫자(`1,961`)만 복원이 불가능하다. 이것만 유효숫자 대조로 남기되 `value_verified=False`로 내려 **"존재는 확인, 자릿수는 미확인"**임을 카드에 정직하게 표시한다 — 검증하지 않은 것을 검증했다고 말하지 않는다.

인덱스는 series_key/canonical/label/account_id를 원 단위 절대값 집합으로 색인하며, **sj_div 한정 키도 색인**해(동명이계 오매칭 차단, verify가 우선 조회) 손익계산서와 현금흐름표의 같은 계정명·다른 금액을 구분한다. 주석 fact는 `note:{label}`/`note:{category}` 네임스페이스로 색인하고, 서술형 공시(담보·특수관계자)는 token별 + 전역 `__disclosure__` 풀로 색인한다(사각#3 해결).

판정 규칙:
- 계정 미존재·금액 불일치 → grounded=False
- 관계는 **모든 다리가 실존**해야 grounded(가짜 관계 날조 차단)
- external 분기(출처 URL 검사)는 코드에 있으나 라이브에선 도달 불가(external은 발견자가 아니라 grounding에 안 들어온다), industry는 참고이므로 탈락 안 함(D15)
- **탈락도 reason과 함께 전부 반환**(silent drop 0)

`classify_ref`가 근거 종류(resolved_kind)를 코드로 판정한다 — 렌더러가 locator 모양을 역추정하던 두더지잡기의 근본 해결이다. 규칙은 형식 예상 금지: 서술 네임스페이스→note/narrative, 색인 실존→account, 한글 없는 미해석→metric(표시 금지), 나머지는 값 금액이면 account 아니면 narrative(드롭 없음).

## 6.4 ③ 어휘 게이트 — grounding의 언어 버전

grounding이 숫자에 하는 일을 어휘 게이트(`vocab_guard.py`)는 언어에 한다. LLM 출력에 백데이터 내부 식별자(`target_value`·`peer_median`·`delta_score`·`ratio_time_series`)가 새면 코드가 `ModelRetry`로 반려한다("내부 식별자 쓰지 마라, 감사인 회계언어로 재작성").

금지 목록은 손 열거가 아니라 **입력 dict 키에서 자동 추출**한다 — 모집단이 입력이라 새 필드가 추가돼도 자동 커버되고(두더지잡기 방지), 오탐을 막기 위해 5자 이하 일반 단어·감사 약어(roe·dso·trend)는 금지하지 않고, 구조 필드(locator·cluster_key)는 면제한다(계정 앵커 내부 키는 정당). 단일 단어 6자+ 키(decomposition·residual)도 금지 대상이다. 이 게이트는 perspective_runner·investigator·rebuttal 세 곳에 부착된다.

## 6.5 ④ 금액 환산 병기 — 나누기 오류를 원천 제거

LLM이 "1조 2,534.7억"을 "1,253.47억"으로 ÷10 축소하는 오독을 막는 방법은, 환산 작업 자체를 LLM에서 걷어내는 것이다. `amounts.annotate_amounts`(`ANNOTATE_THRESHOLD=1e8`)는 LLM 입력 경계에서 원값에 환산 표기를 병기한다:

```
1,253,469,878,367  →  "1,253,469,878,367(1조 2,534.7억)"
```

원값을 앞에 남겨 grounding 유효숫자 대조를 통과시키고, 프롬프트는 "그대로 옮겨 쓰기"로 교체한다(LG생건 감사 결함② 근본 차단). perspective_runner·investigator 두 곳이 json.dumps 직전 호출한다(rebuttal 경로는 미호출).

`figure_sheet.py`는 반박 서술 수치를 한 단계 더 감사하기 위한 장치다 — 구현·테스트만 완료됐고 파이프라인 배선은 보류 상태다(현재 반박 경로에서 호출되지 않는다). 설계는 as-filed series에서 KEY_TOTALS의 정확 수치를 코드가 계산해 LLM에 주고, 서술에 등장한 숫자가 그 도표의 멤버인지 감사하는 것이다(파생값 환각 차단). 연속 YoY만 집합에 넣어, 다년 임의 쌍 델타가 집합을 넓혀 환각(아스트 583.1억)을 흡수하는 것을 막는다. "LLM에 준 작은 도표"의 정확 멤버십이라 전역 DB 대조보다 신뢰할 수 있다.

## 6.6 에이전트 레벨 가드레일

에이전트 출력 검증(`guardrails.py`)도 있다 — 단 부착 지점은 구경로 단일 에이전트(numeric_analyst·note_analyst)뿐이고, Phase2 관점 에이전트에는 어휘 게이트(vocab_guard)만 걸려 있다. `BANNED_EXTERNAL_FACTS`(반도체 불황·뉴스·시장점유율·금리 인상으로·AI 수요)나 `BANNED_CERTAINTY`(명확히 증명·확정·부정 적발·분식)가 출력에 하나라도 있으면 `ModelRetry`로 반려한다 — 포지셔닝 원칙(부정 확정 금지)의 강제 지점이다. numeric_evidence와 flow_evidence가 둘 다 비어도 반려한다. retry 정책은 provider별로 나뉘며(`gemini_retry`·`model_retry`, delays (2,4,8,16)), 특히 `insufficient_quota`는 "일시적 아님"으로 판정해 헛재시도 후 빈 결과로 둔갑하는 hollow-PASS를 차단한다(`model_retry.py:26-27`).

## 6.7 실증 예시 — 대주 담보·특수관계 서술이 "환각"으로 죽던 것을 부활

담보·특수관계 등 서술형 공시는 report_extracts(사업보고서 본문 추출)에 사는데, 과거 grounding 인덱스는 XBRL fact만 커버했다. 그래서 진짜 공시가 "환각"으로 죽는 **허위 탈락**이 발생했다(사각#3). 이 경로는 XBRL 주석이 없는 회사연도(2022년 이하가 사실상 전부)에서 특히 결정적이다 — 그때는 report_extracts가 주석 근거의 유일한 출처다.

수리는 `build_account_index(note_disclosures=...)`로 서술형 공시를 색인에 넣고, `_verify_note_suspicion`이 라벨 미매칭이라도 인용 금액이 disclosure 풀에 있으면 grounded를 주도록 한 것이다. card_pipeline이 materials[note]의 서술형 공시를 정규화 전달한다. 대주 실측: 담보 54,345·특수관계 233,546이 둘 다 탈락→grounded로 부활했고, 동시에 허위 금액 99,999는 탈락을 유지했다(환각 가드 보존). "진짜 공시를 살리되 지어낸 금액은 여전히 죽인다" — precision과 recall을 동시에 지킨 근본 해결이다.
