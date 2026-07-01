# PHASE2_DESIGN — 멀티에이전트 교차검증 단단설계

> Phase1(수집→정규화→신호→온보딩 게이트)이 만든 라우팅 재료를 받아, 6관점이 독립
> 검토 → 코드가 결정론으로 교차·집계 → 반박 에이전트가 반대근거를 채워, 감사인이 바로
> 쓰는 **의심건 카드 목록**을 산출한다. 설계 단일 출처는 [PLAN.md](PLAN.md)이며 본 문서는
> Phase2 레이어(L3/L4)의 확정 설계다. grill 합의(17개 결정) 기반. 작성 2026-06-20.

> **포지셔닝 고정**: 부정을 확정하지 않는다. 모든 카드는 반대근거·정상설명·확인질문·
> 다음절차를 포함한다. 도구는 후보를 제시하고, 확정은 감사인이 한다([CLAUDE.md](../../CLAUDE.md)).

## 1. 현재(기초 설계)의 한계

기존 MVP는 동작하나 핵심이 비어 있다.

| 단계            | 기존 상태                                     | 문제                                   |
| --------------- | --------------------------------------------- | -------------------------------------- |
| 6관점 독립 검토 | `perspectives.py` 자유텍스트 요약+risk_areas  | 근거 검증·앵커링 없음, 순차 실행       |
| 교차검증        | `crosscheck.py` 하드코딩 4단어 substring 매칭 | 결과 1건만, §3 위반, 핵심가치가 최빈약 |
| 반박(⑤)         | 부재                                          | PLAN 원칙④·포지셔닝 계약 미이행        |
| 종합            | `synthesis.py` 단문 1문단                     | 감사인이 못 씀, 카드 구조 아님         |

`AccountFinding`(findings.py)에 이미 카드의 7요소(materiality/anomaly/confidence·counter_evidence·
normal_explanation·confirm_question·next_procedure·EvidenceRef)가 정의돼 있으나 멀티에이전트
흐름이 이를 쓰지 않았다. 본 설계는 **원설계로 되돌리고 결정론 골격을 채우는 것**이다.

## 2. grill 결정 매핑표 (17)

| #   | 결정 항목              | 확정안                                                                         |
| --- | ---------------------- | ------------------------------------------------------------------------------ |
| 1   | 최종 산출물            | 의심건별 카드 목록(자유 단문/점수 대시보드 아님)                               |
| 2   | 카드 묶는 방식         | 관점이 양식 제출 → 코드가 계정별 클러스터(교차검증=결정론)                     |
| 3   | 계정 밖 의심건 앵커링  | 계정 우선 + 회사레벨 버킷 별도(흐름=대표+관련계정 세트)                        |
| 4   | 반박 담당              | 전용 반박 에이전트 1명, 카드 전체 일괄 1회                                     |
| 5   | 근거 grounding         | 구조화 EvidenceRef{계정ID·연도·수치} 필수 + 코드 대조, 환각 탈락               |
| 6   | "몇 명 지적" 카운트    | 내부 4관점만 N/4 + 외부·동종은 참고배지(D15)                                   |
| 7   | 반박의 카드 제거 권한  | 절대 제거 안 함, 강등+표시만(가짜수치만 탈락)                                  |
| 8   | 카드 정렬              | 표수 내림 → 동점 시 금액(materiality) 내림                                     |
| 9   | 구현 순서              | 결정론 골격 먼저(TDD) → 그 위에 LLM 관점·반박                                  |
| 10  | 위험도/이상도 점수     | 코드가 Phase1 신호에서 결정론 계산(원칙①), AI는 점수 안 매김                   |
| 11  | 회사레벨 카드 배치     | '회사 전체 이슈' 별도 섹션                                                     |
| 12  | 확신도 표시            | 표시함, 코드 산정(매핑강도+근거검증+표수)                                      |
| 13  | 의심건 0건(정상 회사)  | "계정 N개·관점 6개 검토, 의심건 0" 검토범위 명시(§9)                           |
| 14  | 유형(issue_type) 분류  | 9종 enum + '기타' 안전판 + 자유부제 병기(자주 나오면 enum 승격)                |
| 15  | 관점당 의심건 개수상한 | 상한 없음, 유의성 우선 가드만(결함① 교훈)                                      |
| 16  | 외부·동종 근거 검증    | 검증 가능한 만큼만(peer DB 대조 / URL 존재), 나머지는 확신도로 솔직히          |
| 17  | 반박의 강등 권한 범위  | 원 위험도 보존 + 판정 플래그(정상우세/반반/의심우세)만, 숫자 직접변경 금지(§9) |

