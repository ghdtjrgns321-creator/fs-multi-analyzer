# 작업: company_quirks 인프라 (스키마 + 로더 + 적용 pass)

## 1. 목표
- 회사 고유 이탈을 코드가 아니라 데이터로 교정하는 `config/company_quirks.yaml` + 로더 + 정규화 적용 pass를 신설한다.
- 성공 기준: ①quirk 없는 회사는 정규화 결과 무변경(기존 전체 테스트 무회귀) ②예시 quirk(account_override·alias_addition)가 해당 회사연도에만 적용됨을 단위검증으로 확인.

## 2. 컨텍스트
- 읽어야 할 파일(수정 전 필수): `src/normalize/config.py`(`load_canonical_accounts` 로더 패턴·`CanonicalAccount`), `src/normalize/pipeline.py`(`normalize_company_year`·`normalize_raw_file`·`_arbitrate_conflicts` 호출 위치·corp_code/year가 어디서 흐르는지), `config/canonical_accounts.yaml`(yaml 구조 참고)
- 설계 출처: `dev/active/synonym-dedup-onboarding-gate/synonym-dedup-onboarding-gate-plan.md` "company quirk config 스키마"·"_apply_company_quirks"
- 배경: 측정상 within-category 진짜오매핑(투자부동산↔단기금융상품)은 mechanical 분리 불가 → 회사별 교정(quirk)으로 흡수. corp_code는 **데이터 키**(코드 분기 하드코딩 절대 금지).

## 3. 설계 (이대로 구현 — 임의 변경 금지)
### 3-1. config/company_quirks.yaml (신설)
```yaml
# 회사 고유 정규화 이탈 교정(데이터). corp_code/year는 데이터 키(코드 분기 아님).
# 3개+ 회사 반복 시 canonical_accounts.yaml로 승격하고 여기서 제거(quirk=임시·예외).
company_quirks: {}
# 예시(주석 — 실제 1건은 활성화해 단위검증):
#   "00545716":
#     "2021":
#       alias_additions:
#         - {canonical: 매출, alias: 영업수익}
#       account_overrides:
#         - {account_id: dart_OperatingIncomeLoss, label: 영업수익, force_canonical: 매출, reason: "렌탈사 영업수익을 영업이익 id로 오태깅"}
```

### 3-2. src/normalize/config.py — load_company_quirks
- `load_company_quirks(path=None) -> dict`: company_quirks.yaml → `{corp: {year: {"alias_additions":[...], "account_overrides":[...]}}}`. 파일 미존재·빈 파일 → 빈 dict(안전). 기존 로더 패턴 준수.

### 3-3. src/normalize/pipeline.py — _apply_company_quirks
- `_apply_company_quirks(frame, corp_code, year, quirks)`: corp_code/year에 매칭되는 quirk 적용.
  - `account_overrides`: (account_id, label) 매칭 행의 canonical을 force_canonical로 덮고 mapping_status에 흔적(예: `company_quirk:override`).
  - `alias_additions`: 해당 회사연도에서 label이 alias와 맞으면 canonical로 매핑(또는 매핑 후처리에서 흡수).
  - 매칭 quirk 없으면 frame 무변경.
- 호출 위치: **corp_code/year를 아는 지점**에서 `_arbitrate_conflicts` 다음. normalize_raw_file에 corp/year가 없으면 normalize_company_year에서 호출(읽고 적절한 지점 선택). corp_code/year는 **인자로 전달**(전역·하드코딩 금지).

설계가 현장과 안 맞으면(예: corp/year가 정규화 흐름에 없음) 멈추고 STATUS: NEEDS_CONTEXT.

## 4. 단계 체크리스트 (순서 고정)
- [ ] Step 1: config.py·pipeline.py 읽고 로더 패턴·corp/year 흐름·_arbitrate 호출 위치 인용
- [ ] Step 2: company_quirks.yaml 신설(빈 스키마+주석 예시) → 증거: 파일 내용 + `python -c "import yaml;yaml.safe_load(open('config/company_quirks.yaml',encoding='utf-8'))"` 파싱 성공
- [ ] Step 3: load_company_quirks 추가 → 증거: `git diff src/normalize/config.py`
- [ ] Step 4: _apply_company_quirks 추가 + 호출 연결(corp/year 인자) → 증거: `git diff src/normalize/pipeline.py`
- [ ] Step 5: 단위검증 — 예시 quirk 1건(00545716/2021 영업수익→매출) 활성화해 적용 확인 + quirk 없는 회사 무변경 확인
      증거: 작성한 검증 스니펫 + 출력(override 적용된 canonical / 무관 회사 불변)
- [ ] Step 6(마지막): 전체 무회귀 → 증거: `PYTHONPATH=. uv run python -m pytest tests/ -q` 출력(passed 수)

## 5. 금지 사항 (1건 위반 시 전체 실패)
- 하드코딩: corp_code·연도·계정명을 코드 분기(if corp=="..." 등)에 박지 말 것. 전부 quirk 데이터에서.
- 테스트 약화 금지(skip/xfail/assert삭제).
- 범위 밖 수정 금지: config/company_quirks.yaml·src/normalize/config.py·src/normalize/pipeline.py 외 변경 금지. canonical_accounts.yaml·mapper.py·_arbitrate_conflicts 로직 손대지 말 것.
- 단위검증 후 예시 quirk는 주석 처리로 되돌려 company_quirks: {} 빈 상태 유지(검증만 하고 실데이터 비움).

## 6. 최종 검증
- `PYTHONPATH=. uv run python -m pytest tests/ -q` → 기대: 기존 baseline 동일 passed(회귀 0)
- Step 5 → 기대: 예시 override 적용됨, quirk 없는 회사 무변경

## 7. 완료 보고 양식
STATUS: DONE | DONE_WITH_CONCERNS | NEEDS_CONTEXT | BLOCKED
체크리스트: 항목별 [x]/[ ] + 증거 원문(명령+출력)
변경 파일: 경로 목록(변경한 것만)
최종 검증 결과: §6 출력 원문
미완·우회·우려: 정직하게(없으면 "없음")
