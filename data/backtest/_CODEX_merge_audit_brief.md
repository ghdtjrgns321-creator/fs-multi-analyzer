# Codex 의뢰서 — canonical 이질계정 병합 전수 감사

## 목적
서로 다른 경제적 실질의 계정이 같은 canonical 한 칸으로 매핑되어, 정규화 중복제거에서
한 계정이 통째로 버려지거나(소실) 다른 계정 값으로 덮이는(오염) 케이스를 **수집된 전
회사·전 재무제표에서 빠짐없이** 찾는다. 표본 점검이 아니라 전수 감사다.

## 배경 (코드 사실)
- L1 매핑: `src/normalize/mapper.py` `AccountMapper.map_row` — account_id(IFRS 표준ID) 1순위,
  label alias 2순위.
- 중복제거: `src/normalize/pipeline.py` `_dedupe_canonical_rows` — `(canonical, year, fs_div)`
  당 **1행만 keep, 합산하지 않음**. keep 우선순위는 `_canonical_score`(sj_div==canonical_statement
  6점 > exact 4점 > label==canonical 3점 > 그외 2점), 동점 시 `abs(amount)` 큰 행.
  → **중복제거 키에 sj_div가 없다.** 그래서 재무상태표 잔액과 현금흐름표 조정이 같은 canonical이면
  서로를 덮을 수 있다.
- canonical 정의: `config/canonical_accounts.yaml`.

## 이미 발견·처리한 것 (재발견 말고, 누락분을 찾아라)
- (수정완료) 종속기업투자가 관계기업투자에 병합 → 별도 canonical로 분리함.
- (표본서 발견, 미수정) A: 매출채권·매입채무가 "○○ 및 기타채권/채무" 통합 라벨 흡수(BS 동점→큰 값이
  순수계정 덮음). B: 재고/매출채권/매입채무의 현금흐름표 증감조정이 BS 잔액과 같은 canonical(sj_div
  키 부재). C: 충당부채가 유동/비유동 혼재(라벨 "충당부채"가 유동 칸 흡수).
- 위 A/B/C 외에 **다른 canonical에서 같은 유형 오류가 더 있는지**가 이번 조사 대상이다.

## 필수 요건
1. **전수**: `data/companies/` 아래 **전 회사(현재 1668사)·전 연도·CFS+OFS·BS·IS·CIS·CF·SCE**.
   표본·상위N 샘플링 금지. 불가피한 축소는 결과 md에 `[~]사유`로 명시(조용한 다운스코프 금지).
2. **운영코드 재현**: `AccountMapper`, `_canonical_score`, `_dedupe_canonical_rows`를 **실제로 호출**해
   무엇이 keep되고 무엇이 drop되는지 정확히 계측한다. 별도 재구현·추정 금지.
3. **자기참조 금지(§10)**: 이질 여부는 현재 canonical/alias가 아니라 **account_id의 IFRS 표준명 자체**의
   회계 실질로 판정한다. 도구(현 매핑)로 사각을 재면 사각은 영원히 안 보인다.
4. **동질 제외 기준(가짜 경보 — 이질 아님)**:
   - prefix 차이: `ifrs-full_` vs `ifrs_` vs `dart_` vs "-표준계정코드 미사용-"(account_id 공백)
   - 세전/세후: `...BeforeTax` vs `...NetOfTax`
   - 같은 계정의 표문 변형: `...ForStatementOfCashFlows`, `...ForStatementOfChangesInEquity`,
     `ProfitLoss` 가 BS·CF·SCE에 반복
   - 의도된 유동+비유동 통합 canonical(예: 리스부채 generic) — 단 별도 canonical이 따로 있는데도
     흡수되면 이질로 본다(충당부채↔장기충당부채 사례).
5. **진짜 이질 판정 기준**: 서로 다른 실질 — (a) 잔액 vs 현금흐름 조정, (b) 순수계정 vs 기타포함 통합,
   (c) 유동 vs 별도 존재하는 비유동계정, (d) 지배(종속) vs 유의적영향(관계), (e) 자산 vs 부채/손익 등
   재무제표 성격 자체가 다른 것.

## 산출물
1. **이질병합표** (canonical 단위):
   `canonical | 동시출현 (회사,연도,fs) 그룹수 | drop된 금액 합·최대 | keep된 account_id | drop된
   account_id | 실데이터 예시(회사·연도·금액) | 심각도`.
   - 심각도: BS↔BS(실질 소실, 상) / BS↔다른표문(잔액 우선보존, 중) / 동질의심(하).
2. **신규 발견 강조**: 위 A/B/C·종속관계 외에 새로 나온 canonical을 별도 절에.
3. 재현 하니스 스크립트(`data/backtest/`)와 결과 `data/backtest/MERGE_AUDIT.md` 저장.
   참고 시작점: `data/backtest/_audit_merge.py`(표본 27사·노이즈 미분리 버전. 이를 전수·노이즈제거로 확장).

## 완료 기준 (done)
- 돌린 회사 수·연도 수·그룹 수를 **수치로 명시**(전수 증명). "1668사 중 N사 데이터 보유, 전부 검사" 형태.
- 이질병합 각 항목에 실데이터 금액 예시 1건 이상(hollow 금지).
- "이질 없음" 결론을 내는 canonical은 **검사한 그룹 수(분모)와 동질 사유**를 함께 적는다(빈 PASS 금지).

## 금지
- 표본으로 전수 갈음, 상위N 절단, 조용한 범위 축소.
- 도구 출력 무비판 수용 — 동질/이질 판정 근거를 account_id 표준명으로 제시할 것.
- 한글 파일 인코딩 깨짐(mojibake) — 최소 편집, diff 확인.
