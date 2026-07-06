---
name: accounting-precision
description: "Float precision and rounding rules for audit calculations. Use when comparing amounts against materiality threshold, rounding monetary values, mixed-currency aggregation, or handling tax-exempt/zero-rated transactions. Triggers: materiality, float64, round, decimal, 금액 비교, 부가세, tax_amount, 면세, 영세율. 금액 정밀도 처리 시 활성화."
---

# Accounting Precision (금액 정밀도)

## 원칙

float64 누적 연산은 항상 오차를 만든다. **금액 비교는 round 후 진행**, 부가세 계산은 **거래 유형별 분기**, 통화 혼합 시 **group 단위 정규화**.

## 트리거 조건

- materiality threshold 와 금액 비교
- pandas `Series.round()` 호출
- 통화 컬럼이 둘 이상인 데이터 처리
- 부가세 (`vat`, `tax_amount`) 검증
- 면세 / 영세율 거래 분류

## 핵심 룰 3개

### 1. Materiality 비교 전 `round(value, 2)` 필수

```python
# Bad
if abs(actual - expected) > materiality:
    flag_as_misstatement(...)

# Good — float 누적 오차 방어
if round(abs(actual - expected), 2) > round(materiality, 2):
    flag_as_misstatement(...)
```

**이유**: `0.1 + 0.2 != 0.3`. GL 수천 행을 합산한 뒤 materiality(예: 100만원)와 비교할 때 0.0000001 단위 오차로 boundary 케이스가 false positive 가 된다.

자릿수 선택: 원화 정수 단위면 `round(_, 0)`, 외화·소수단위면 `round(_, 2)`. 회사 회계 정책에 맞춰 정한 뒤 모듈 상수로 노출.

**실전 사고 (audit 프로젝트 누적)**:
- 사고: 수십만 건 float64 `sum()` 후 뺄셈 시 이진법 변환 한계로 `0.00000000000014` 같은 잔차 불가피.
- 패턴: `materiality=0` 상황에서 `is_within_materiality=False` 오탐 유발.
- 해결: difference 계산 또는 materiality 비교 **직전** 에 반드시 `round(value, 2)` (또는 회계 시스템 최소 단위) 반올림.

### 2. `Series.round()` 는 단일 int decimal만 받는다

pandas `Series.round(decimals)` 는 decimals 가 스칼라(int). 행마다 다른 자릿수가 필요하면(원화 0자리 / USD 2자리) **groupby + transform** 패턴.

```python
# Bad — 행별 decimals 불가
df["amount_rounded"] = df["amount"].round(df["currency"].map(DECIMALS))

# Good
def _round_group(s: pd.Series) -> pd.Series:
    currency = s.name  # group key
    return s.round(DECIMALS[currency])

df["amount_rounded"] = (
    df.groupby("currency")["amount"]
      .transform(_round_group)
)
```

대안: `Decimal` 객체로 정확 산술. 다만 성능 비용 큼 — 통화 혼합이 빈번한 데이터에만 적용.

**실전 사고 (audit 프로젝트 누적)**:
- 사고: 혼합 통화(KRW + USD) DataFrame 에서 통화별 자릿수 다르게 적용하려 `df["amount"].round(df["currency"].map(DECIMALS))` 시도 → TypeError. `Series.round(decimals)` 의 `decimals` 는 int 만 허용, Series 인자 불가.
- 패턴: 직관적으로 map 후 round 에 Series 넣으면 에러.
- 해결: `df.groupby("currency")["amount"].transform(_check_round)` 패턴. for loop 보다 성능 우수, pandas 네이티브 벡터화 유지.

### 3. 면세/영세율 거래는 VAT 검증에서 제외

VAT 검증 룰 (예: `tax_amount / supply_amount ≈ 0.10`) 을 모든 행에 적용하면 면세·영세율 거래가 100% false positive.

```python
# 면세: tax_amount = 0 또는 NaN, supply_amount > 0, account 면세 분류
# 영세율: tax_rate = 0.0, 명시적 영세 코드

EXEMPT_MASK = (
    df["tax_amount"].fillna(0).eq(0)
    | df["tax_code"].isin(EXEMPT_TAX_CODES)
)

vat_check_target = df.loc[~EXEMPT_MASK]
ratio = vat_check_target["tax_amount"] / vat_check_target["supply_amount"]
violations = vat_check_target[(ratio - 0.10).abs() > 0.001]
```

**확장**: 수출(영세율 0), 의료·교육(면세), 간이과세 별도 처리. tax_code 매핑은 YAML 외부화 (`pandera-validation` 스킬의 COA 패턴과 동일).

**실전 사고 (audit 프로젝트 누적)**:
- 사고: 부가세 검증 룰 `tax_amount ≠ round(supply_amount × 0.1)` 을 모든 행에 적용 → 도서/농산물(면세), 수출(영세율) 거래가 전부 False Positive.
- 패턴: 회계 장부에는 과세(10%) 외 면세(0%)·영세율(0%) 거래가 상당수 존재. `tax_amount=0` 이 정상값.
- 해결: 부가세 검증 서브룰 적용 전 마스크 `(tax_amount.notna()) & (tax_amount > 0)` 인 행만 대상으로. tax_amount 가 0 또는 NaN 인 행은 S2 에서 완전 제외.

## Anti-pattern → Fix

```python
# Bad — float 직접 비교, materiality 누락
diff = sum_a - sum_b
if diff > 0:                      # 0.0000003 도 통과 → false positive
    raise ValueError("불일치")

# Good
if round(abs(diff), 2) > round(MATERIALITY, 2):
    raise ValueError(f"불일치 {diff:,.2f} > materiality {MATERIALITY:,.2f}")
```

## 적용 위치 (local-ai-assist 기준)

- `dashboard/_kpi.py` — materiality 카드 계산
- `dashboard/components/_redetect.py` — 재집계 시 round 적용
- 탐지 룰 중 금액 임계 사용 모듈 (예: 거액 거래, materiality 미달 누적)

## 관련 스킬

- `pandera-validation` — 스키마 단위 dtype/통화 검증
- `ripple-search` — DECIMALS / 면세 코드 변경 시 파급 영향 검색
