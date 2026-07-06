---
name: pandera-validation
description: "Pandera DataFrameSchema validation for audit GL/TB/IC data. Use when defining schemas, validating ledger structure, separating L1/L2/L3 layers, or mapping chart-of-accounts. Triggers: pandera, DataFrameSchema, validate, L1/L2/L3, COA, opening_balance, closing_balance. 감사 데이터 스키마 검증 시 활성화."
---

# Pandera Validation (감사 데이터)

## 원칙

감사 데이터(GL, TB, IC) 검증은 **3계층 분리**가 핵심이다. 하나의 거대한 schema에 모든 룰을 넣지 않는다.

| 계층 | 책임 | 실패 시 의미 |
|------|------|-------------|
| **L1 구조** | 컬럼 존재, 타입, NotNull, 값 도메인 | 데이터 적재 자체가 불가 |
| **L2 회계** | 차/대 균형, 계정 매핑, 기간 정합 | 회계 룰 위반 — 원장 신뢰 불가 |
| **L3 통계** | 분포 이상치, 거래 빈도 정상 범위 | 패턴 이상 — 탐지 후보 |

L1 통과 없이 L2 검증 금지. L2 통과 없이 L3 검증 금지.

## 트리거 조건

- `pandera.DataFrameSchema` 작성/수정
- `validate()` 호출
- chart-of-accounts(COA) 매핑 추가
- `opening_balance`, `closing_balance` 컬럼 정의
- GL → TB 집계 로직 작성

## 3계층 패턴 (예시)

```python
import pandera.pandas as pa

L1_GL_SCHEMA = pa.DataFrameSchema({
    "doc_no":       pa.Column(str, nullable=False),
    "account_code": pa.Column(str, nullable=False),
    "debit":        pa.Column(float, checks=pa.Check.ge(0)),
    "credit":       pa.Column(float, checks=pa.Check.ge(0)),
    "post_date":    pa.Column("datetime64[ns]", nullable=False),
})

L2_GL_SCHEMA = L1_GL_SCHEMA.add_columns({}).set_checks([
    pa.Check(lambda df: (df["debit"] * df["credit"] == 0).all(),
             error="한 행에 debit/credit 둘 다 nonzero — 분개 위반"),
    pa.Check(lambda df: df.groupby("doc_no")[["debit","credit"]].sum().diff(axis=1).iloc[:,1].abs().lt(0.01).all(),
             error="전표 단위 차/대 불균형"),
])
```

L3는 별도 모듈에서 분포 검증만 담당. 매핑은 YAML/config 외부화.

## Don't do (도메인 함정)

### 1. 계정 코드 하드코딩 금지

회계과목코드는 회사·연도·법인격에 따라 다르다. 스키마/룰 안에 `"1101"`, `"매출"` 같은 리터럴을 박지 않는다.

```python
# Bad
if row["account_code"] == "1101":  # 현금 — 어느 회사 기준?
    ...

# Good
COA = load_yaml("config/coa_mapping.yaml")
if row["account_code"] in COA["cash_accounts"]:
    ...
```

**실전 사고 (audit 프로젝트 누적)**:
- 사고: 회사마다 다른 계정과목 코드 (A사 1150, B사 1153, C사 AR-IC). 코드에 상수로 박으면 클라이언트 바뀔 때마다 재배포 필요한 기술 부채.
- 패턴: YAML → Pydantic(타입 검증) → Python(실행) 흐름 미적용.
- 해결: 매핑 관계가 있는 설정은 flat list 가 아닌 구조화된 YAML로 설계. 적용 사례: `intercompany.pairs` (receivable ↔ payable 쌍 구조).

### 2. `closing_balance` 의미 명확화

`closing_balance` 단어는 두 의미가 충돌한다:
- **당기 순증감액** (period delta) — GL → TB 집계 결과
- **누적 잔액** (running balance) — opening + delta

같은 컬럼명으로 두 의미를 섞으면 dashboard KPI에서 부호·단위 사고 발생.

**규칙**: 스키마에는 `period_delta` (순증감) 와 `running_balance` (누적) 를 별 컬럼으로 분리. UI 라벨에도 한국어 명시 ("당기 증감" vs "기말 잔액"). `closing_balance` 단일 컬럼을 굳이 써야 하면 docstring/주석에 어느 의미인지 1줄 명시.

**실전 사고 (audit 프로젝트 누적)**:
- 사고: GL 원본에 이월 기초전표(Opening Entry) 부재 → 집계된 TB 의 `opening_balance` 가 항상 0. `closing_balance` 는 실제 기말잔액이 아닌 "당기 순증감액(Net Change)".
- 패턴: GL-TB 무결성 검증은 통과하지만, 대시보드에서 감사인이 "기말 잔액" 으로 오해 가능.
- 해결: 대시보드 라벨 "기말 잔액" 대신 "당기 발생액(집계)" 사용. 코드 주석에도 명시.

### 3. opening_balance 누락 검증

기초 잔액이 None/0 인 채로 GL 적재되면 누적 계산이 모두 틀어진다. L2 검증에 다음을 포함:

```python
pa.Check(lambda df: df.groupby(["company","fiscal_year","account_code"])
                      ["opening_balance"].first().notna().all(),
         error="opening_balance 누락 — 전기 마감 미반영 의심")
```

## Anti-pattern → Fix

| Bad | Why | Fix |
|-----|-----|-----|
| 단일 schema에 L1+L2+L3 30개 check | 한 check 실패가 다른 검증 차단 | 3 schema 분리, 순차 적용 |
| `dtype=int` for 금액 | 통화 단위/소수 손실 | `float` + `accounting-precision` 룰 |
| account_code 정규식으로 분류 | COA 변경 시 누락 | YAML 매핑 + `ripple-search` 스킬 |

## 적용 위치 (local-ai-assist 기준)

- `config/settings.py` — schema 상수
- `dashboard/components/_redetect.py` — TB 재집계 시 L1+L2 적용
- 탐지 룰 모듈 — L1 통과한 GL만 입력으로 수용