## 3. 카드 1장의 구성

| 칸                         | 내용                           | 출처           |
| -------------------------- | ------------------------------ | -------------- |
| 무엇이 이상                | 계정·연도·이상 근거            | 관점 AI 발견   |
| 유형                       | 9종 + '기타'(자유부제 병기)    | 관점 AI        |
| 몇 명이 지적               | 내부 N/4 + 외부·동종 참고배지  | 코드 집계      |
| 금액유의성·이상도          | 결정론 점수                    | 코드(Phase1)   |
| 확신도                     | High/Med/Low(검증 가능한 만큼) | 코드 산정      |
| 반박 판정                  | 정상우세 / 반반 / 의심우세     | 반박 AI 플래그 |
| 정상이유·확인질문·다음절차 | 반대근거                       | 반박 AI        |

카드 타입 = 기존 `AccountFinding` 재사용 + 메타(표수·참고배지·반박 플래그) 추가. 회사레벨
카드는 계정 앵커가 없으므로 N/4=0, 참고배지·확신도로 표현.

## 4. 파이프라인

```
6관점 독립 검토 (numeric·note·flow·change=GPT-5.4 / external=Gemini / industry=peer)
  └ 각 관점 출력 = 구조화 의심건 리스트
       {issue_type, subtype, account_id(locator), year, cited_value, 근거설명}
       개수상한 없음. 프롬프트에 "유의성 큰 것 우선" 가드만.
        │
[코드 결정론 골격]   ← §9 단계: 먼저 구현·테스트로 고정(LLM 없이 검증)
  ① 근거검증 (grounding)
     - 계정 의심건: cited_value 가 account_level_series 의 (account_id, year) 실값과
       round 후 일치하나(accounting-precision). 불일치=환각 → 탈락.
     - 외부 의심건: 출처 URL 존재만 확인(내용 검증 불가) → 통과하되 낮은 확신도.
     - 동종 의심건: peer DB에 해당 지표·분위수 존재하나 대조 → 통과/탈락.
  ② 클러스터
     - account_id(locator)로 묶음 → 계정 카드.
     - 계정 앵커 없음(외부·동종·지배구조·소송) → 회사레벨 버킷 카드.
     - 흐름 관점의 다계정 관계는 대표 계정에 묶고 관련 계정 세트를 카드에 첨부.
  ③ 점수·집계
     - 표수 = 그 클러스터를 지적한 내부 4관점 수(N/4). 외부·동종은 참고배지.
     - materiality·anomaly = Phase1 신호에서 코드 계산(절대금액·총계대비·z·항등식위반).
     - confidence = 매핑강도 + 근거검증 통과 + 표수로 코드 산정.
        │
[반박 에이전트 1회 일괄]  GPT-5.4(reasoning)
  └ 묶인 카드 전부를 받아 카드별로 채움:
     - counter_evidence(숫자상 반대 가능성)·normal_explanation(정상 사업 설명)
     - confirm_question·next_procedure
     - 반박 판정 플래그(정상우세/반반/의심우세) ※risk_level 숫자 직접 변경 금지(§9)
        │
[정렬·표시]
  - 계정 섹션: 표수 내림 → 동점 시 materiality 내림. '정상우세' 플래그 카드는 하단 강등 표시.
  - 회사레벨 섹션: 별도.
  - 의심건 0건: "계정 N개·관점 6개 검토, 제기된 의심건 0" 검토범위 명시(빈 화면 금지).
```

## 5. 기존 코드 처분 (ripple)

