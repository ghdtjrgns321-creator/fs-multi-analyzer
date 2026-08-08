# 5. L3/L4 — 5관점 발견 → 카드 → 조사·반박·외부검증

> **위치**: L2 신호엔진 → `[L3 5관점 + L4 카드 파이프라인]` → L5 Human. Phase2의 핵심. 산출물은 자유 단문이 아니라 **의심건 카드 목록**이다(PHASE2_DESIGN, grill 17결정).

## 5.1 내부 흐름

```
materials.py (관점별 발췌, 등수 힌트 없음)
   │
   ▼  asyncio.gather 병렬 (발견 5관점 — external은 발견자 아님)
┌──────────┬──────────┬──────────┬──────────┬──────────┐
│ numeric  │  note    │  flow    │  trend   │ industry │
│ 당해급변  │ 서술리스크│ 관계교차  │ 다년추세  │ 업종분위  │
│ GPT-5.4  │ GPT-5.4  │ GPT-5.4  │ GPT-5.4  │ GPT-5.4  │
└──────────┴──────────┴──────────┴──────────┴──────────┘
   │  PerspectiveOutput{status, suspicions}  (completed/deferred/failed)
   ▼
grounding.verify_suspicions  →  원 단위 복원 대조로 환각 탈락 (silent drop 0)
   ▼
card_builder  →  계정/관계/회사 클러스터 + 표수 N/4 + 사전식 정렬 + 브리지 병합
   ▼
decompose_change 부착  →  investigator (도구 루프)  →  rebuttal ∥ external_verify (Gemini 뉴스검색 — 카드 확정 후 타깃 검증)
   ▼
card_report  →  정렬(표수→금액) + markdown 렌더
```

## 5.2 구조

| 구성요소               | 개수                                                    | 출처                                       |
| ---------------------- | ------------------------------------------------------- | ------------------------------------------ |
| 검증 관점              | 6 (내부 4 + 외부·동종 2)                                | `PerspectiveName`, `suspicion.py:17`       |
| 표수 카운트 대상(내부) | 4 (numeric·note·flow·trend)                             | `INTERNAL_PERSPECTIVES`, `suspicion.py:18` |
| 카드 scope             | 3 (account·relationship·company)                        | `SuspicionScope`                           |
| 조사원 도구            | 4 (get_series·get_decomposition·find_notes·top_changes) | `investigation_tools.py`                   |
| 반박 verdict           | 3 (normal_dominant·mixed·suspicion_dominant)            | `RebuttalVerdict`                          |
| 정렬 기준              | 사전식 — 표수 내림 → 금액 내림 (반박 판정 미개입)       | `src/report/card_order.py`                 |

## 5.3 왜 6개 독립 관점인가

한 AI가 전부 판단하면 한 관점에 매몰된다. 여섯 관점이 **독립 실행**(타 관점 결과를 입력으로 안 받음) 후 충돌을 잡는 것이 신호다 — "숫자는 위험한데 주석은 잠잠하다 → 더 의심"(MULTI_AGENT). 관점은 직교 차원이다(PLAN §5):

- **numeric**(정량×수준): 당해 급변(YoY 튐) 전담. 금액 수준·구성비 이상.
- **note**(정성×수준): 우발·약정·소송·특수관계·담보·계속기업 서술. 발췌 누락 ≠ 공시 누락. 입력은 두 갈래다 — XBRL 주석 fact(`note_facts`, 2023년 이후 회사연도만 존재)와 사업보고서 본문 추출(`report_extracts`, 전 연도). `note_material`이 둘을 각각 다른 안내문으로 실어 근거의 등급(회사 태깅값 vs LLM 추출물)을 구분한다.
- **flow**(공간교차): 매출↔매출채권↔영업CF, 이익↔법인세 계정 간 모순. scope=relationship. 연결↔별도 현금 괴리.
- **trend**(시간교차): 당해 급변 안 봄(numeric 전담). 다년 기울기 드리프트·가속만.
- **external**(외부맥락): grounding URL 있는 항목만. 원인 뉴스 검색 — 설명이지 면죄부 아님. 내부 위험 안 키움(참고).
- **industry**(동종): peer baseline(benchmark)만. 사업구조 차이 한계 명시(ISA/KSA 520 참고 신호).

