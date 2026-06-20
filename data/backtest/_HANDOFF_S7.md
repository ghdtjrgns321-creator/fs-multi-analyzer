# 핸드오프 — S7(사업보고서 원문 주석·섹션 수집) 설계 확정 + 구현

> 2026-06-15. **컴팩트 후 이 파일부터 읽고 바로 실행.** 작업 디렉터리:
> C:\Users\ghdtj\workspace\portfolio\fs-multi-analyzer. 모든 결정은 실측 근거 있음
> (`_S7_STRUCTURE_PROBE.md`·`_S7_VERSION_PROBE.md`).

---

## A. 숲 — Phase1 전체 위치

목표: Phase1(수집·정규화) 신뢰 확보 후 Phase2(LLM 분식 리스크 리뷰). 단일출처
`docs/agent/COVERAGE_REMEDIATION.md` (S0~S11).

| 단계 | 상태 |
|---|---|
| S0~S2 | ✅ 완료 |
| S3 5종 신호(CIS/SCE/CF) | ✅ 닫음(측정 확인) |
| S4 미매핑·정합 | ✅ 종료(member-sign·IFRS16/관계기업 alias·01406618 기록) |
| S5 절대수준 | ✅ Phase2 perspectives가 이미 수행(코드 추가 0) |
| S6 분기/반기 | ✅ 의도적 비범위(연간 전용, `DATA_SCOPE.md §2`) |
| **S7 원문 주석·섹션** | **설계 확정(이 문서) → 구현 대기** |
| S8 감사보고서 KAM | 미착수(별도 첨부 attach_files) |
| S9 정정공시 | 미착수(원문 XI.1에 일부 포함) |
| S10 특수관계자/report·event | 미착수(원문 X·IX에 상당부분 포함) |
| S11 종료 게이트 | 미착수(16분식사 결정론/LLM 인계 매핑) |

**이번 세션(41~51차) 완료**: member-sign 검증(audit 334→0, 00141477=원공시모순 raw확증) ·
SCE **가로항등 anomaly 신호 신규**(`sce.py:sce_horizontal_identity`, dump §F 노출) ·
적대감사로 **`_align_member_signs_to_bare` overreach 발견·제거**(비차감 원공시모순을 추측으로
뒤집던 것 — 충실보존+가로항등/검산 노출로 전환) · S3/S5/S6 마감 · S4 종료. pytest **208 passed**.

**★S7은 S9·S10을 상당부분 흡수**(원문 한 문서에 정정·특수관계자·계열사 다 있음). S8만 별도 첨부.

---

## B. 진행 중 / 보류

- **보류1 — 전체 corpus persist**: `_align` 제거·alias 보강이 ~30% 저장본에 미반영(stale).
  코드는 정확(pytest·백테스트 5/6). **Phase1 마감 시 `PYTHONPATH=. uv run python -m
  src.normalize.renormalize_all --force` 1회**로 일괄 최신화(is_fresh가 부호 아닌 테이블만 보므로
  반드시 --force). 백그라운드 동시성 OK.
- **미커밋 다수**(sce.py 신규·mapper/pipeline/config·canonical_accounts.yaml·company_quirks.yaml·
  tests·probe 스크립트). **커밋은 사용자 명시 지시 시만**.

---

## C. S7 설계 (확정 — 전부 실측 근거)

### 목적
XBRL이 **못 긁는 정보 전부**(주석 서술 + 사업보고서 narrative: 우발부채·대주주거래·연결범위·
자금조달·제재·MD&A 등)를 Phase2 LLM 재료로. 주석 한정 아님. **사람용 정제 ✕, LLM용 텍스트만**.

### 측정으로 확정된 사실
1. `OpenDartReader.document(rcept_no)` = 사업보고서 전체를 **구조화 XML(dart3.xsd, ~1.3MB)**로 반환.
   주석·우발·대주주·연결범위 다 그 안. TITLE 태그로 12파트 구분.
2. **12파트 골격은 회사 불문 표준**: 층화랜덤 50(2011~2024) **49/49 부합, 이탈 0**.
3. **fetch 41.8 doc/s(동시 8) → 전수 ~5000 ≈ 2분, DART 무료.** 저장 ~900MB(텍스트)/6.5GB(원문).
4. **서식버전 35개** → **sub-section을 TITLE 키워드로 콕 집는 하드코딩은 실패**(우발/종속회사
   최신본만). 단 PART 경계는 안정, **내용은 본문에 다 있음**(삼성2017 v3.0: 종속기업 132·우발 9·
   특수관계자 35회 본문 출현 — TITLE 태깅만 안 됨).
5. 내용필터 실측(강원에너지): 전체 113K토큰 → 필터 후 **53K(46%)**, 비분식 노이즈 54% 버림.
6. **"분식 청크"는 틀린 말**(포지셔닝: 99% 정상). → **"검토 관심 공시 종류"**(판단·추정·관계·우발·
   자금·연결범위 = 감사인이 보는 종류). 정상·분식 동일 파이프, 선별은 종류 기준, 판단은 LLM.
