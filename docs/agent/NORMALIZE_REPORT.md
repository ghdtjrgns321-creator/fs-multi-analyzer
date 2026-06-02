# NORMALIZE_REPORT — L1 정규화 스파이크 결과

> 범위: 삼성전자(`00126380`) 2022~2025 사업보고서, CFS/OFS 재무제표 raw.
> 목적: `account_id` 1순위 canonical 매핑 가설을 수치로 검증한다.

## 1. 구현 범위

- 입력: `data/companies/00126380/{year}/raw/finstate_all_{CFS|OFS}.csv`
- 출력: `data/companies/00126380/{year}/analysis.duckdb`
- 테이블: `normalized_financials`
- L1 long format:
  - `corp_code`, `year`, `fs_div`, `sj_div`
  - `canonical`, `account_id`, `label`, `amount`, `mapping_status`

이번 단계에서는 정규화까지만 수행했다. LLM, 신호엔진, 에이전트, 주석 인덱싱(L1.5)은
호출하지 않았다.

## 2. Raw Schema 고정

- `fs_div`: API 응답에는 없으므로 파일/수집 context에서 `CFS` 또는 `OFS`를 주입한다.
- `sj_div`: `BS`, `IS`, `CIS`, `CF`, `SCE` enum으로 검증한다.
- `amount`: `thstrm_amount` 문자열을 숫자로 캐스팅한다.
  - 쉼표 제거
  - `None`, 빈 문자열, `-`, `nan`은 결측 처리
  - 비교·집계 전 `settings.amount_round_digits` 기준으로 반올림

## 3. 매핑 규칙

`config/canonical_accounts.yaml`은 MVP1 10개 계정을 `account_id` 1순위 스키마로 관리한다.

1. `account_id`가 `account_ids`에 있으면 `exact_taxonomy_match`
2. 표준 ID로 매칭되지 않고 한글 라벨이 `aliases`에 있으면 `label_alias_match`
3. 둘 다 아니면 `canonical = 기타 중요 계정`, `unmapped_extension_account`

미매핑 행은 제외하지 않고 보존한다.

## 4. Mapping Status 분포

| 연도 | 구분 | mapping_status | 행 수 | 비율 |
|------|------|----------------|------:|-----:|
| 2022 | CFS | exact_taxonomy_match | 9 | 4.86% |
| 2022 | CFS | label_alias_match | 1 | 0.54% |
| 2022 | CFS | unmapped_extension_account | 175 | 94.59% |
| 2022 | OFS | exact_taxonomy_match | 9 | 7.89% |
| 2022 | OFS | label_alias_match | 1 | 0.88% |
| 2022 | OFS | unmapped_extension_account | 104 | 91.23% |
| 2023 | CFS | exact_taxonomy_match | 9 | 5.11% |
| 2023 | CFS | label_alias_match | 1 | 0.57% |
| 2023 | CFS | unmapped_extension_account | 166 | 94.32% |
| 2023 | OFS | exact_taxonomy_match | 9 | 7.83% |
| 2023 | OFS | label_alias_match | 1 | 0.87% |
| 2023 | OFS | unmapped_extension_account | 105 | 91.30% |
| 2024 | CFS | exact_taxonomy_match | 9 | 4.23% |
| 2024 | CFS | label_alias_match | 1 | 0.47% |
| 2024 | CFS | unmapped_extension_account | 203 | 95.31% |
| 2024 | OFS | exact_taxonomy_match | 9 | 6.87% |
| 2024 | OFS | label_alias_match | 1 | 0.76% |
| 2024 | OFS | unmapped_extension_account | 121 | 92.37% |

해석:

- 전체 raw 행 기준 미매핑 비율은 높다. 이번 config가 MVP1 10개 계정만 대상으로 하므로
  정상적인 결과다.
- 각 연도·구분마다 MVP1 10개 중 9개는 `account_id`로 직접 매칭됐고, 1개는 라벨 alias가
  필요했다.

## 5. 2022 CFS 표준계정코드 미사용 행 구제율

