# DATA_CONTRACT — L0 OpenDART Raw 관찰 기록

> 목적: L1 정규화 설계 전에 OpenDART 실제 응답 구조를 기록한다.
> 범위: 삼성전자(`corp_code=00126380`) 2022~2024 사업보고서, 연결(CFS)·별도(OFS).
> 생성일: 2026-06-01.

---

## 1. 수집 범위와 저장 위치

수집 모듈은 [src/collect](../../src/collect)를 사용한다. 이번 단계는 raw 저장까지만 수행하며,
정규화·신호엔진·에이전트·LLM 호출은 수행하지 않았다.

| 항목 | 값 |
|------|----|
| 대상 회사 | 삼성전자 |
| corp_code | `00126380` |
| 사업연도 | 2022, 2023, 2024 |
| 보고서 | 사업보고서 (`reprt_code=11011`) |
| 재무제표 | 단일회사 전체 재무제표 API, `CFS`/`OFS` 각각 수집 |
| 주석 | OpenDART 재무제표 주요 주석 조회 HTML, `CFS`/`OFS` 각각 수집 |
| 원본 XBRL | 사업보고서 접수번호 기준 `fnlttXbrl.xml` zip 저장 |

Raw 저장 경로:

```text
data/companies/00126380/
├── collection_summary.json
├── 2022/raw/
├── 2023/raw/
└── 2024/raw/
```

각 연도 raw 디렉터리:

```text
raw/
├── collection_summary.json
├── finstate_all_CFS.csv
├── finstate_all_CFS.json
├── finstate_all_OFS.csv
├── finstate_all_OFS.json
├── financial_statement_xbrl.zip
└── notes/
    ├── note_categories.json
    ├── CFS/{note_code}.html
    ├── CFS/{note_code}.txt
    ├── OFS/{note_code}.html
    └── OFS/{note_code}.txt
```

---

## 2. 재무제표 API 실제 컬럼

`finstate_all` 응답은 `pandas.DataFrame`으로 수신했다. 실제 컬럼은 2022~2024 CFS/OFS 모두
동일했다.

```text
rcept_no
reprt_code
bsns_year
corp_code
sj_div
sj_nm
account_id
account_nm
account_detail
thstrm_nm
thstrm_amount
frmtrm_nm
frmtrm_amount
bfefrmtrm_nm
bfefrmtrm_amount
ord
currency
thstrm_add_amount
```

관찰:

- `fs_div` 컬럼은 응답에 포함되지 않는다. 연결/별도 구분은 요청 파라미터(`CFS`, `OFS`)와
  저장 파일명으로 보존해야 한다.
- `sj_div`는 재무제표 종류를 나타낸다. 관찰값은 `BS`, `IS`, `CIS`, `CF`, `SCE`다.
- `account_nm`은 한글 라벨이며 회사별 표시 라벨 그대로 들어온다.
- 금액 컬럼은 문자열로 들어온다. 쉼표는 없고 원 단위 숫자 문자열 또는 음수 문자열이다.

---

## 3. 규모

| 연도 | 구분 | 전체 행 | 고유 계정 라벨 | BS | IS | CIS | CF | SCE |
|------|------|--------:|---------------:|---:|---:|----:|---:|----:|
| 2022 | CFS | 185 | 127 | 53 | 18 | 13 | 41 | 60 |
| 2022 | OFS | 114 | 97  | 44 | 15 | 7  | 29 | 19 |
| 2023 | CFS | 176 | 122 | 52 | 18 | 13 | 39 | 54 |
| 2023 | OFS | 115 | 96  | 44 | 15 | 7  | 30 | 19 |
| 2024 | CFS | 213 | 121 | 52 | 17 | 13 | 40 | 91 |
| 2024 | OFS | 131 | 96  | 44 | 14 | 7  | 31 | 35 |

3개년 CFS/OFS 전체에서 관찰된 고유 계정 라벨은 165개다.

---

## 4. 계정 라벨 실제 예시

