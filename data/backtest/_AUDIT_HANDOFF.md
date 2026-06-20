# DART 커버리지 감사 — 핸드오프 (다른 컨텍스트에서 이어받기)

> 이 문서 하나로 현재 상태·문제·남은 일을 재개할 수 있게 정리. 작성 시점 기준.

## 1. 무슨 문제였나 (과제 원본)

"우리가 재무제표를 전수로 본다"는 주장이 거짓임을 **코드 경로 + 실데이터**로 검증.
DART 제공 데이터 → 수집(L0)→정규화(L1)→신호(L2)→관점입력 각 단계를 **계정 단위까지 전수 매핑**해
무엇을 받고/보고/버리는지 정량화. 제약: LLM 호출 없음(결정론), 코드 수정 금지(읽기·집계·보고만),
추측·단일샘플 단정 금지(전수), 한글 인코딩 주의. 산출물 = `data/backtest/COVERAGE_AUDIT.md`.

## 2. 지금 상태

### (A) 완료 — 전역 강제 장치 설치 (audit과 별개, 재작업 불필요)
원인 진단: 1차 감사 때 "빨리 그럴듯하게 끝내려는 압력"으로 도구가 보는 부분집합(BS/IS·한 해)만
측정하고 전수 요구를 누락. 재발 방지를 위해 전역 설정 완료:
- `~/.claude/CLAUDE.md` **§10 전수 측정** 추가.
- `~/.claude/settings.json` hook 2개 병합(기존 hook 보존):
  - UserPromptSubmit → `hooks/completion_discipline.sh` (완료 규율 주입, 키워드 무관)
  - Stop → `hooks/completion_gate.sh` (종료 시 1회 자가검증 강제, stop_hook_active로 무한루프 차단, fail-open)
- 검증: pipe-test 4입력 + JSON 유효 + 라이브 발화 확인됨. **이 항목은 손대지 말 것.**

### (B) 부분 완료 — COVERAGE_AUDIT.md
`data/backtest/COVERAGE_AUDIT.md` 작성됨(408줄). 아래는 **검증 끝난 부분**:
- §1 API: OpenDartReader 24메서드 중 4개만 사용(finstate_all·company·list·finstate_xml). 감사보고서·정정·특수관계자 미수집. ✅ grep 확인
- §2 reprt_code=11011만, fs_div CFS/OFS 둘 다. ✅
- §3 sj_div 생존: raw vs 정규화 행수 집계(BS 12434→12189, IS 1591→1579, CIS 5778→5346, CF 14000→13633, SCE 14728→2811). 신호스캔=BS/IS만. ✅
- §6 신호 전부 "변화"기반(level 이상 없음), ratios는 리포트 숫자로만. ✅ 코드 확인
- §7 주석: DART indCd 직접 조회로 70종 UNION 확인(XBR103=8, 전부 수집). 무형자산·개발비·관계기업 주석은 구조화엔드포인트에 없음(원문 미수집). ✅
- §5 신호 후보율 깔때기: 27사 funnel. **검증 앵커 = 삼성 2025 → 61계정/floor통과34/미달27(44.3%) = 사용자 측정 "34/61" 정확 일치.**

### (C) 미완 — COVERAGE_AUDIT.md 5개 구멍 (★ 다음 작업)
1차 감사가 좁힌 부분. 아직 안 채움:

| # | 구멍 | 현재 | 채워야 할 산출물(전수 스펙) |
|---|---|---|---|
| 1 | frmtrm 재작성 | 아스트 1건만(684억) | **분식 16사 전수**: 각 사 핵심계정의 frmtrm(N년 전기) vs thstrm(N-1년 당기) 차이 표. 몇 사·몇 계정에서 재작성 탐지되는데 우리가 놓치는지 정량 |
| 2 | 계정 운명표 | BS/IS·한 해 funnel만 | **전 sj_div(CIS/CF/SCE 포함) 계정별 raw존재→정규화결과(canonical/기타중요/미매핑)→신호운명** 행 단위 테이블. 표본별 |
| 3 | 분식 16사 주석 수집 여부 | 삼성만 확인 | 16사 각 연도 notes/ 디렉터리 html 존재 집계(안 받은 회사 있나) |
| 4 | dedup 정보손실 | "대부분 아님" 단정만 | `_dedupe_canonical_rows`/`_dedupe_statement_rows`가 실제로 버린 행을 1~2사에서 실물 출력 → 진짜 중복인지 distinct 계정인지 |
| 5 | 미매핑 계정명 | 비율(45~83%)만 | 미매핑(기타 중요 계정) 중 큰 금액 계정명 나열 — 무슨 중요계정이 canonical에서 빠지나(개발비·리스부채·사용권자산 등?) |

## 3. 재현 자산 (그대로 재사용)

```
하니스      data/backtest/_coverage_audit.py
  함수      funnel(cc, target_year) · raw_sjdiv_counts(cc) · load_all_years(cc) · collected_years(cc)
  상수      FRAUD(16) · NORMAL(10) · SAMSUNG(1) dict (corp_code→이름)
  실행      uv run python  (※ duckdb는 uv 환경에만. python3는 Store 스텁이라 'python' 또는 'uv run' 사용)
집계결과    data/backtest/_audit_funnel.json  (27사 × fate_rows 1240행, floor_miss_accounts 포함)
보고서      data/backtest/COVERAGE_AUDIT.md   (부분 완료, 위 5개 보강 대상)
원천데이터  data/companies/{corp_code}/{year}/raw/finstate_all_{CFS,OFS}.csv (18컬럼)
            data/companies/{corp_code}/{year}/raw/notes/{CFS,OFS}/D*.html
            data/companies/{corp_code}/{year}/analysis.duckdb (table: normalized_financials, 단일연도)
```

## 4. 표본 (27사)

```
분식16: 00159616두산에너빌리티 00409681아스트 00118345디아이동일 00657783모델솔루션
        00413046셀트리온 01091382세토피아 00108649티피씨 00127699유네코 01098792본느
        00480756이트론 00526696웨이브 00141273웰바이오텍 00125521에스엘 00116426이렘
        00351454더테크놀로지 00163716한창
정상10: 00164779SK하이닉스 00356361LG화학 00157070한국단자 00139083아진산업 00100601강원에너지
        00102432계룡건설 00148364하림지주 00120526롯데쇼핑 00164645HMM 00176914다우기술
삼성  : 00126380
대상연도: 분식=각 사 마지막 fraud run_year, 정상/삼성=2024
```

## 5. 핵심 코드 사실 (재확인 끝, 출처)

- 정규화 사용 컬럼 7개(corp_code·bsns_year·sj_div·account_id·account_nm·thstrm_amount·account_detail[dedup만]) — `src/normalize/pipeline.py`
- frmtrm·bfefrmtrm·ord·currency·thstrm_add 미사용 — `grep -rn` 0건
- 신호 BS/IS 한정 — `src/signals/universal.py:36`
- floor = max(자산총계×1%, 1억) — `relationship_chains.yaml` universal_min_pct_of_assets:1.0 / universal_min_abs_amount:1e8
- canonical 계정에 CIS·SCE statement = 0개 — `config/canonical_accounts.yaml`
- 주석 매핑 9키→8 note_code, 무형자산/개발비/관계기업 없음 — `config/playbooks/note_mappings.yaml`

## 6. 다음 액션

5개 구멍을 §10(전수) 기준으로 채워 COVERAGE_AUDIT.md 갱신. 진행 범위(5개 전부/일부)는 사용자 확인 후.
임시 산출물(_coverage_audit.py, _audit_funnel.json, 이 핸드오프)은 audit 종료 시 정리 여부 결정.