**발견자/검증자 분리**(2026-07 재편)가 중요하다. 발견자(industry 포함 5관점)는 카드가 생기기 전 병렬로 넓게 스캔하고, 검증자(반박·외부검증)는 카드가 만들어진 **뒤** 카드별로 붙어 깊게 판다. external은 발견자에서 검증자로 옮겨졌다 — 카드 없이 막연히 회사명을 검색하는 것보다 분해로 좁혀진 가설("판관비 기여 −54%")을 들고 검색하는 쪽이 질·비용 모두 우위이기 때문이다.

## 5.4 프롬프트는 데이터 — perspective_prompts.yaml

관점 프롬프트는 코드에 없다(원칙3). `perspective_runner.py`가 공통 `shared`(role·grounding·forbid·output)와 관점별 `focus`를 합성한다. `shared.role` 원문 요지:

> "너는 공시 재무제표 리뷰 도구의 독립 관점 에이전트 중 하나다. 제공된 material_board만 사용. 다른 관점 결과 미참조. 외부사실·뉴스·업종기억·인과단정 금지. **코드가 순위를 안 정해주므로 account_metrics_panel(전 계정 계산값) 전체를 훑어 유의 계정을 직접 선정**하라."

출력 규칙이 포지셔닝을 강제한다 — issue_type은 **재무제표 영역 축**(분식 가설 아님)이고 구체 위험(계속기업·이익의 질)은 subtype 자유서술로 내린다. description은 두괄식·환산표기 그대로(스스로 나누기 금지)·내부 필드명(z점수·target_value) 금지다.

관점 실행 후 3가지 코드 개입이 hollow-PASS를 막는다:
- **상태 3분기**: LLM 에러=`failed`(suspicions=[]), 키없음=`deferred`(의도적 스킵), 정상=`completed`. 에러를 "0건 위험없음"으로 둔갑시키지 않는다.
- **perspective 라벨 코드 재주입**: LLM이 틀린 라벨("note")을 달아도 실행한 관점("numeric")으로 재스탬프(LLM 자기 라벨 불신).
- **어휘 게이트 부착**: material_board 키를 banned_vocab으로(입력이 모집단이라 새 필드 자동 커버).

## 5.5 카드 조립 — 표수·사전식 정렬·브리지 병합

`card_builder.build_cards`는 grounded=True 의심건만 scope별 버킷으로 클러스터링한다. **표수(votes)**는 `INTERNAL_PERSPECTIVES` 관점 고유 개수만 카운트하고(외부·동종은 참고 배지, 미가산), 카드에 "지적 4관점 중 N"으로 표시된다. `merge_bridge_cards`는 부모-자식 계정(GP→OP→세전 다단)을 한 카드로 흡수한다 — 같은 사건이기 때문이다.

정렬은 **사전식 비교**다(`card_order.py`) — ①표수 내림 ②금액 내림. 반박 판정은 정렬에 쓰지 않는다 — 병렬 관점이 독립적으로 합의한 표수를 후속 단일 에이전트의 판정이 뒤집는 통로였고, '정상우세' 하단 강등은 목록에서 사실상 안 보이게 만들어 silent drop과 구분이 어려웠다. High/Medium/Low 라벨이 먼저 폐지됐고(PLAN §5, 문제⑤ "분식은 기준선 아래 숨는다"와 충돌), 그 대체였던 **가중합 우선순위 점수(0.35·0.30·0.15·0.20)도 폐지**했다 — 성분별 가중치의 근거를 댈 수 없고("왜 금액이 표수보다 0.05 무거운가") 단위가 다른 값을 한 축에 합쳐 "왜 이 카드가 위인가"에 답하지 못하기 때문이다. 사전식은 각 단계가 그대로 설명이 된다("관점 3곳이 겹쳤고, 같은 표수 안에서 금액이 가장 크다"). **임계로 자르지 않는 것**은 그대로다. 폐지 과정에서 화면(가중합)과 마크다운 리포트(사전식)가 서로 다른 순서를 내던 불일치도 해소됐다 — 이제 화면·리포트·외부검증 대상 선정이 같은 함수를 쓴다. LLM이 매긴 위험도는 입력에서 제외한다(risk_level은 LLM 감 라벨이라 원칙 §3.1 위반 유일 지점이었다).