아래는 3개년 CFS/OFS에서 처음 관찰된 순서 기준 예시다. 정규화 전에는 이 값을 코드에
하드코딩하지 않는다.

```text
유동자산
현금및현금성자산
단기금융상품
단기상각후원가금융자산
단기당기손익-공정가치금융자산
매출채권
미수금
선급비용
재고자산
기타유동자산
매각예정분류자산
비유동자산
기타포괄손익-공정가치금융자산
당기손익-공정가치금융자산
관계기업 및 공동기업 투자
유형자산
무형자산
순확정급여자산
이연법인세자산
기타비유동자산
자산총계
유동부채
매입채무
단기차입금
미지급금
선수금
예수금
미지급비용
당기법인세부채
유동성장기부채
```

---

## 5. 연결(CFS) / 별도(OFS) 구분

OpenDartReader의 `finstate_all(corp, year, reprt_code="11011", fs_div=...)`를 CFS와 OFS로
각각 호출했다.

관찰:

- 응답 행 자체에는 `fs_div` 컬럼이 없다.
- `rcept_no`, `reprt_code`, `bsns_year`, `corp_code`는 CFS/OFS 모두 동일하게 들어온다.
- `sj_div`와 계정 라벨만으로 연결/별도를 역추론하면 안 된다.
- L1 raw schema에는 반드시 `fs_div`를 수집 메타데이터로 추가해야 한다.

---

## 6. 표준 계정 외 회사 확장계정 관찰

`finstate_all`의 `account_id`에는 `ifrs-full_*`, `dart_*` 같은 표준 계정 ID와
`-표준계정코드 미사용-` 값이 함께 나타났다.

| 연도 | 구분 | 표준계정코드 미사용 행 | 고유 라벨 수 | 예시 |
|------|------|----------------------:|-------------:|------|
| 2022 | CFS | 51 | 42 | 단기상각후원가금융자산, 미수금, 선급비용, 매각예정분류자산 |
| 2022 | OFS | 24 | 22 | 선급비용, 매입채무, 미지급금, 금융비용 |
| 2023 | CFS | 8  | 6  | 단기차입금, 매각예정분류, 비지배지분의 증감 |
| 2023 | OFS | 2  | 2  | 단기차입금, 단기금융상품의 순감소(증가) |
| 2024 | CFS | 7  | 7  | 단기차입금, 사채 및 장기차입금의 상환, 매각예정분류 |
| 2024 | OFS | 3  | 3  | 단기차입금, 사채 및 장기차입금의 상환, 단기금융상품의 순감소(증가) |

원본 XBRL zip 내부에는 `entity00126380_*` 네임스페이스 파일과 회사별 taxonomy 파일이 있다.
따라서 L1에서는 다음을 구분해야 한다.

- API 표면에서 표준계정코드가 없는 행
- XBRL taxonomy 내부의 회사별 확장 concept
- 한글 라벨은 같지만 `account_id`가 다르거나 누락된 행

미매핑 행은 분석 제외하지 않고 `unmapped_extension_account` 또는 별도 raw issue로 올려야 한다.

---

## 7. 원본 XBRL zip 구조

사업보고서 접수번호를 찾아 `financial_statement_xbrl.zip`으로 저장했다.

| 연도 | 접수번호 | zip 내부 파일 수 | 관찰 |
|------|----------|----------------:|------|
| 2022 | `20230307000542` | 8 | `.xbrl`, entry point `.xsd`, dimensions, labels |
| 2023 | `20240312000736` | 7 | `entity00126380_2023-12-31.*` 파일 세트 |
| 2024 | `20250311001085` | 7 | `entity00126380_2024-12-31.*` 파일 세트 |

2024 zip 예시:

```text
entity00126380_2024-12-31.xbrl
entity00126380_2024-12-31.xsd
entity00126380_2024-12-31_def.xml
entity00126380_2024-12-31_cal.xml
entity00126380_2024-12-31_pre.xml
entity00126380_2024-12-31_lab-ko.xml
entity00126380_2024-12-31_lab-en.xml
```

