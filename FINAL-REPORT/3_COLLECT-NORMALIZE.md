# 3. L0 수집 · L1 정규화 · 온보딩 게이트 (계산 레이어)

> **위치**: `[L0 수집] → [L1 정규화] → [온보딩 게이트]` → L2 신호엔진. 이 세 레이어에는 **LLM 호출이 전혀 없다** — 전부 결정론 코드(수집·매핑·검산). LLM은 게이트의 별칭 제안(코드가 좁힌 후보 안에서만)에서만 관여한다 — G6 통독은 LLM 입력 dump 생성까지 구현돼 있고 실제 호출은 R4 예정이다.

## 3.1 내부 흐름

```
raw OpenDART               L1 정규화                      온보딩 게이트
finstate JSON     ──→   validate(Pandera)          ──→   G1 완결성 + BS 항등식(tol 100만원)
주석 XBRL zip           map_row (id-first)                G3 산술검산 + G5 신호 무결성
사업보고서 XML          _arbitrate_conflicts               통화 KRW 검사(_currency_ok)
                       _rescue_cross_statement            G6 dump(LLM 통독 입력)
                       _dedupe (소실 대신 강등 보존)          │
                       _enforce_capital_decomposition       │ FAIL → 별칭 3단 분업
                       SCE 2D 별도(sce_balance)             │      코드 후보→LLM 선택→고신뢰 자동 등록(보류분만 사람 확인)
                            │                              │      quirk 재게이트
                            ▼                              ▼
                  회사/연도 격리 DuckDB              gate_passed → L2 진입
```

## 3.2 구조

| 구성요소           | 개수                                                                       | 출처 파일                          |
| ------------------ | -------------------------------------------------------------------------- | ---------------------------------- |
| L0 수집 모듈       | 12                                                                         | `src/collect/`                     |
| L1 정규화 모듈     | 12                                                                         | `src/normalize/`                   |
| canonical 표준계정 | 약 2,015 (5표: BS/IS/CIS/CF/SCE)                                           | `config/canonical_accounts.yaml`   |
| 매핑 상태 코드     | 6 (EXACT·ALIAS·UNMAPPED·ID_LABEL_CONFLICT·OTHER_CANONICAL·CROSS_STATEMENT) | `src/normalize/mapper.py:11-18`    |
| 온보딩 게이트      | G1·G2·G3·G5·G6 + 통화                                                      | `src/normalize/onboarding_gate.py` |
| 회계 항등식        | 3 (BS-BALANCE·ROLLFORWARD·CF-RECON)                                        | `config/playbooks/identities.yaml` |

## 3.3 L0 수집 — raw만 저장, 부재≠오류

`opendart.py`는 OpenDartReader를 감싼 얇은 어댑터로, raw payload만 수집·저장하고 정규화·분석·LLM은 하지 않는다. `finstate_all`은 `reprt_code="11011"`(사업보고서) 고정이다.

**as-filed 원본 선택**이 핵심이다. `select_annual_report`(순수함수, `opendart.py:27-51`)는 정정 이력에서 원본을 고른다:

```
① report_nm에 "사업보고서" AND "(year.12)" 둘 다 포함 (타년도 정정 오염 차단)
② "정정" 미포함 원본 우선
③ 없으면 rcept_dt 최소(최초 제출 = as-filed) 선택
```

`filings`는 `final=False`로 조회해 [기재정정]/[첨부정정] 재제출 기록을 보존한다(`final=True`는 정정 이력을 뭉개 원본까지 누락).

**부재를 예외로 두지 않는다** — `document`의 미제공 보고서 ValueError는 `""`로, event/report 오류는 빈 DataFrame으로, XBRL 없는 보고서(status 013/014)는 `False`로 흡수한다. 수집 실패와 데이터 부재를 구분해 기록한다(`storage.py`의 `ABSENCE_REASONS={no_report,dart_no_data,dart_no_xbrl,ok}`).

주석은 XBRL 경로를 쓴다(`notes_xbrl.py`). 사업보고서 XBRL zip을 Arelle로 전개해 비금융 주석 fact를 추출하며, `_context_dimensions`가 세그먼트 축(`축=멤버|축=멤버`)을 보존한다. `find_annual_reports_for_company`는 회사당 목록 조회를 1회로 묶어 OpenDART 일일 한도(2만)를 절감하고, 저장은 원자적(`.tmp → os.replace`)으로 재추출 중 종료돼도 파일이 잘리지 않는다. `document()` 처리량은 동시 8스레드에서 41.8 doc/s 실측(전수 ~5,000건 ≈ 2분).

## 3.4 L1 정규화 — id-first 매핑과 소실 방지

`mapper.py`의 `map_row`는 account_id 우선(id-first)으로 canonical을 정한다. 하지만 회사가 영문 id 슬롯에 다른 실질을 신고하는 경우가 있어(id-label 모순), 규칙이 필요하다:

- id-label 모순 시 **같은 표(sj_div) 라벨 교정만** ALIAS로 허용하고, 아니면 `ID_LABEL_CONFLICT`로 id를 유지하며 label 후보를 기록(후처리 중재).
- `map_change_row`(SCE 전용)는 반대로 label을 우선한다 — SCE에서는 회사가 `dart_StockDividends` 슬롯에 주식선택권 등을 신고하는 일이 흔해 한글 라벨이 변동 실질이다.

`pipeline.py`의 정규화 순서는 `validate → map_row → _arbitrate_conflicts → _rescue_cross_statement → _dedupe_statement_rows → _dedupe_canonical_rows`이다. 두 가지 원칙이 데이터 무결성을 지킨다:

