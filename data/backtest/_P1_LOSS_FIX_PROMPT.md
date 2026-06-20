# P1 소실·오매핑 수정 프롬프트 — 핸드오프 (다른 컨텍스트에서 실행)

> 이 문서 하나로 수정 작업을 재개할 수 있게 정리. LLM 심층 탐색(2026-06-10)으로 원인까지
> 규명된 상태이며, 남은 것은 **수정 + 검증**이다. 탐색 경위는 [docs/agent/STATE.md](../../docs/agent/STATE.md),
> 검증 프레임은 [docs/agent/PHASE1_VERIFICATION_PROTOCOL.md](../../docs/agent/PHASE1_VERIFICATION_PROTOCOL.md).

## 0. 배경 (왜 이 작업인가)

리뷰 하니스(`_p1_company_review.py` §D 원문대조)가 분식 19 회사연도에서 "소실 후보 9건"을
보고했다. LLM 심층 탐색으로 해부한 결과:

- 9건 중 **7개 회사연도분은 거짓 소실**(SCE 차감변동 -abs 부호 정규화 — 데이터 정상, 하니스
  §D가 부호까지 일치해야 생존 처리한 탓).
- **2건(세토피아 2019)은 진짜 소실**(CFS dedup 버그).
- 탐색 중 소실보다 큰 결함 2개 추가 발견: **SCE 구성요소 표준화 전사 사망**(T1),
  **id-label 모순 오매핑**(T3).

수정 타깃은 아래 4개. 우선순위 순서대로 진행한다.

---

## T1. SCE account_detail 형식 회귀 — 구성요소 표준화 전사 사망 (★최우선)

### 증거 (재현 가능)
```bash
uv run python -c "
import duckdb
con = duckdb.connect('data/companies/00118345/2017/analysis.duckdb', read_only=True)
print(con.execute('SELECT component_role, count(*) FROM sce_equity_components GROUP BY 1').fetchdf())
print(con.execute('SELECT DISTINCT detail_path FROM sce_equity_components LIMIT 8').fetchdf())
"
```
- component_role = **전부 'unmatched'**(172행), marker 0행. 6사 19 회사연도 공통.
- detail_path가 `ComponentsOfEquityAxis=RetainedEarningsMember` 같은 **XBRL member 코드**.

### 원인
원본(정정 전) 교체 시 XBRL→CSV 컨버터(`data/backtest/_xbrl_to_finstate_csv.py`)가
account_detail에 XBRL axis=member 코드를 기록. 그러나 SCE 구성요소 분류기는 **한글 alias**
기반이다:
- `config/canonical_accounts.yaml` `sce_equity_components:` aliases = 자본금·이익잉여금 등 한글.
- `sce_fs_total_markers: [연결재무제표, 별도재무제표]` — member 코드와 절대 매칭 불가.
- 분류 경로: `src/normalize/config.py:30` `SceComponentMap.classify()` →
  `src/normalize/sce.py:97` `classify_component()`.

DART 정정본의 원래 account_detail은 한글 경로("연결재무제표 | 이익잉여금")였으므로
이것은 **원본 교체 작업이 만든 회귀**다.

### 수정 방향 (권장: ①)
1. **컨버터 수정(권장)**: `_xbrl_to_finstate_csv.py`가 member 코드를 한글 라벨로 변환해
   account_detail을 DART 정정본과 동일한 형식("연결재무제표 | 이익잉여금")으로 합성.
   XBRL 원본에 label_ko가 있으므로 member→한글 매핑 가능. 매핑 불가 member는 코드
   그대로 보존(소실 금지). 변환 후 **재정규화 필요**.
2. (대안/보강) `sce_equity_components` aliases에 표준 member 코드(RetainedEarningsMember 등)
   추가. 단 udf_* 커스텀 member는 회사별이라 alias로 못 덮는다 — ①이 근본 해결.

### 수용 기준
- 19 회사연도 재정규화 후 component_role에 marker/leaf 등장(전부 unmatched 금지).
- SCE 검산(기초+Σ변동=기말, T4의 §F 재작성 기준)이 19건 중 대다수에서 차이≈0.
- 매핑 안 되는 member도 행은 보존(행수 불변 — §D funnel SCE raw→norm 수 유지).

---

## T2. CFS blank account_id 동명행 dedup 소실 — 실데이터 증발

### 증거 (재현 가능)
```bash
grep "파생상품부채\|리스부채" data/companies/01091382/2019/raw/finstate_all_CFS.csv
uv run python -c "
import duckdb
con = duckdb.connect('data/companies/01091382/2019/analysis.duckdb', read_only=True)
print(con.execute(\"SELECT fs_div, sj_div, canonical, label, amount FROM normalized_financials WHERE label LIKE '%파생%' OR label LIKE '%리스부채%'\").fetchdf())
"
```
- raw CFS BS: 동명 2행씩 존재 — 파생상품부채 4,435,767,233(ord 28, 유동)+**944,653,799**(ord 35,
  비유동), 리스부채 **297,623,861**(ord 29, 유동)+359,238,028(ord 36, 비유동). account_id는
  전부 `-표준계정코드 미사용-`(blank).
