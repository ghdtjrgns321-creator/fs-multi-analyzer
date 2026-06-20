# 금융 미매핑 "9건" 원인 규명 + 분해

> 2026-06-17. 자백정정: 앞서 "보험 canonical 9건 추가"라 뭉뚱그린 건 부정확. 실측 분류로
> 근본원인을 규명하고, 진짜 신규 추가가 필요한 것만 골라낸다. (대상: KB금융 00688996/2024 CFS)

## 근본원인 (1줄)

`AccountMapper._by_id`는 **id→canonical 1:1**(statement 무관 1개)이라, **같은 IFRS 개념 id가
여러 표(SCE 자본변동·CIS 포괄손익·CF 현금흐름)에 출현**하면, 등록된 표(statement) 밖에서 나온
행은 statement 불일치로 "기타 중요 계정"으로 강등된다.

## 9건 분류 (id를 COA에 대조)

| 라벨 | 행 표 | id 등록 canonical (statement) | 분류 |
|------|-------|------------------------------|------|
| 당기순이익 | CF | 당기순이익 (IS) | A1 statement-context |
| 보험계약관련손익 | CF | 보험손익 (CIS) | A1 |
| 외환차이 | CIS | 해외사업환산손익(SCE) **(SCE)** | A2 OCI-SCE등록 |
| FVOCI 채무상품손익 | CIS | …관련손익 **(SCE)** | A2 |
| 해외사업장순투자위험회피 | CIS | …평가손익 **(SCE)** | A2 |
| 현금흐름위험회피 | CIS | …파생평가손익 **(SCE)** | A2 |
| 보험계약자산순금융손익 | CIS | …순금융손익 **(SCE)** | A2 |
| 주식보상비용 | CF | 주식기준보상 **(SCE)** | A2(SCE)→CF |
| 재보험계약자산 | CF | (미등록) | **B 미등록** |

- **A(등록됐으나 statement 불일치) = 8건 / B(id 미등록) = 1건.** "9건 다 신규 추가"는 틀림.

## 지배원인 — OCI id가 SCE에만 등록됨

A2의 OCI 개념(외환차이·위험회피·FVOCI)은 **CIS statement canonical이 이미 COA에 존재**한다
(해외사업환산손익·현금흐름위험회피손익 등 CIS OCI canonical 65개). 그런데 해당 **IFRS id
(ifrs-full_OtherComprehensiveIncomeNetOfTax…)는 SCE canonical에만 등록**돼 있고 CIS canonical엔
미등록이다. 실측:

```
ifrs-full_…ExchangeDifferencesOnTranslation  등록 statement: ['SCE']  ← CIS 미등록
ifrs-full_…CashFlowHedges                     등록 statement: ['SCE']  ← CIS 미등록
```

즉 SCE 2D 작업(AGENDA_DD_SCE2D)에서 자본변동 구성요소로 이 id들을 SCE canonical에 등록하면서,
**포괄손익계산서(CIS) OCI 라인에서의 같은 id 출현이 등록처가 없어 강등**된다. CIS canonical은
있는데 id가 안 걸려 있는 **등록 누락**이지, canonical 부재가 아니다.

## 분해 — "진짜 추가 필요한 것"

| 갈래 | 건 | 진짜 필요한 것 | 비고 |
|------|----|---------------|------|
| **B 미등록** | 재보험계약자산 | **신규 canonical 1건**(CF, dart_AdjustmentsForDecreaseIncreaseInReinsuranceContractsHeldThatAreAssets) | IFRS17 재보험, COA에 없음 |
| **A2 OCI** | 외환차이·FVOCI·위험회피류 | canonical 신규 **불필요** — 기존 CIS OCI canonical에 **id 추가 등록**(또는 다중표 id 허용) | CIS canonical 이미 존재, id만 SCE 독점 |
| **A1 statement-context** | 당기순이익·주식보상(CF) | canonical 신규 **불필요** — CF 간접법 시작줄/조정. statement 처리 | 당기순이익은 IS canonical 있음 |

- **실제 신규 canonical 추가 = 재보험계약자산 ~1건.** 나머지 8건은 **id 등록 보강 / 다중표 처리**.
- A2(OCI)가 가장 일반적(어느 회사나 OCI 보유) → 효익 큼. 단 수정은 canonical 추가가 아니라
  CIS OCI canonical에 IFRS id를 추가하는 것(데이터, §3).

## 수정 (진행 상황)

1. **A2(지배) [완료, 78차]**: 다중표 id 매핑 `cross_statement_ids` 채택(근본·§3). canonical에
   `cross_statement_ids`(다른 표 출현 id) 선언 → 강등(기타) 행만 가산적 구제(`_rescue_cross_statement`),
   mapping_status='cross_statement_match'(투명). OCI 4종(외환차이·현금흐름위험회피·해외사업장순투자·
   FVOCI채무) CIS canonical에 등록. **KB 4건 기타→정확 CIS canonical**. 격리 diff로 기존 매핑 무변경
   증명(비-SCE 변화 정확히 4)·백테스트 5/6 불변·262 passed. **잔여: 보험계약자산순금융손익 cross 등록.**
2. **B [미착수]**: 재보험계약자산 canonical 1건 신규(CF, dart_Adjustments…ReinsuranceContractsHeld).
3. **A1 [미착수]**: CF 당기순이익/주식보상은 별도 statement 처리(범위·회귀 영향 별도 검토).

## 검증 (실데이터 3종 경로)

- 외환차이: id 등록 statement=['SCE'] → CIS 행 강등(A2 재현).
- 당기순이익: id→canonical 당기순이익(IS) → CF 행 강등(A1 재현).
- 재보험계약자산: id가 _by_id에 없음 → 라벨도 미매핑 → 기타(B 재현).
