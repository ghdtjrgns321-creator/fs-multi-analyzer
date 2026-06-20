# 작업: dedup 고신뢰 동의어 통합 — 소량 배치로 메커니즘 증명 (인코딩 안전)

## 1. 목표
- `_dedup_candidates.json`의 synonym 쌍 중 **고신뢰 소량 배치(≤15쌍)**만 canonical_accounts.yaml에서 통합(생존자에 흡수+중복키 삭제)해 충돌 소멸을 증명하고, 회귀 0을 확인한다.
- 성공 기준: ①통합한 쌍이 충돌 인벤토리에서 사라짐 ②백테스트 recall 5/6·known·SCE·IS/CF 검산 무회귀 ③F1 신호 dangling Layer A 0 ④mojibake 0. **벌크 650 전체 적용 아님 — 메커니즘 증명용 소량.**

## 2. 컨텍스트
- 읽을 파일(필수): `data/backtest/_dedup_candidates.json`(synonym/survivor), `config/canonical_accounts.yaml`(통합 대상 블록 구조), `src/normalize/config.py`(load_canonical_accounts·_by_alias/_by_id 빌드), `dev/active/synonym-dedup-onboarding-gate/synonym-dedup-onboarding-gate-plan.md`("yaml 흡수 방식")
- 배경: 두 canonical을 합치면 _by_id·_by_alias가 같은 account 가리켜 충돌 자체 미발화. 생존 canonical 블록에 중복본의 account_ids·aliases·**중복본 name(을 alias로)**를 흡수하고 중복본 키 블록 삭제.
- ★인코딩(CLAUDE.md §4): 11k줄 한글 yaml **전체 재작성·formatter·ruamel round-trip 금지**. Edit 도구로 **해당 블록만** 표적 수정.

## 3. 설계 (이대로)
1. `_dedup_candidates.json`에서 klass=='synonym' 쌍 로드. **고신뢰 ≤15쌍 선별**(엄격 기준):
   - 생존자(survivor)의 aliases·account_ids가 중복본을 명백히 포섭하거나, 차이가 영문약어/단어누락뿐이고 의미 동일이 자명한 것.
   - ★F1 안전: 중복본 canonical name이 `_f1_signal_dangling.py`가 추출하는 신호엔진 참조(코드·playbook)에 있으면 **그 쌍은 제외**(통합 시 신호 dangling 위험). 또는 중복본 name을 생존자 alias로 반드시 흡수.
2. 각 선별 쌍: 생존 canonical 블록의 `account_ids:`에 중복본 account_ids 추가(중복 제거), `aliases:`에 중복본 aliases + 중복본 name 추가, 그 후 **중복본 canonical 키 블록 전체 삭제**. Edit 블록 단위.
3. 통합 후: yaml 파싱 성공, canonical 수 = 이전 − 통합건수, mojibake 0.
4. 충돌 소멸 측정 + 회귀 검증.

설계-현장 불일치(예: 블록 경계 모호) 시 멈추고 STATUS: NEEDS_CONTEXT.

## 4. 단계 체크리스트 (순서 고정)
- [ ] Step 1: json·yaml·config.py·F1 스크립트 읽고 synonym 쌍·생존자·신호참조 인용 → 고신뢰 ≤15쌍 선별 목록(제외사유 포함)
- [ ] Step 2: yaml 통합 적용(Edit 블록 단위) → 증거: 적용 전후 canonical 수(`python -c "import yaml;print(len(yaml.safe_load(open('config/canonical_accounts.yaml',encoding='utf-8'))['canonical_accounts']))"`) + 통합 쌍 목록
- [ ] Step 3: 인코딩 검증 → 증거: yaml 파싱 성공 + mojibake 0 (`PYTHONPATH=. uv run python -c "print(open('config/canonical_accounts.yaml',encoding='utf-8').read().count(chr(0xFFFD)))"` = 0)
- [ ] Step 4: 충돌 소멸 측정 → 증거: `PYTHONPATH=. uv run python data/backtest/_dedup_candidates.py` 재실행 — 통합 쌍이 synonym에서 사라지고 건수 감소
- [ ] Step 5: F1 dangling → 증거: `PYTHONPATH=. uv run python data/backtest/_f1_signal_dangling.py` Layer A 0
- [ ] Step 6: 회귀(전수 재정규화 후) → 증거: `PYTHONPATH=. uv run python -m src.backtest.run_backtest`(recall 5/6) + `PYTHONPATH=. uv run python data/backtest/_is_cf_arithmetic.py`(악화 0) + `PYTHONPATH=. uv run python -m pytest tests/ -q`(green)

## 5. 금지 사항 (1건 위반 시 전체 실패)
- 벌크 적용 금지: synonym 650 전체 적용 금지. **고신뢰 ≤15쌍만**(증명용). narrower·mistag 쌍 절대 통합 금지.
- 인코딩: yaml 전체 재작성·Set-Content·Out-File·formatter·ruamel round-trip 금지. Edit 블록 단위 minimal diff만. mojibake 유발 시 즉시 롤백.
- 테스트 약화 금지. baseline 회귀 시 DONE 금지(롤백 후 BLOCKED 보고).
- 범위 밖 수정 금지: config/canonical_accounts.yaml 외 src/ 변경 금지(분석 스크립트 재실행만).
- 하드코딩: 통합 쌍은 json 데이터에서. 코드에 계정명 박지 말 것.

## 6. 최종 검증
- 충돌 소멸(Step 4): 통합 쌍 synonym에서 소멸, narrower/mistag 불변
- F1 Layer A 0(Step 5) · recall 5/6 · IS/CF 악화 0 · pytest green(Step 6) · mojibake 0(Step 3)
- 하나라도 미달이면 DONE 금지(롤백 후 BLOCKED/CONCERNS)

## 7. 완료 보고 양식
STATUS: DONE | DONE_WITH_CONCERNS | NEEDS_CONTEXT | BLOCKED
체크리스트: 항목별 [x]/[ ] + 증거 원문(명령+출력)
변경 파일: 경로 목록 + 통합한 쌍 목록(생존자←중복본)
최종 검증 결과: §6 명령별 출력 원문
미완·우회·우려: 정직하게 전부(없으면 "없음")