- norm CFS: 각 1행만 생존 — 945백만·298백만 **증발**.
- **같은 데이터의 OFS는 정상**: 비유동파생상품부채 944,653,799·유동리스부채 251…·비유동리스부채
  301… 전부 분리 생존 → CFS 경로만의 dedup 버그.
- 부수 결함: 생존 행의 canonical도 비일관(CFS '리스부채' vs OFS '유동/비유동리스부채').

### 원인 추정 (수정 시 확정할 것)
`src/normalize/pipeline.py`의 dedup(`_dedupe_*`)이 blank account_id 동명행을 중복으로 오인.
유동/비유동 구분 정보(ord 위치 또는 직전 소계 문맥)가 dedup 키에 없음. OFS가 생존하는
이유(키 차이? 경로 차이?)를 먼저 규명하고 동일 원리로 CFS를 고친다 — 증상 패치 금지.

### 수용 기준
- 01091382/2019 CFS에 파생상품부채 944,653,799·리스부채 297,623,861 생존(유동/비유동 구분).
- §D 미출현(부호 무시 비교, T4 반영 후)에서 01091382/2019 = 0건.
- 의미: 세토피아는 BW 분식 케이스, 파생상품부채가 메커니즘 핵심 계정. 수정 후 백테스트에서
  세토피아 신호 변화 여부 관찰(개선 기대, 단 회귀 가드는 기존 baseline 유지).

---

## T3. id-label 모순 오매핑 — 주식선택권이 배당으로 분류

### 증거 (재현 가능)
```bash
uv run python -c "
import duckdb
con = duckdb.connect('data/companies/00159616/2017/analysis.duckdb', read_only=True)
print(con.execute(\"SELECT change_label, change_canonical, account_id, amount FROM sce_equity_components WHERE change_label LIKE '%주식선택권%' LIMIT 5\").fetchdf())
"
```
- change_label **"주식선택권"**(주식보상) + account_id `dart_StockDividends`(주식배당) →
  change_canonical **"배당금의 지급(SCE)"**. 주식보상 -3,292백만이 배당으로 집계.
- 같은 회사의 "종속기업의 주식선택권"은 '기타 중요 계정' — 같은 실질이 행마다 다른 canonical.

### 원인
회사가 XBRL의 StockDividends 슬롯에 주식선택권 변동을 신고. 매퍼(`src/normalize/mapper.py`)가
account_id를 label보다 우선해 모순을 못 본다. PROTOCOL D3(영문 id vs 한글 label 모순) 유형.

### 수정 방향
id 매핑과 label 매핑이 **서로 다른 canonical을 가리키면 모순으로 처리**: label 우선(한글
공시명이 실질) 또는 최소한 '기타 중요 계정'으로 게시(잘못된 canonical 단정 금지). 특정
계정명 하드코딩 금지 — 모순 감지는 일반 규칙으로 구현. 기존 backtest 결과에 영향 주는
변경이므로 mapping_status에 모순 흔적(예: `id_label_conflict`)을 남겨 투명하게.

### 수용 기준
- 00159616 2017~2019 주식선택권 행이 '배당금의 지급(SCE)'에서 제외.
- 모순 감지 단위테스트(id→A, label→B인 합성 행) 추가.
- 기존 정상 매핑(모순 없는 행)의 canonical 분포 회귀 없음(재정규화 전후 diff로 확인).

---

## T4. 하니스 보강 — 거짓 경보 제거 + 죽은 검사 부활 【✅ 완료 2026-06-10 — 아래는 기록용】

> T4는 본 프롬프트 발행 직후 같은 세션에서 선반영 완료. 전수 재실행 결과 거짓 소실
> 7개 회사연도분 → 0, 세토피아/2019 진짜 소실 2건 유지, SCE표준화 FAIL 18/19 기계 노출.
> **부활한 §F 검산이 신규 이상 3건 검출**: 00159616/2017 차이 -1,144백만 ·
> 00413046/2018 차이 2,431,929백만(≈2.4조!) · 01091382/2018 차이 10,512백만.
> 단 SCE 표준화 사망(T1) 상태의 검산이므로 T1 수정 후 재평가 필요 — T1 수용 기준에 반영.
> 추가 산출물: 판정 매트릭스(`_review_dumps/_VERDICT_MATRIX.md`) + 게이트
> (`_p1_verdict_gate.py`) + 전용 에이전트(`.claude/agents/p1-auditor.md`).
> T1~T3 완료 후 **매트릭스를 삭제하고 재생성→LLM 통독→게이트 통과**까지가 완료 조건.

