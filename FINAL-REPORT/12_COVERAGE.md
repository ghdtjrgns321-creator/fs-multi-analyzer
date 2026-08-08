# 12. 전수 커버리지 부록

## 12.1 센서스

- **분모 N = 1,626** 정독 대상 파일 (code 326 · config 105 · doc 221 · text 974)
- 실행 커맨드 (census.py는 저장소가 아니라 final-report 스킬에 있는 스크립트):
  ```
  python ~/.claude/skills/final-report/scripts/census.py inventory . --exclude companies --exclude _backup_corrected
  ```
- **제외 디렉토리로 걸러진 파일 = 77,645**: `.venv` 29,705 · `companies` 43,197 · `.git` 3,490 · `_backup_corrected` 746 · `__pycache__` 299 · `.ruff_cache` 42 · `.superpowers` 34 · `.claude` 121 · `.codex` 5 · `.pytest_cache` 6
- 목록만(정독 면제) = 97

정독 분모 N은 두 층으로 나뉜다: **핵심 시스템 306 파일**(전수 정독, 12 서브에이전트 팬아웃 M/M 확인) + **`data/backtest` 1,320 파일**(백테스트·감사 스크래치 작업공간, 대표 표본 정독 + 글롭 커버).

> **정독 이후 증분**(2026-07-18): 게이트 점검 모듈 3(`gate_identities`·`gate_quality`·`gate_yoy`)과 대응 테스트 3이 추가돼 핵심 시스템은 **312 파일**이 됐다.
>
> **정독 이후 증분**(2026-08-02): 이관 원장 모듈 3(`transfer_ledger`·`ledger_financials`·`ledger_notes`)과 테스트 1이 추가돼 **316 파일**이 됐다. 게이트를 조건 목록에서 원장(원본 전량 차집합)으로 교체하면서 임계 기반 차단(미매핑 20%·주석 적재율 50%)은 삭제했다.
>
> **정독 이후 증분**(2026-08-08): 주석 청킹 모듈 1(`src/report/chunking.py`)과 테스트 1(`tests/test_chunking.py`)이 추가돼 **318 파일**이 됐다. 사업보고서 III장(주석)을 서술 리더에 편입하면서 필요해진 분할·중복제거이며, XBRL 주석이 없는 회사연도(2022년 이하 99.5~100%)의 주석 경로를 여는 변경이다.
>
> 신규분은 3장(게이트)·9장(테스트)에 반영돼 있고, 여기 분모는 최초 전수 정독 시점 기준임을 명시한다 — 사후 증분을 원래 정독 범위처럼 적지 않는다.

## 12.2 명시 제외 (--exclude)

| 디렉토리                                       | 건수   | 사유                                                                                   | 대표 표본 다룬 장                    |
| ---------------------------------------------- | ------ | -------------------------------------------------------------------------------------- | ------------------------------------ |
| `companies` (`data/companies`)                 | 43,197 | 회사/연도별 균일 생성 데이터(OpenDART 원본 JSON·주석 XBRL(TSV)). 회사당 동일 구조 반복 | 3장(수집·정규화 메커니즘), 실증 예시 |
| `_backup_corrected` (`data/_backup_corrected`) | 746    | 정정 전 백업 코퍼스(위와 동일 구조)                                                    | 3장                                  |

두 코퍼스는 분석 대상 원자료로, 파일마다 회사·연도만 다른 균일 데이터다. 구조·대표 표본은 3장(정규화)과 2·5장(실증 예시)에서 실제 ID·값으로 다뤘다.

## 12.3 파일 → 장 매핑

핵심 시스템 306 파일은 서브시스템별로 해당 장에 1:1 반영됐다(디렉토리 글롭 = 서브에이전트가 전수 정독한 파일 집합, 표 압축이지 커버리지 갭 아님).

`src/report/**` · L4 리포트/카드 파이프라인 → 5·6장
`src/agents/**` · PydanticAI 관점 에이전트·retry·가드레일 → 5·6장
`src/schemas/**` · Pydantic 스키마(IssueType·SuspicionItem·AccountFinding) → 5장
`src/notes/**` · 사업보고서 PART 추출 → 3·5장
`src/orchestrate/**` · 오케스트레이션 자리표시자 → 2장
`src/collect/**` · L0 OpenDART 수집 → 3장
`src/normalize/**` · L1 정규화·온보딩 게이트(점검 모듈 `gate_identities`·`gate_quality`·`gate_yoy` 포함)·SCE·라벨 감사 → 3장
`src/signals/**` · L2 신호엔진(프로파일러·전수 스캔·비율) → 4장
`src/analysis_tools/**` · tool DSL → 4·6장
`src/peers/**` · 동종 벤치마크 → 4·5장
`src/db/**` · DuckDB 격리 → 3·4장
`src/backtest/**` · 백테스트 채점 → 9장
`src/__init__.py` · src 루트 패키지 → 1장
`config/**` · 플레이북 YAML(계정지식 데이터화) → 3·4·5장
`dashboard/**` · Streamlit UI → 7장
`golden/**` · 골든 테스트 2검사 → 9장
`tests/**` · 단위·통합 테스트(계약·불변식) → 9장
`docs/**` · 설계 문서(PLAN·DECISION·VERIFICATION 등) → 전 장 뼈대
`dev/**` · 진행 중 작업(계획·프롬프트) → 8·10장
`AGENTS.md` · 비-Claude 에이전트 규약 → 1장
`CLAUDE.md` · 프로젝트 규칙 → 1장
`README.md` · 프로젝트 소개 → 1장
`pyproject.toml` · 의존성·툴 설정 → 1장
`*.env.example` · 환경변수 예시(권한 정책상 원문 미확보, CLAUDE.md 근거로 키 3종 기록) → 1장
`*.gitignore` · git 제외 목록 → 12장

## 12.4 글롭 행 — data/backtest 스크래치 작업공간

`data/backtest/**` · 백테스트·감사·E2E 측정 스크래치 작업공간(md 78·py 121·덤프 디렉토리 8) → 9·11장

`data/backtest`는 균일한 역할의 검증·감사 아티팩트다 — 일회성 감사 스크립트(`_audit_*.py`·`_da_*.py`)가 운영 함수를 그대로 호출해 계정 단위로 계측하고, 그 결과·사고를 핸드오프/브리프 md와 덤프 디렉토리(`_review_dumps` 411·`_s7_sample` 302·`raw_text` 230·`_holistic_findings` 34·`_gate_dumps` 15 등)에 남긴 곳이다. 대표 표본(핸드오프·감사 브리프 md 20개 + 대표 스크립트 4개 + 덤프 디렉토리 10개)을 정독했고, 거기서 나온 실측치(E2E 시간·비용, 백테스트 recall 5/6)와 사고 기록(id_label_conflict·member-sign 등)을 9장(검증)·11장(트러블슈팅)에 반영했다. 전량 정독이 아니라 대표 표본 정독 + 글롭 커버임을 명시한다.

## 12.5 목록만(정독 면제) 파일

`data/backtest` 하위의 `.csv`·`.jsonl`·`.parquet` 등 데이터·바이너리 97건은 정독 면제(census `LIST_ONLY_EXTS`). 대표: `_dg_load_notes.jsonl`(주석 로드 결과), `coverage_audit_cache/*.csv`(감사 캐시)는 8장·11장에서 성격만 참조했다.

## 12.6 verify 결과

```
$ python census.py verify . FINAL-REPORT/12_COVERAGE.md --exclude companies --exclude _backup_corrected
인벤토리 N = 1626, 커버리지 표 경로 = 28 + 글롭 24
PASS — 전수 커버리지 1626/1626
```