## 5.6 조사원 — 꼬리무는 도구 루프

발견은 넓게 갖췄으나 조사(깊게)와 판단(결론 주체)이 없다는 진단(2026-07-10)에서 조사원이 신설됐다. `investigator.run_investigation`은 결정론 게이트로 경로를 분기한다:

```
needs_tool_loop = 분해없음 OR 잔차>20% OR 최대 leaf 기여<60%
   → True:  도구 루프 (max 8왕복) — get_series·get_decomposition·find_notes·top_changes
   → False: 종합 1호출 (결론문만)
```

핵심은 **모든 카드가 결론을 받는다**는 것 — 코드가 이미 답을 낸 카드만 LLM 조사를 반복하지 않는 것(경로 차이지 배제가 아님)이다. 조사가 깊어지는 유입구는 도구 호출뿐이다 — "LLM 둘을 마주 앉혀도 새 사실은 안 생긴다(같은 입력의 재조합)"는 이유로 에이전트 토론은 미채택했다. 도구는 전부 순수함수라 "LLM은 이 반환값 밖 숫자를 못 만든다"(`investigation_tools.py`). 비용은 카드 스코프(3~8k 토큰)라 발견 관점(전 데이터 250k+)보다 훨씬 작다.

## 5.7 반박·외부검증 — 카드는 삭제하지 않는다

**반박**(`rebuttal.py`)은 카드+의심근거+분해+조사 결론을 받아 반대근거·정상설명·확인질문·다음절차·verdict를 채운다. 철칙 두 가지: **위험도 숫자 불변**(verdict 플래그만) · **카드 절대 제거 0**. 반박 없는 카드는 verdict=None("반박 미수행")으로 남긴다(§9 silent drop 금지). 정상우세(normal_dominant)로 판정돼도 카드는 삭제되지 않고 순서도 바뀌지 않는다 — 판정은 카드 표시로만 남고 정렬 키에는 들어가지 않는다.

**외부검증**(`external_verify.py`)은 카드 확정 후 상위 카드를 분해 결론 기반으로 타깃 검색한다. 대상 = 조사 미해결 카드 전부다(조사 실패·미수행도 미확인이라 포함). 조사로 원인이 설명된 카드는 순위와 무관하게 제외하며, `EXTERNAL_HARD_CAP=30`은 선정 기준이 아니라 폭주 방지 안전핀이다. 순서는 화면과 같은 사전식 정렬(`card_order`)을 쓴다. 외부 인용 금액을 내부 공시값과 대조(`check_figures`)해 match/mismatch(삭제 아니라 "공시와 상이" 마킹)/uncheckable로 판정하고, 못 찾아도 checked=True로 기록한다(빈손 은폐 금지).

## 5.8 실증 예시 — 대주산업 매출↔재고 관계가 관계 카드로 부활

대주산업(00112457) E2E에서, 과거에는 흐름(flow) 관점의 `related_accounts`가 카드에 전파되지 않아 계정 쌍 관계가 단일 계정 카드로 붕괴했다(진단 시 소실).

근본 수리는 SuspicionItem.scope에 "relationship"이라는 세 번째 단위를 신설한 것이다(`test_relationship_cards`). flow 관점이 재고↔매출원가↔매출 관계를 제출하면, `card_builder`가 이를 `rel:` 접두의 별도 관계 카드로 산출한다. cluster_key는 정렬 canonical(`rel:CFS:매출|CFS:매출원가|CFS:재고자산`)이라 A↔B == B↔A로 vote가 합산되고, 교차재무제표(CFS↔OFS)도 특수 분기 없이 동일 규칙(`rel:CFS:현금|OFS:현금`)을 따른다. grounding은 모든 다리가 실존해야 grounded=True를 주고, 유령 계정 상대는 drop한다(가짜 다리 날조 차단). 대주 실 LLM E2E에서 flow 6/6이 전부 scope=relationship으로, 연결↔별도 현금 관계가 부활했다(`_E2E_FLOW_REL_00112457.json`). 이 관계 카드가 최종 화면에서 "↔" 표기의 관계 섹션으로 렌더된다(7장).