---

## 8. 주석 데이터 실제 형태

OpenDartReader 0.2.3은 주석 조회 API를 래핑하지 않는다. 이번 스파이크에서는 OpenDART
`재무제표 주요 주석 조회` 화면의 public HTML endpoint를 사용해 raw HTML과 HTML에서 추출한
텍스트를 저장했다.

OpenDART 화면 기준 주석 카테고리는 비금융업(`XBR103`)에서 8개가 관찰됐다.

| 코드 | 이름 | 설명 |
|------|------|------|
| D82210 | 유형자산 | Property, plant and equipment |
| D82242 | 매출채권 및 기타채권 | Sales credit and other credit |
| D82240 | 차입금 | Borrowings |
| D82245 | 사채 | Bonds |
| D82757 | 충당부채 | Provisional liability |
| D82638 | 재고자산 | Inventory asset |
| D83800 | 주당이익 | Profit per share |
| D86120 | 자본금, 적립금, 기타지분 | Issued capital, reserves, other equity |

각 연도마다 CFS 8개, OFS 8개 주석 상세를 저장했다. 연도별 HTML/TXT 파일은 각 16개다.

주석 상세 HTML 관찰:

- 하나의 상세 페이지가 표와 문장영역을 함께 포함한다.
- `table`이 포함되어 숫자 표를 구성하고, 동시에 `문장영역` 텍스트도 포함한다.
- 추출 텍스트에는 기간, 구성요소, 항목, 표 행/열 값이 줄 단위로 섞여 들어온다.
- 섹션 구분은 가능하다. 예: `[D822420] 7. 매출채권 및 미수금`, `연체되거나 손상된 금융자산에 대한 공시 [개요][ 문장영역 ]`.
- L1.5에서는 HTML 구조를 보존한 parser가 필요하다. 단순 텍스트 split만으로는 표의 행/열 의미가 손실된다.

2024 CFS `D82242` 텍스트 일부:

```text
[D822420] 7. 매출채권 및 미수금
매출채권 및 기타채권 [개요]
금융자산의 공시 [개요]
2024-01-01 ~ 2024-12-31
2023-01-01 ~ 2023-12-31
2022-01-01 ~ 2022-12-31
연결재무제표 [구성요소]
금융자산의 공시 [항목]
매출채권
43,650,714,000,000
36,671,282,000,000
유동매출채권
43,623,073,000,000
36,647,393,000,000
35,721,563,000,000
```

---

## 9. L1 정규화 설계 입력

다음 단계에서 확정해야 할 raw contract:

1. `fs_div`는 API 응답 컬럼이 아니라 수집 context에서 주입한다.
2. `sj_div`는 `BS`, `IS`, `CIS`, `CF`, `SCE` enum으로 검증한다.
3. `account_id == "-표준계정코드 미사용-"` 행은 별도 mapping status로 분리한다.
4. 주석은 HTML과 TXT를 모두 보존한다. TXT는 검색·관찰용, HTML은 표 구조 복원용이다.
5. 주석 category code와 한글명은 `note_categories.json`에서 관리한다.
6. 원본 XBRL zip은 L1 정규화/Arelle 스파이크 입력으로 보존한다.

---

## 10. 참고한 OpenDART 화면

- OpenDART `단일회사 전체 재무제표` API는 [PLAN.md §9](PLAN.md#9-데이터-소스-opendart)의 수치 입력이다.
- OpenDART 공시정보 활용마당은 재무정보조회가 XBRL 재무제표를 출처로 한다고 안내한다.
- OpenDART `주석 일괄다운로드` 화면은 XBRL 주석사항을 탭 구분값 파일(`.tsv`)로 제공한다고 안내한다.
- 이번 스파이크는 대용량 일괄 zip 다운로드 대신 `재무제표 주요 주석 조회` 상세 HTML을 회사·연도·주석 코드별로 raw 저장했다.
