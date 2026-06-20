# 핸드오프 — E2E 충실도 감사 (DART 원본 통독 ↔ Phase1이 LLM에 넘기는 것)

> 2026-06-15. **컴팩트 후 이 파일부터 읽고 실행.** 작업 디렉터리:
> C:\Users\ghdtj\workspace\portfolio\fs-multi-analyzer.

## 과제 (사용자 정의)

1. 샘플 회사를 **최종본 PHASE1 파이프라인**에 태운다(수집→정규화→신호→material).
2. 내가(Claude Opus) **DART에서 받은 정보를 아주 세세하게 전수 통독**한다(재무제표·주석·사업보고서
   원문 12파트·event·정정).
3. 그것을 **Phase1이 LLM(Phase2 6관점)에 넘기는 material과 비교**한다.
4. 목적 = **충실도/누락 감사**: DART가 주는 유용정보 중 Phase1이 LLM에 넘기기 전에 **빠뜨리거나
   왜곡하는 것**을 찾는다. (분식 탐지 아님 — 정보 전달 충실도.)

## 결정: 6개 회사 (랜덤 아닌 층화 — 차원별 1사)

깊은 전수 통독은 회사당 고비용(원본 ~100K+ 토큰). **랜덤 10보다 구조 다양 6**이 충실도 갭을
빨리 드러낸다. 파이프라인의 서로 다른 스트레스 경로를 하나씩 친다:

| # | 스트레스 차원 | 무엇을 검증 | 선정 기준 |
|---|---------------|-------------|-----------|
| 1 | 대형 다각화(주석·종속기업 多) | 주석·원문·연결범위 추출 충실도 | review_queue·ratio 큰 정상 대형사 |
| 2 | 소형 단순 | 공통 케이스 기본 충실도 | 단일~소수 연도·작은 큐 |
| 3 | 금융/지주(계정체계 상이) | 정규화·매핑(업종 특수계정) | 금융업/지주 |
| 4 | 정정본 보유(재작성) | S9 정정 이력·원본/정정본 플래그 | `list`에 [기재정정]사업보고서 과거연도 |
| 5 | 자본거래 多(CB/유증/합병) | S10 event 타임라인·원문 narrative | event 비어있지않은 유형 3+ |
| 6 | 구포맷(2017 이전, 11파트) | S7 시대 매핑(PART 추출) | 옛 연도 사업보고서 |

(원하면 +공통케이스 2~4사로 10까지 확장 가능 — 단 위 6이 갭 발견 핵심.)

## 실행 절차 (회사마다)

1. **최종 PHASE1 태우기**: `collect_company_years(corp, years, include_notes=True,
   include_corrections=True, include_events=True)` → 정규화(필요시 `--force`) → `build_company_report`
   + 4 material(numeric/note/flow/change) + S7 review_chunks + S9 restated + S10 routed_timeline.
2. **DART 원본 전수 통독(나)**: 재무제표(`finstate_all`)·주석(raw/notes)·원문(`document` 12파트)·
   event(`events.json`)·정정(`corrections.json`)을 직접 Read로 깊게 통독.
3. **비교**: 원본에 있는데 material엔 없는 것 / 왜곡된 것 / 압축으로 소실된 신호를 표로.

## 비교축 (무엇을 대조하나)

- 재무 라인: 원본 계정 ↔ 정규화 canonical(미매핑·오매핑·소실).
- 주석: 원본 주석 카테고리 ↔ note_material note_sections(누락 카테고리).
- 원문 narrative: 12파트 검토관심(우발·소송·대주주·연결범위) ↔ S7 review_chunks(놓친 청크).
- event/정정: DART event·정정 ↔ S10 timeline·S9 flag(누락).
- 수준/추세: 원본 급변·이상 ↔ review_queue·ratio(못 띄운 후보).

## 산출

- 회사별 **충실도 매트릭스**(원본 차원 × Phase1 전달 여부 × 갭 사유) → `_E2E_AUDIT_RESULTS.md`.
- 종합: Phase1이 구조적으로 빠뜨리는 정보 차원(예: 주석 미수집·원문 청크 누락·event 미라우팅) 목록.
- 발견된 갭은 수정 백로그로.

## 주의 (포지셔닝·규율)

- 분식 잡기가 목적 아님 — **정보 전달 충실도**. 정상 회사로 한다.
- hollow-PASS 금지: "material 있음"이 아니라 **원본 대비 무엇이 빠졌나**를 본다.
- 6사 각각 전수 통독(표본 1~2개로 일반화 금지). 차원별 갭은 그 차원 회사에서 확인.

## 현재 상태(컴팩트 직전)

- PHASE1 S0~S11 종료(`PHASE1_EXIT_GATE.md`). S7~S10 모듈·배선 완료, 단 **기존 corpus엔 주석·event·
  정정 미수집** → E2E 회사는 `include_notes/corrections/events=True`로 **새로 수집**해야 채워진다.
- persist ~30% stale → E2E 회사는 정규화 `--force` 권장.
- 참조: `_S10_ANALYSIS.md`·`_S9_SCALE_COST.md`·`_S8_*`·`_s7_sample/`.
