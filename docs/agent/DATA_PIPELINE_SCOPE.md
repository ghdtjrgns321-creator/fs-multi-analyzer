# DATA_PIPELINE_SCOPE — 데이터 출입(포함/제외) 전 단계 명세

> 목적: DART가 주는 것 중 **무엇을 가져오고·무엇을 빼는지**, 단계마다 그 이유를 한곳에 기록한다.
> 단일 출처(현재 상태). 초기 삼성 스파이크 관찰은 [DATA_CONTRACT.md](DATA_CONTRACT.md)(역사 기록).
> 갱신: 수집·정규화·분류·적재 스키마 변경 시. 최종 갱신 2026-06-09.

## 0. 한눈에 — 데이터 흐름

```
OpenDART ──┬─ finstate_all (본문 5표) ─→ raw/finstate_all_{CFS,OFS}.csv ─┐
           └─ 사업보고서 XBRL zip ─────→ raw/financial_statement_xbrl.zip │
                                                                          ▼
                                          L1 정규화(canonical 428·dedup·통화)
                                            ├─→ DuckDB normalized_financials  (본문)
                                            └─→ DuckDB sce_equity_components   (SCE 2D)
                                          주석 분류(Arelle 추출 → 3분류 → 필터)
                                            └─→ DuckDB note_facts_classified   (주석)
                                                                          ▼
                                                              Phase2 LLM 교차검증 입력
```

회사연도별 격리 DB: `data/companies/{corp}/{year}/analysis.duckdb` (3개 테이블).

---

## 1. L0 수집 — DART가 주는 것 / 가져오는 것 / 빼는 것

### 본문 재무제표 (`finstate_all`, `src/collect/opendart.py`)

| 차원 | 가져옴 | 뺌 | 이유 |
|------|--------|-----|------|
| 보고서 종류 | **사업보고서**(`reprt_code="11011"`) | 반기·분기(11012/11013/11014) | 연간 단위 분석. **분기 분식 선행신호는 못 봄**(알고 가는 경계) |
| 재무제표 구분 | **연결(CFS)+별도(OFS)** 각각 | — | 둘 다 보존(fs_div 메타 주입, 응답엔 없음) |
| 표(sj_div) | **BS·IS·CIS·CF·SCE 5종 전부** | — | finstate_all 한 호출이 5표 통째 반환 → 표 단위 누락 없음 |
| 연도 | 수집 시점 파라미터 | API 한계 | **OpenDART finstate_all은 대략 2015년 이후만 제공** → 그 이전 분식은 API에 없음(우리 누락 아님) |
| 컬럼 | 18종(아래) | — | `account_id`·`account_nm`·`account_detail`·`thstrm/frmtrm/bfefrmtrm_amount`·`currency` 등 |

18컬럼: rcept_no, reprt_code, bsns_year, corp_code, sj_div, sj_nm, account_id, account_nm,
account_detail, thstrm_nm, thstrm_amount, frmtrm_nm, frmtrm_amount, bfefrmtrm_nm,
bfefrmtrm_amount, ord, currency, thstrm_add_amount. (`fs_div`는 응답에 없어 수집 context에서 주입.)

### 주석 (XBRL, `src/collect/notes_xbrl.py` — 구 HTML 웹스크랩 대체)

| 항목 | 내용 |
|------|------|
| 소스 | 사업보고서 **XBRL 원본 zip + Arelle** 전개(웹뷰어 singlnote 아님 — 소형사 빈응답 회피) |
| 보고서 탐색 | `find_annual_report` = year+1..+4 정정대응(분식사는 정정으로 수년 뒤·상폐 결측) |
| 추출 | 전체 fact를 `note_facts.tsv` 저장. **차원(qnameDims) 보존**(세그먼트·지역·자본구성·차입건별) |
| 컬럼(7) | concept·label_ko·label_en·period·unit·value·**dimensions**("축=멤버\|축=멤버") |

### 수집 결과(전수, 2026-06-08~09)

- 본문: 회사연도 raw 보유 약 5,120 (유니버스 1,668사).
- 주석: 분모 5,126 중 **ok 4,579·기수집 skip 35·보고서없음 239·XBRL없음 273**(=상폐·미상장·과거소형
  XBRL미제출, 빈PASS 아님). 저장 `note_facts.tsv` **4,614개**(= ok 4,579 + skip 35).
- 총 fact **9,786,311행**(약 978만, 빈껍데기 0).

---

## 2. L1 본문 정규화 (`src/normalize/pipeline.py`)

raw 18컬럼 → 12컬럼 long table. **계산 안 함, 분류만.**

출력 컬럼: corp_code·year·fs_div·sj_div·**canonical**·account_id·label·amount·prior_amount·
prior2_amount·mapping_status·currency.

### 포함/제외·변환

| 처리 | 내용 | 이유 |
|------|------|------|
| canonical 매핑 | account_id(표준ID) 우선 → label alias. **canonical 428종**(116→428, 이번 세션 확장) | 회사 간 비교 가능한 표준계정 |
| 미매핑 | **"기타 중요 계정"으로 게시(분석 제외 아님)** | 라벨·금액·표 그대로 보존, Phase2가 봄 |
| statement guard | 행의 sj_div ≠ canonical 정해진 statement면 매핑 무효화(기타로 강등). IS↔CIS만 호환 | CF 조정·SCE 변동행이 잔액/손익 칸으로 흡수되는 **이질 오매핑 차단** |
| dedup 2단계 | ① (account_id,label,year,fs_div,sj_div) ② (canonical,year,fs_div) | 같은 계정 1행 유지. **구성요소 합산 안 함** |
| 통화 보존 | `currency` 컬럼 유지 + 외화연도 가드(`exclude_foreign_currency_years`) | 두산밥캣 KRW→USD 전환 시 1,300배 가짜점프 차단(D-F) |