- **dedup은 소실 대신 강등 보존** — 같은 canonical에 여러 행이 잡히면 비대표 행을 드롭하지 않고 "기타 중요 계정"으로 강등한다. 소실(2종오류)과 이중계상을 동시에 차단한다.
- **자본분해 정확 조건** — `_enforce_capital_decomposition`은 `자본금 A ≈ 보통주자본금 B + 주식발행초과금 C`가 round 일치할 때**만** 분해한다. 자본잠식·우선주는 성립하지 않아 무영향이다.

**SCE 2D 보존**(`sce.py`)이 이 도구의 정규화 난이도를 상징한다. 자본변동표는 (변동행 × 자본구성요소)의 2차원 격자표다. 메인 long format이 이 열 차원을 붕괴시키므로 별도 2D long 프레임으로 보존한다. 두 검산이 무결성을 지킨다:

- `sce_balance`(세로): **기초 + Σleaf변동 = 기말** (leaf만 합산, 소계 합산은 이중계상). 허용오차 `tol = max(1000, |end|×1e-7)`.
- `sce_horizontal_identity`(가로): **변동행 총계 ≈ 지배지분 + 비지배지분**. 세로 검산이 못 보는 축. 허용오차 `tol = max(100만, |grand|×0.5%)`.

member 셀 부호는 raw에 충실하게 보존한다 — grand이 진실이라 추측해 뒤집으면 데이터 변조이고, 모순은 위 두 검산이 노출한다.

## 3.5 온보딩 게이트 — 결정론 검문 + 별칭 3단 분업

회사마다 라벨·확장계정이 무한 변주하므로, 처음 보는 회사는 정규화 직후 게이트를 거쳐야 L2에 진입한다. 게이트는 기존 감사 스크립트를 **재사용**(재구현 금지)한다.

**통과 기준**(`onboarding_gate.py:275`):
```
gate_passed = G1 완결성 FAIL 0
            AND BS 항등식 잔차 ≤ BS_TOL(1,000,000원)
            AND G3 산술검산 경성위반 0
            AND G5 신호 dangling 0
            AND 통화 KRW
```

핵심은 **hollow-PASS(빈 검사가 통과로 둔갑) 차단**이다. `_g1_verdict`는 completeness=="OK"만으로 통과시키지 않는다 — `bs_residuals`가 실재해야 한다(**검산 0건이면 "검산 못함"이지 통과 아님** — BS 핵심행 결손 시 빈 검사가 통과로 둔갑하던 갭). SCE 전 행이 unmatched(표준화 사망)여도 통과 아니다.

`_currency_ok`(`onboarding_gate.py:220-229`)는 `{통화} - _NON_CURRENCY_UNITS`에 외화(USD 등)가 남으면 False다. 외화 재무를 원화 환산 없이 분석하면 환율(~1,300배) 오차가 항등식에 안 잡혀 silent 통과하기 때문이다. `_NON_CURRENCY_UNITS = {KRW, SHARES}` — SHARES(주당이익 단위)는 통화가 아니므로 차단하지 않는다(2026-07-14 수정, 11장 참조).

**별칭 3단 분업**(원칙 1·4의 온보딩 적용)이 자동 오분류를 막는다:

```
후보 검색 = 코드   candidate_canonicals: 같은 표에서 라벨 2-gram 유사도순 ≤12개
분류 선택 = LLM    candidate 목록 안에서만 1개 선택 (밖이면 '기타 중요 계정' 강등 = _anchor, 환각 차단)
적용     = 코드    confidence≥0.7이면 자동 등록+재정규화, 임계 미만·NO_MATCH만 사람 확인 보류
```

`alias_suggest.py`의 `_anchor`(`:165-174`)는 LLM 제안이 candidate 밖이면 `NO_MATCH`로 강등하고 confidence=0을 준다. 초기 실험에서는 confidence가 회계 오답을 못 걸렀다(제조원가→매출원가 오답에 0.88 부여, ONBOARDING_LLM_PLAN) — 이후 회계힌트 라운드에서 고확신 오답이 해소된 뒤 임계(0.7) 기반 자동 등록으로 전환했고, 임계 미만·NO_MATCH 보류분에만 사람 확인이 남는다. 사람이 확정하면 `config/company_quirks.yaml`에 등록되고, `_apply_company_quirks`가 corp_code/year를 **데이터 키**로 그 회사·연도에만 적용한다(하드코딩 분기 아님, 매칭 없는 회사는 무변경).

## 3.6 실증 예시 — 진양(별도재무제표만 있는 회사)의 정규화

E2E 충실도 감사(`_E2E_AUDIT_RESULTS.md`)에서 발견된 갭 G5를 따라간다. 진양은 연결재무제표(CFS) 없이 별도(OFS)만 공시하는 단일 실체 회사다.

과거 코드는 `_account_level_series`가 `fs_div=="CFS"`로 하드코딩돼 있어, 별도만 있는 진양은 unmapped 계정이 0건으로 잡혔다 — 유의성 큰 미매핑 계정이 통째로 사라진 것이다. 근본 수리는 CFS+OFS를 둘 다 1급 series로 게시하되 series_key에 fs_div 접두(`CFS:차입금`/`OFS:차입금`)를 붙여 동명 계정의 이질 병합을 차단하는 것이었다(`company_report._account_level_series`, `_primary_fs_div` 제거). 이 수정은 부수적으로 KB의 SCE 라벨 노이즈 57건을 드러냈다. 진양은 이제 게이트를 통과해 OFS 계정 전량이 L2 패널에 실린다 — "연결과 별도를 둘 다 분석하되 섞지 않는다"(DATA_SCOPE)의 실현이다.
