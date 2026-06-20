# 작업: dedup 후보 자동 3분류 스크립트 (synonym / narrower / mistag)

## 1. 목표
- same-statement 충돌 canonical 쌍 592개를 synonym(통합 대상)·narrower(세분화 보존)·mistag(진짜오매핑)으로 자동 시드 분류하고, synonym 쌍의 생존 canonical을 규칙으로 제안하는 스크립트를 신설한다.
- 성공 기준: 스크립트 실행 시 3분류 건수 출력 + `_dedup_candidates.json` 산출. 핵심 케이스 자동분류 정확: 유동리스부채↔리스부채=narrower(통합금지), FVPL금융자산↔당기손익-공정가치측정금융자산=synonym, 영업이익↔매출=mistag.

## 2. 컨텍스트
- 읽어야 할 파일(필수): `data/backtest/_conflict_canonical_inventory.py`(same-statement 충돌 쌍 추출 방식·_conflict_pairs.json 구조), `dev/active/id-label-conflict-category-arbiter/_264_triage.md`(진짜충돌 9쌍 패턴·거짓양성 6경계패턴), `dev/active/id-label-conflict-category-arbiter/_conflict_pairs.json`(83 same-stmt-diff-cat 쌍)
- 배경: lexical·범주·영문id 유사도 3종 다 자동분류 실패 측정됨 → 이 스크립트는 **확정이 아니라 보수적 시드**(애매하면 사람검수 큐). 목적은 명백한 narrower(통합금지)·명백한 mistag(게이트행)을 걸러 사람 검수 부담을 줄이는 것.

## 3. 설계 (이대로 구현)
신규 `data/backtest/_dedup_candidates.py`:
- 입력: `_conflict_canonical_inventory.py`가 산출하는 same-statement 충돌 쌍 전체(592쌍). 그 스크립트 함수 재사용 또는 corpus 재수집(동일 방식).
- 각 쌍 (canon_a, canon_b)에 자동 분류:
  - **narrower(통합 금지)**: 한 name이 다른 것의 부분문자열이고, 차이가 {유동,비유동,단기,장기,순,총,비} 접두/수식어뿐 → 세분화. (예: 유동리스부채⊃리스부채). 보수적: 조금이라도 세분화 의심이면 narrower.
  - **mistag(진짜오매핑 후보→게이트행)**: `_264_triage.md` 진짜충돌 9쌍 패턴(수익↔이익소계 등 cross-category) 또는 두 core 명사가 완전히 다른 실물(투자부동산↔금융상품, 사채↔주식)이면 mistag. 단 확신 없으면 synonym 큐로(보수).
  - **synonym(통합 후보, 사람검수 큐)**: 위 둘 다 아닌 나머지.
- 생존자 선정 규칙(synonym 쌍에만, 결정론): ①account_ids 많은 쪽 ②동수면 ifrs-full_ 보유 쪽 ③그래도 동수면 수식어 적은(짧고 일반적인) name. 제안값 출력.
- 산출: `_dedup_candidates.json` = [{a, b, klass, survivor, reason}]. + 콘솔에 klass별 건수.

## 4. 단계 체크리스트 (순서 고정)
- [ ] Step 1: _conflict_canonical_inventory.py·_264_triage.md·_conflict_pairs.json 읽고 쌍 추출·진짜충돌 패턴 인용
- [ ] Step 2: `_dedup_candidates.py` 작성 → 증거: 핵심 함수(분류·생존자) 전문
- [ ] Step 3: 실행 → 증거: `PYTHONPATH=. uv run python data/backtest/_dedup_candidates.py` 출력(synonym/narrower/mistag 건수)
- [ ] Step 4(마지막): 자기검증 — 핵심 케이스 3개 분류 확인
      증거: 유동리스부채↔리스부채=narrower / FVPL↔당기손익-공정가치측정=synonym / 영업이익↔매출=mistag 임을 json에서 인용

## 5. 금지 사항
- 하드코딩: 특정 corp_code·연도를 분기에 박지 말 것. corpus는 _holistic_chunks.json, 패턴은 일반 규칙.
- src/·config/ 수정 금지(분석 스크립트·json 산출만). 읽기만.
- 결과 fabricate 금지: 실제 corpus/충돌 데이터 출력만. 빈 결과 임의 채우지 말 것.
- 애매한 쌍을 mistag/synonym으로 과확신 분류 금지 — 애매하면 synonym 큐(사람검수). narrower는 명백할 때만(통합 금지 안전).

## 6. 최종 검증
- `PYTHONPATH=. uv run python data/backtest/_dedup_candidates.py` → 기대: 592쌍 3분류 건수 출력, json 산출
- 핵심 케이스 3개 분류 정확(Step 4)

## 7. 완료 보고 양식
STATUS: DONE | DONE_WITH_CONCERNS | NEEDS_CONTEXT | BLOCKED
체크리스트: 항목별 [x]/[ ] + 증거 원문
변경 파일: 경로 목록
최종 검증 결과: §6 출력 원문
미완·우회·우려: 정직하게(없으면 "없음")