### 이번 세션 분류 확장(코드는 최신, 디스크 데이터는 재정규화 필요)

- canonical 116→428: D-A(≥50사 보편 223종, CF흐름·SCE변동·BS기타금융 등)·D-B(이질병합 차단)·
  D-C(비유동채권/채무)·D-F(통화).
- **stale 경고**: normalized_financials 4,771 중 최신(통화컬럼)=41·구버전=4,730 → **전수 재정규화 대기**.

---

## 3. SCE 2D (`src/normalize/sce.py`)

자본변동표는 (변동행 × 자본구성요소) 2차원 표. 메인 정규화가 붕괴시키는 구성요소 차원을 별도 보존.

- 테이블 `sce_equity_components`: 변동행(change_label·change_canonical) × 구성요소(component_raw·
  component_std·component_role) + 금액(당기·전기·전전기) + detail_path.
- role: leaf(실데이터)/subtotal(소계)/total(총계)/composite(미분리 합산)/marker(표마커).
- 적립금은 원명 보존(component_raw) + 표준 묶음(component_std) 둘 다.

---

## 4. 주석 분류·적재 (`src/normalize/notes_classify.py`, `src/collect/load_notes_classified.py`)

note_facts.tsv concept(namespace 없는 local name)을 **3분류** 후 **적재 필터** 적용.

### 3분류 (우선순위: 메타 → 흡수 → detail → 기타)

| 갈래 | 정의 | 표본 비율 |
|------|------|----------:|
| **메타** | meta_tokens 포함(표지·감사·연락처·거래소 등) | 14.3% |
| **흡수** | concept stem이 본문 canonical account_id와 일치(=본문 재게시) | 42.3% |
| **detail** | note_categories 토큰(28종, 우선순위순) 매칭 | 35.5% |
| **기타주석** | 위 어디에도 안 걸리는 회사 특화 | 7.9% |

28 카테고리(차입금조건·사채·특수관계자거래·충당부채·약정우발·재고·매출채권대손·매입채무·수익고객계약·
이자배당손익·금융상품·위험관리공시·리스·확정급여·이연법인세·법인세·파생위험회피·종속관계기업투자·
정부보조금·외화환산·손상·무형자산명세·유형자산명세·투자부동산·현금금융기관·자본적립금·주당이익·
주식기준보상). 우선 카테고리 10종(`note_high_priority`)은 Phase2 리스크 리뷰 우선. **전부 config 외부화**
([config/playbooks/note_mappings.yaml](../../config/playbooks/note_mappings.yaml), 구 account_notes 보존).

### 적재 범위 (DuckDB `note_facts_classified`) — 무엇을 넣고 빼나

| 갈래 | 적재 | 이유 |
|------|:----:|------|
| detail | ✅ | 주석 고유 가치(차입조건·특수관계자 등) |
| 기타주석 | ✅ | 회사 특화, 비용 0, Phase2 단서 가능 |
| **흡수 — 유차원** | ✅ | CFS/OFS 외 축(세그먼트·지역·차입건별·자본구성) 보유 = **본문에 없는 분해**. 지역별매출·차입처별·부문손익·특수관계자 등 분식 고가치 |
| **흡수 — 무차원** | ❌ | 연결/별도 총계만 = 본문 normalized_financials 완전 중복 |
| 메타 | ❌ | 분석가치 0 |

판정 근거(실측): 흡수 행의 64.5%는 무차원(중복), 35.5%는 유차원(고가치). 무차원흡수가 모호한 게 아니라
명백한 본문 중복이라 제외. **차원 라벨이 없으면 못 쓰므로 재추출로 보존**(아래 한계 참조).

### 적재 결과(전수, 2026-06-09)

- 4,614 회사연도 처리(loaded 4,605 + skip 9=기적재) → 전부 `note_facts_classified` 보유.
- 적재 **5,767,592행** = 전체 978만 fact의 **~59%**(detail 35.5 + 기타 7.9 + 유차원흡수 15.0).
- 제거 **~41%** = 메타 14.3 + 무차원흡수 27.3. 검증: 무차원흡수 누출 0·메타 0.
- 테이블 컬럼: concept·label_ko·period·unit·value·dimensions·bucket·category·corp_code·year.

---

## 5. 알려진 경계·미검증 (정직 기록)

| 항목 | 상태 |
|------|------|
| 반기·분기 보고서 | **제외**(연간 11011만). 분기 선행신호 못 봄 |
| 2015년 이전 | OpenDART finstate API 미제공 → 과거 분식 데이터 부재(우리 누락 아님) |
| 업종(금융·보험·건설) | 비금융(`XBR103`) 가정 다수 → 금융사 계정체계 오분류 가능성 **미검증** |
| 정정공시(restatement) 버전 | **🔴 문제 확인(2026-06-09 감사)**: 분식 5사 중 4사(두산·셀트리온·아스트·모델솔루션)의 분식연도가 **정정본**(rcept 신고일 FY+2~7). finstate_all이 정정신고분 반환 → 백테스트가 원본 분식 아닌 정정 흔적 탐지 가능. 원본 rcept 지정 수집 검토 필요 |
| 세그먼트 차원 활용 | note에 보존됐으나 본문 normalized엔 연결/별도 총계만(세그먼트 분해는 note 측) |
| EvidenceRef provenance | normalized 행이 원 raw 행 위치를 추적 안 함 → Phase2 grounding 위해 보강 필요 |
| 본문 재정규화 | 분류기 최신이나 디스크 데이터 99% 구버전 → 전수 재정규화 대기 |

상세 완성 점검 계획은 [PHASE1_INTEGRITY_PLAN.md](PHASE1_INTEGRITY_PLAN.md).