| 대상 | 값 |
|------|---:|
| 2022 CFS `-표준계정코드 미사용-` 행 | 51 |
| 라벨 alias로 구제된 행 | 1 |
| 구제율 | 1.96% |

구제된 MVP1 계정은 `매입채무`다. 나머지 50행은 이번 MVP1 범위 밖이므로
`unmapped_extension_account`로 보존됐다.

## 6. MVP1 연도 간 정합성

값은 해당 canonical이 연도·CFS/OFS별로 연결된 행 수다.

| canonical | 2022 CFS | 2022 OFS | 2023 CFS | 2023 OFS | 2024 CFS | 2024 OFS |
|-----------|---------:|---------:|---------:|---------:|---------:|---------:|
| 현금및현금성자산 | 1 | 1 | 1 | 1 | 1 | 1 |
| 단기금융상품 | 1 | 1 | 1 | 1 | 1 | 1 |
| 매출채권 | 1 | 1 | 1 | 1 | 1 | 1 |
| 재고자산 | 1 | 1 | 1 | 1 | 1 | 1 |
| 유동부채 | 1 | 1 | 1 | 1 | 1 | 1 |
| 매입채무 | 1 | 1 | 1 | 1 | 1 | 1 |
| 단기차입금 | 1 | 1 | 1 | 1 | 1 | 1 |
| 매출 | 1 | 1 | 1 | 1 | 1 | 1 |
| 매출원가 | 1 | 1 | 1 | 1 | 1 | 1 |
| 영업활동현금흐름 | 1 | 1 | 1 | 1 | 1 | 1 |

결론: MVP1 10개 계정은 3개년 CFS/OFS 전부 같은 canonical로 연결됐다.

## 7. Label Alias가 필수였던 사례

| 연도 | 구분 | sj_div | canonical | label | account_id |
|------|------|--------|-----------|-------|------------|
| 2022 | CFS | BS | 매입채무 | 매입채무 | `-표준계정코드 미사용-` |
| 2022 | OFS | BS | 매입채무 | 매입채무 | `-표준계정코드 미사용-` |
| 2023 | CFS | BS | 단기차입금 | 단기차입금 | `-표준계정코드 미사용-` |
| 2023 | OFS | BS | 단기차입금 | 단기차입금 | `-표준계정코드 미사용-` |
| 2024 | CFS | BS | 단기차입금 | 단기차입금 | `-표준계정코드 미사용-` |
| 2024 | OFS | BS | 단기차입금 | 단기차입금 | `-표준계정코드 미사용-` |

## 8. 판단

`account_id` 1순위 전략은 MVP1 연결성에는 충분했다. 다만 `account_id`만으로는 6개
행이 누락되므로 라벨 alias 보조는 필수다. Arelle/원본 XBRL taxonomy 파싱은 아직 투입하지
않아도 MVP1 L2 입력을 만들 수 있다.

## 9. 2025 포함 최신 매핑 점검

2025 수집 후 `canonical_accounts.yaml`의 기본 합계 계정까지 포함한 최신 매핑 상태를
재점검했다. MVP 계정은 2022~2025 CFS/OFS 전 구간에서 모두 1건씩 매핑됐다.

| 연도 | 구분 | exact_taxonomy_match | label_alias_match | unmapped_extension_account |
|---|---|---:|---:|---:|
| 2022 | CFS | 28 | 3 | 154 |
| 2022 | OFS | 23 | 3 | 88 |
| 2023 | CFS | 29 | 1 | 146 |
| 2023 | OFS | 25 | 1 | 89 |
| 2024 | CFS | 32 | 1 | 180 |
| 2024 | OFS | 28 | 1 | 102 |
| 2025 | CFS | 32 | 1 | 196 |
| 2025 | OFS | 28 | 1 | 112 |

2025에서 label alias가 필요한 MVP 계정은 CFS/OFS 모두 `단기차입금`이다.
`account_id == "-표준계정코드 미사용-"`이지만 라벨 보조로 매핑됐다.