| 파일                     | 처분   | 내용                                                                           |
| ------------------------ | ------ | ------------------------------------------------------------------------------ |
| `report/crosscheck.py`   | 폐기   | 하드코딩 키워드 매칭 → 결정론 클러스터/집계 모듈로 대체                        |
| `report/perspectives.py` | 교체   | `PerspectiveAssessment` → 구조화 의심건 리스트(EvidenceRef 강제), 6관점 병렬화 |
| `report/synthesis.py`    | 전환   | 단문 종합 → 반박 에이전트(카드 채우기 + 판정 플래그)                           |
| `report/materials.py`    | 유지   | 관점별 입력 발췌는 그대로(필요 시 EvidenceRef locator 노출 보강)               |
| `report/multi_agent.py`  | 재배선 | 순차 `_assess` → asyncio.gather 병렬 + 신규 골격·반박 배선                     |
| `schemas/findings.py`    | 재사용 | `AccountFinding`에 표수·참고배지·반박 플래그 메타 필드 추가                    |

## 6. 가드 점검 (위반 0 확인)

- **포지셔닝**: 모든 카드에 counter_evidence·normal_explanation·confirm_question·next_procedure
  필수(빈칸 제출 거부). "분식 확정" 문구 금지, 반박 판정으로 정상 가능성 항상 병기.
- **§3(하드코딩 금지)**: 관점·코드 어디서도 개수상한(head/limit) 금지(결함① 교훈). 계정ID·연도·
  임계는 데이터/인자에서. 동의어 사전 같은 리터럴로 교차검증을 구동하지 않음(클러스터는 account_id).
- **§9(은폐 금지)**: 반박은 카드를 제거 못 함(플래그만). 가짜수치(grounding 실패)만 탈락. 의심건
  0건은 검토범위를 수치로 표시(hollow-PASS 차단).
- **§10(전수)**: 전수는 사용자 요청 시에만. 본 설계 검증은 백테스트 6사 회귀 가드 + 2+ 회사 E2E로
  적정 범위. 결정론 골격은 단위테스트로 전수 고정.

## 7. 단계별 구현계획 (TDD, 결정론 골격 먼저)

| 단계 | 산출물                                                                 | 검증기준                                                                   |
| ---- | ---------------------------------------------------------------------- | -------------------------------------------------------------------------- |
| S1   | 의심건 스키마(`SuspicionItem`)·EvidenceRef locator 규약·카드 메타 필드 | unit: 스키마 직렬화·필수필드 강제 통과, 빈칸 제출 거부 RED→GREEN           |
| S2   | 근거검증 모듈(cited_value↔실값 round 대조, 외부 URL·동종 peer 대조)    | unit: 일치=통과/불일치=탈락/외부=저확신 가짜 material 케이스 ≥6            |
| S3   | 클러스터·회사레벨 버킷·N/4 집계·점수(materiality/anomaly/confidence)   | unit: 동일 account_id 묶임·앵커없음 버킷행·표수 정확, 가짜 material 케이스 |
| S4   | 정렬(표수→금액)·정상우세 강등·0건 검토범위 표시·markdown 렌더          | unit: 정렬 순서·0건 메시지·강등 위치 고정                                  |
| S5   | 관점 구조화 출력 교체 + 6관점 병렬(`multi_agent.py` 재배선)            | E2E: 2+ 회사 실행 산출, 백테스트 6사 무회귀(recall 5/6·FP0 유지)           |
| S6   | 반박 에이전트(synthesis→전환), 카드 일괄 채움 + 판정 플래그            | E2E: 카드 4필드 비어있지 않음, 반박이 카드 제거 0건                        |
| S7   | `crosscheck.py` 폐기 + ripple-search(perspectives 스키마 파급 점검)    | grep: PerspectiveAssessment·crosscheck 참조 0, pytest 전체 green           |

**ripple 점검(S5/S7 필수)**: `perspectives.py` 스키마 변경은 `multi_agent.py`·테스트·dashboard·
materials 참조에 파급. `ripple-search`로 `PerspectiveAssessment`·`cross_check_assessments`·
`create_integrated_summary` 호출처 전수 확인 후 일괄 수정.

## 8. 비용·모델