### 4a. §D 미출현 검사를 부호 무시로 (`data/backtest/_p1_company_review.py`)
- 현재: raw 양수 11,804가 norm -11,804(-abs 차감 정규화)로 살아있어도 "소실"로 거짓 경보.
- 수정: `abs(amt)` 기준 비교. 단 **부호만 반전돼 생존한 행은 별도 카운트**(`부호반전=N`)로
  [기계요약]에 노출 — 부호 정보를 조용히 버리지 않는다(차감 canonical 외의 부호 반전은
  그 자체가 버그 단서).

### 4b. §F SCE 검산 재작성 (hollow 제거)
- 현재: `component_role == 'marker'` 필터 — T1 회귀로 marker 0행이라 전 회사에서
  "기초 0 + Σ0 = 0 vs 0" 무의미 출력(빈 집합이 통과처럼 보임).
- 수정: ①빈 집합이면 "⛔ 검산 불가(marker 0행)"를 명시 FAIL로 출력(T1 수정 전에도 죽은
  검사가 보이게) ②검산 자체는 component_std='-'(bare 합계열) 행 + change_canonical
  기초자본/자본총계 기반으로 재작성. [기계요약]에 `SCE검산=OK/FAIL(차이)/불가` 추가.

### 4c. §D funnel에 CIS→IS 재분류 주석
- CIS 행수 격차(예: 30→13)는 단일포괄손익계산서의 IS성 행을 IS로 재분류한 정상 동작
  (전수 추적으로 손실 0 확인됨). funnel 출력에 "CIS 격차는 IS 재분류 포함" 한 줄 명시
  또는 IS+CIS 합산 병기 — LLM 독자의 오판 방지.

### 수용 기준
- 수정 후 `_p1_review_all.py` 전수 재실행: 거짓 소실 7개 회사연도분 → 소실 0,
  01091382/2019는 T2 수정 전까지 소실 2 유지(진짜 소실이 가려지면 안 됨).
- §F가 19건 전수에서 검산 결과 또는 명시적 "불가 FAIL"을 출력(무의미한 0 출력 금지).

---

## 검증 프로토콜 (전 타깃 공통 — 순서 고정)

1. **TDD**: 각 타깃마다 실패 테스트 먼저(T1 컨버터 member→한글, T2 dedup 보존, T3 모순
   감지, 기존 `tests/test_normalize.py` 형식 준수).
2. T1·T2·T3 수정 → 분식 6사 19 회사연도 **재정규화**(`src/normalize/renormalize_all.py`).
3. `PYTHONPATH=. uv run python data/backtest/_p1_review_all.py` 전수 — 수용 기준 대조.
   소실/병합/SCE검산 컬럼을 회사연도별로 기록.
4. **백테스트 회귀 가드**: `src/backtest/run_backtest.py` — recall 5/6 이상 유지(분식
   discovered 5사 + 대조군 미발굴 유지). 세토피아 변화는 별도 보고(개선이어도 단정 금지).
5. `uv run pytest tests/ -v` 전체 통과.
6. 문서 갱신: STATE.md(결과), PHASE1_VERIFICATION_PROTOCOL.md(B3·C3·D3 상태, 발견 이력).

## 제약 (글로벌 룰 발췌 — 위반 금지)

- **한글 인코딩 가드**: 한글 포함 파일은 PowerShell 텍스트 왕복·일괄치환 금지, 최소 diff 편집.
- **하드코딩 금지**: 회사코드·계정명·연도로 분기하는 수정 금지. 근본 원인을 일반 규칙으로.
- **커밋은 사용자가 명시 요청할 때만.**
- **§9**: 수치 곧이곧대로 보고 금지 — 수용 기준 수치를 직접 재현해 검증. 빈 집합·fallback을
  PASS로 둔갑 금지.
- **검증은 2+ 케이스**(ripple-search): CFS 회사 + OFS 전용(01091382) 양쪽에서 확인.

## 재현 자산

```
하니스(단일/전수)   data/backtest/_p1_company_review.py / _p1_review_all.py
dump(19 전수)       data/backtest/_review_dumps/<corp>_<fy>.txt + _ALL.txt
컨버터              data/backtest/_xbrl_to_finstate_csv.py
정규화              src/normalize/{pipeline,sce,mapper,config}.py + config/canonical_accounts.yaml
대상(전수)          known_cases.json positive·runnable 6사 19 회사연도 (하드코딩 금지, targets() 사용)
원천                data/companies/{corp}/{year}/raw/finstate_all_{CFS,OFS}.csv · analysis.duckdb
백업(정정본)        data/_backup_corrected/  (수정 중 원본 raw 덮어쓰기 금지)
```
