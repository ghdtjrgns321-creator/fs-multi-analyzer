# 작업: canonical config에 category 차원 추가 (Phase 2 스키마만)

## 1. 목표
- `CanonicalAccount`에 `category: str = ""` 필드를 추가하고 `load_canonical_accounts`가 yaml의 `category` 키를 로드한다.
- 성공 기준: `uv run pytest tests/test_normalize.py -v` 가 기존과 동일하게 통과(무회귀), 그리고 category 키가 있는 canonical 로드 시 필드에 값이 들어가고 없으면 빈 문자열.

## 2. 컨텍스트
- 읽어야 할 파일: `src/normalize/config.py` (수정 전 반드시 읽기 — `CanonicalAccount` dataclass와 `load_canonical_accounts` 함수)
- 배경: 이 필드는 후속 단계(충돌 중재)가 쓸 메타데이터다. 이번 작업은 **스키마 추가만** — 실제 category 값 기입(yaml)이나 중재 로직은 범위 밖.
- 기본값 `""`(빈 문자)는 "범주 미부여 → 중재 시 id 유지 폴백"을 의미한다. 절대 None이 아니라 빈 문자열.

## 3. 설계 (이대로 구현 — 임의 변경 금지)
- `CanonicalAccount` dataclass에 필드 1개 추가: `category: str = ""` (기존 필드 순서 유지, 맨 뒤 또는 is_subtotal 옆 — 기본값 있는 필드는 기본값 없는 필드 뒤에 와야 함).
- `load_canonical_accounts`에서 각 canonical 생성 시 `category=values.get("category", "")` 전달.
- 그 외 로직·시그니처 변경 금지. 설계가 현장과 안 맞으면 멈추고 STATUS: NEEDS_CONTEXT.

## 4. 단계 체크리스트 (순서 고정)
- [ ] Step 1: `src/normalize/config.py` 읽고 `CanonicalAccount`·`load_canonical_accounts` 구조 파악
      증거: dataclass 필드 목록과 load 함수의 CanonicalAccount(...) 생성부 인용
- [ ] Step 2: `category: str = ""` 필드 추가 → 산출물: config.py diff
      증거: `git diff src/normalize/config.py` 출력
- [ ] Step 3: load 함수에 `category=values.get("category","")` 추가 → 산출물: config.py diff
      증거: 동 diff에 포함
- [ ] Step 4: 무회귀 검증 → 증거: `uv run pytest tests/test_normalize.py -v` 출력 원문(passed 수)
- [ ] Step 5(마지막): category 로드 동작 확인
      증거: `PYTHONPATH=. uv run python -c "from src.normalize.config import load_canonical_accounts; from config.settings import settings; a=load_canonical_accounts(settings.config_dir/'canonical_accounts.yaml'); print('has category field:', hasattr(a[0],'category')); print('sample:', a[0].category)"` 출력

## 5. 금지 사항 (1건이라도 위반 시 작업 전체 실패)
- 하드코딩: 특정 canonical 이름·category 값을 코드에 박지 말 것(이번엔 값 기입 안 함, 스키마만).
- yaml 파일(`config/canonical_accounts.yaml`) 수정 금지(이번 작업은 코드 스키마만 — yaml은 다음 단계).
- 테스트 약화 금지(skip/xfail/assert 삭제).
- 범위 밖 수정 금지: `src/normalize/config.py` 외 파일 변경 금지.
- 한글 인코딩: config.py에 한글 없으면 무관하나, 편집은 minimal diff.

## 6. 최종 검증 (완료 선언 전 필수)
- `uv run pytest tests/test_normalize.py -v` → 기대: 기존과 동일 passed(회귀 0)
- Step 5 명령 → 기대: `has category field: True`

## 7. 완료 보고 양식
STATUS: DONE | DONE_WITH_CONCERNS | NEEDS_CONTEXT | BLOCKED
체크리스트: 항목별 [x]/[ ] + 증거 원문
변경 파일: 경로 목록(변경한 것만)
최종 검증 결과: §6 명령별 출력 원문
미완·우회·우려: 정직하게(없으면 "없음")