7. note_mappings.yaml: 카테고리=XBRL concept 기반(grounded), **keywords=hand-authored(비전수)**.

### 4단 파이프라인 (LLM에 통째로 안 줌)
1. **수집**: document() fetch + **PART 통째 텍스트 추출**(35버전을 PART 경계로 흡수).
2. **baseline 씨앗**: **안 쓰던 원문 narrative를 층화 샘플 ~30-50사** LLM에 돌려 검토관심 내용어
   도출(**전수 ✕ — 표준유형이라 샘플 수렴·수 달러·수분**). 콜드스타트 fallback용.
3. **본체(B안)**: **온보딩 LLM(`onboarding.py run_llm_holistic`, 이미 회사 통독해 quirk 생성)에
   "검토관심 청크 직접 선별" 얹기** → `company_quirks.yaml`에 캐시. 고정 키워드 의존 ✕. 거의 공짜
   (이미 통독함). 키워드 baseline은 첫 패스 fallback.
4. **투입**: 선별 청크만 **관점별** LLM(`perspectives.py` material). 희석·비용 차단.

### 핵심 결정 (사용자 확정)
- sub-section TITLE 하드코딩 ✕ → **PART 단위 추출**.
- baseline **전수 ✕ / 샘플 ○**(B가 본체, baseline은 fallback).
- 통째 LLM 투입 ✕ → **내용 선별 후 투입**.
- "검토 관심 공시 종류"(포지셔닝 준수), "분식 청크" 표현 금지.

---

## D. 구현 단계 (TDD·기존 패턴 준수)

- [ ] **1. 수집기** — `src/collect/opendart.py`에 `document(rcept_no)` 수집 추가. rcept_no는
  `dart.list(corp, kind='A')` → '사업보고서' 필터로 획득. 저장:
  `data/companies/{corp}/{year}/raw/report_doc/`(원문 또는 PART 텍스트). 동시 fetch(ThreadPool).
- [ ] **2. PART 추출기** — `src/notes/` 또는 신규 모듈: DSD XML → TITLE로 12파트 분해 → PART별
  텍스트(표→행). **시대 매핑**: 구포맷(~2017, 11파트, IV=감사의견·X="이해관계자와의 거래"·XII없음)
  vs 신포맷(2018+, 12파트). 논리섹션→PART 다중패턴(거래=대주주|이해관계자 등). 못 찾으면 graceful.
- [ ] **3. baseline 씨앗** — 층화 샘플(서식버전×업종×규모 ~30-50사) 원문에 LLM 돌려 검토관심
  내용어 도출 → `config/`에 yaml(또는 note_mappings 확장). 1회. **전수 금지.**
- [ ] **4. 본체(B)** — `dashboard/onboarding.py:run_llm_holistic` 확장: 회사 원문 통독 시 검토관심
  청크 선별·`company_quirks.yaml`에 캐시(스키마: `content_chunks`/`content_keywords` 필드 추가).
- [ ] **5. Phase2 투입** — `src/report/materials.py`에 선별 청크를 관점별 material로 추가
  (내용필터=baseline+quirk). `perspectives.py`가 받음.

### 검증(각 단계)
- 수집: 동시fetch throughput 41.8 doc/s 재현.
- PART 추출: 시대 2개 + 옛버전(v2.4·3.0) 본문에 우발/종속/특수관계자 존재 재현(`_s7_version_probe.py` 참조).
- 내용필터: 113K→~53K 토큰 감소 재현.
- Phase2: perspectives가 새 material 받는지 + 백테스트 5/6 무회귀.

### 금지/주의
- 35버전 → sub-section TITLE 하드코딩 금지(PART 단위).
- "검토 관심" ≠ "분식"(포지셔닝).
- baseline 전수 금지(샘플).
- 통째 LLM 투입 금지(내용 선별 후).
- 한글 문서/config는 최소 edit + mojibake 0 확인.

---

## E. 참조 자료 (본 세션 산출)
- `data/backtest/_S7_STRUCTURE_PROBE.md` — 50 층화랜덤 12파트 표준 검증(49/49) + 포맷 시대 분석.
- `data/backtest/_S7_VERSION_PROBE.md` — 서식버전 35개·정착률·throughput·내용필터 토큰·판정.
- `data/backtest/_s7_structure_probe.py`·`_s7_version_probe.py` — 재현 스크립트(seed 고정).
- `config/playbooks/note_mappings.yaml` — 기존 주석 카테고리(concept 기반) + keywords(hand-authored).
- `src/report/perspectives.py`·`materials.py` — Phase2 관점 material 배선 지점.
- `dashboard/onboarding.py` — 온보딩 LLM 통독(B안 얹을 곳).