- 관점 6 + 반박 1 = 회사당 LLM 7회(기존 6+1과 동급). 내부·반박=GPT-5.4(reasoning), external=Gemini.
- 반박 일괄 1회로 카드별 개별 호출(10~30회) 회피. 깊이 부족 시 후속 백로그에서 카드별 승격 검토.

## 9. S5 관점 출력·프롬프트 확정 (grill 2026-06-20)

S5 착수 전 grill로 5개 세부 확정. 핵심: "관점은 역할만, 데이터로 흐른다"(원칙②)·외부화(원칙③)·
grounding 단일 출처(§9).

| 항목                | 확정안                                                                                                                    |
| ------------------- | ------------------------------------------------------------------------------------------------------------------------- |
| 출력 타입           | `PerspectiveOutput {status, suspicions: list[SuspicionItem]}` — agent당 봉투 1개                                          |
| SuspicionItem 보완  | 선택 필드 3개 추가: `related_accounts: list[str]`(흐름)·`prior_value`·`prior_year`(변동). 안 쓰는 관점은 빈값             |
| perspective 라벨    | 코드가 강제 재주입(LLM 자기라벨링 불신)                                                                                   |
| 빈 결과             | status="deferred"/빈 suspicions 명시(빈칸 숨김 금지)                                                                      |
| 프롬프트 위치       | 공통 system prompt=코드(역할·grounding·금지·출력양식), 관점별 focus·금지·예시=`config/playbooks/perspective_prompts.yaml` |
| grounding 검사 단계 | 양식(필드·타입)=PydanticAI agent / 환각(수치 실재)=S2 코드 한 곳(중복·result_validator grounding 안 함)                   |

- **한 봉투 통일 근거**: 6관점 출력이 구조적으로 동일("계정(들)의 연도별 의심 + 근거"). 관점별
  차이는 위 3개 선택 필드뿐 → 관점별 스키마(분기·중복·S1~S4 재작업)는 비용 대비 손해라 기각.
- **S5 배선**: 6관점 병렬(asyncio.gather) → `verify_suspicions`(S2) → `build_cards`(S3) →
  `build_card_report`+`render_card_markdown`(S4). 백테스트는 결정론 신호만 쓰므로 관점 변경 무영향(grep 확정).

## 10. S6 반박 에이전트 확정 (grill 2026-06-20)

전용 반박 에이전트 1명이 카드 전체를 일괄 1회 받아 반대근거를 채운다. 위험도 숫자는 보존하고
판정 플래그만 부여(§9), 카드는 절대 제거하지 않는다.

| 항목      | 확정안                                                                                                                                                         |
| --------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 태도      | 균형 반박 — 정상 설명 가능성과 의심 유지 근거를 공정히 따짐(과도 적대 금지, §9)                                                                                |
| 입력      | 카드 요약 + 그 카드를 만든 의심건들(관점 description·cited_value·근거). 회사 자료 통째 X                                                                       |
| 출력 타입 | `RebuttalOutput {entries: list[RebuttalEntry]}`, `RebuttalEntry{cluster_key, verdict, counter_evidence, normal_explanation, confirm_question, next_procedure}` |
| 매칭      | cluster_key로 카드에 매칭. 없는 cluster_key 항목은 무시(새 카드 날조 금지)                                                                                     |
| 실패·누락 | 반박 없는 카드는 "반박 미수행" 표시 + 빈칸으로 그대로 노출(제거·강등 없음). 전체 실패해도 카드 목록 생존                                                       |
| 권한      | risk_level 숫자 직접 변경 금지, verdict(normal_dominant/mixed/suspicion_dominant)만                                                                            |
| 호출·모델 | 일괄 1회, GPT-5.4(reasoning)                                                                                                                                   |

- **S6 배선**: card_pipeline에서 build_cards 직후 반박 1회 호출 → entries를 cluster_key로 카드에 주입
  (counter_evidence·normal_explanation·confirm_question·next_procedure·rebuttal_verdict) → 정렬(S4 정상우세 하단).
- 렌더는 verdict=None 카드에 "반박 미수행"을 명시(빈칸 숨김 금지).
