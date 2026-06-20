# 작업: 수집 부재 사유 manifest 기록 + 하니스 갭 표기 구분

> 수집 레이어 점검 회차(2026-06-12) 결론에 따른 단건 개선. **수집 버그는 0건으로 확정** —
> 남은 것은 "부재의 사유를 기록하지 않아 미제공과 수집누락을 구분 못 하는 관측 공백"이다.
>
> **【사용자 확정 정책 2026-06-12 — 본 작업과 후속 전 단계에 적용】**
> ①물리 삭제 금지(회사·연도 디렉터리·raw 보존) ②"수집 FAIL"이 아니라 **"원천 미제공(사유)"**
> 로 표기 ③회사별 "분석 가능 연도" 명시, 전 연도 미제공 회사만 분석 모집단에서 자동 제외하되
> 목록엔 유지 ④UI/리포트 단계(L4/L5)에서 미제공 연도를 사유 배지로 표시 ⑤커버리지 수치 공개.
> 사람용 정리: [docs/user/DATA_SCOPE.md §5](../../docs/user/DATA_SCOPE.md). 이 정책과 어긋나는
> 구현(삭제·숨김·FAIL 표기)은 §5 위반으로 작업 실패다.

## 1. 목표

- 원천 부재를 사유와 함께 기록(absence manifest)하고, 하니스가 "미제공(고정)"과
  "수집 필요(재시도 대상)"를 구분 표시하게 한다.
- 성공 기준: §6 검증 명령 3개 전부 기대 출력 일치.

## 2. 컨텍스트 (점검 회차에서 확정된 사실 — 재조사 불필요)

- 전수 측정: 본문 원천 부재 347건(2020:121 → 2024:11 점감), zip(주석) 부재 163건.
- DART API 직접 대조로 원인 3분류 확정:
  - **미제출**: 사업보고서 자체 없음(예: 01584183/2020 — 신규상장 전). list() 빈 응답.
  - **본문 미제공**: 사업보고서 있으나 finstate_all status 013(예: 00117267/2020·00158909/2020
    — 금융업 구 양식, 2023부터 제공). rows 0.
  - **zip 미제공**: finstate_xml ValueError(status 013/014)(예: 00127158/2023 — 재수집
    시도로 실증, no_zip=1). 본문은 정상 수집됨.
- 현 동작: `collection_summary.json`에 rows:0·xbrl_zip:null은 남지만 **사유가 없고**,
  00127158/2023처럼 zip 실패 경로에선 summary 자체가 안 남는 경우도 있다.
- 읽어야 할 파일: `src/collect/opendart.py`(annual_report·save_xbrl_zip),
  `src/collect/collect_notes_all.py`, `src/collect/storage.py`(summary 기록부),
  `data/backtest/_p1_review_all.py` machine_checks·`_p1_company_review.py` §0.

## 3. 설계 (이대로 구현 — 임의 변경 금지)

- summary에 부재 사유 필드 추가: `absence: {"fs": "no_report|dart_no_data|ok", "xbrl_zip":
  "no_report|dart_no_xbrl|ok"}` — 수집 시점에 list()/finstate_all/finstate_xml 결과로 판정해
  기록. 기존 summary 스키마는 보존(필드 추가만).
- zip 실패 경로에서도 summary가 반드시 남도록(부분 실패 ≠ 기록 생략).
- 하니스: `machine_checks`가 DB 없을 때 summary의 absence를 읽어
  `FAIL(DB없음)` → `미제공(no_report)`/`미제공(dart_no_data)`/`FAIL(DB없음·사유미상)`으로
  구분 표기. 주석 MISSING도 동일하게 `미제공(dart_no_xbrl)` 구분. **사유미상만 FAIL로 남긴다**
  (재수집 대상 신호).
- 과거 분 backfill: 별도 일회성 스크립트(`data/backtest/_backfill_absence.py`)로 기존
  347+163건의 summary에 absence를 채움 — DART API 호출 최소화를 위해 "rows:0 기록이 이미
  있으면 API 재호출 없이 dart_no_data로 추정 기록, 사유미상은 API 확인" 전략. 호출량이
  과하면 STATUS: NEEDS_CONTEXT로 중간 보고.
- 설계와 현장이 안 맞으면 **STATUS: NEEDS_CONTEXT** — 멈춤은 실패가 아니다.

## 4. 단계 체크리스트 (순서 고정)

- [ ] Step 1: RED — summary absence 기록 테스트 + machine_checks 구분 표기 테스트.
      증거: `uv run python -m pytest tests/ -q -k "absence or gap"` 출력에 failed 포함
- [ ] Step 2: 수집 레이어 구현(absence 기록 + zip 실패 시 summary 보장) → GREEN.
      증거: 같은 명령 failed 0
- [ ] Step 3: backfill 실행(기지 갭 전수). 증거: 스크립트 출력(건수 합계 = 본문347·zip163과 대조)
- [ ] Step 4: 하니스 표기 반영. 증거: round5 배치 출력에서 00158909 2020~2022가
      `미제공` 표기(FAIL 아님)로 나오는 행 원문
- [ ] Step 5(마지막): §6 전체 검증.
※ 단계 증거 원문 필수. 증거 없는 단계 = 미수행.

## 5. 금지 사항

- 하드코딩: corp_code·연도 리터럴로 absence를 분기 금지(전부 summary 데이터 기반).
- 기존 raw·DB 파일 수정/삭제 금지(기록 추가만). 테스트 약화 금지.
- 수정 가능: `src/collect/*`, `data/backtest/_p1_review_all.py`·`_p1_company_review.py`
  (§0·machine_checks 표기 한정), `tests/`, backfill 스크립트 신규.
  **건드리면 실패**: `src/normalize/`·`src/signals/`, 정답지·표본 json.
- 체크리스트 생략 금지. 실패·미완을 완료로 보고 금지.

## 6. 최종 검증

- round1~6 배치 6경로 → 기대: 기존 FAIL(DB없음)·주석 MISSING 행이 전부 `미제공(...)` 구분
  표기로 전환, **사유미상 FAIL 0건**, 그 외 행 무회귀(소실 0·검산 OK 동일)
- known 배치 → 기대: 전수 PASS 유지
- `uv run python -m pytest tests/ -q` → 기대: 전체 passed

## 7. 완료 보고 양식

```
STATUS: DONE | DONE_WITH_CONCERNS | NEEDS_CONTEXT | BLOCKED
체크리스트: Step 1~5 [x]/[ ] + 각 단계 증거 원문
변경 파일: <실제 변경분만>
최종 검증 결과: §6 명령별 출력 원문
미완·우회·우려 사항: <정직하게. 없으면 "없음">
```
