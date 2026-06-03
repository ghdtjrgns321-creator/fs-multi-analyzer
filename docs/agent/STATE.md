# STATE — 현재 작업 상태

> 새 세션·다른 프롬프트는 **이 파일부터** 읽는다. "지금 어디까지 됐고 다음은 무엇인가."
> 작업 종료 시 반드시 갱신한다. 전체 흐름은 [OVERVIEW.md](OVERVIEW.md), 상세 설계는
> [PLAN.md](PLAN.md), 할 일 전체는 [ROADMAP.md](ROADMAP.md).

## 현재 위치

- 단계: 설계 확정 → 프로젝트 뼈대 구축 → L0 수집 → L1 정규화 → L2 신호엔진 →
  **전 계정 보편 스캔 + BS·IS·CF·연결 신호 + L4 6관점 live 재실행 완료**
- 최근 작업 (2026-06-03): BS 34개, IS 17개, CF 18개 canonical을 raw account_id 기반으로
  등록하고 L1 정규화를 재실행했다. `src/signals/universal.py`를 추가해 BS·IS·CF 모든
  account_id에 YoY, z-score, 구성비 급변, CFS/OFS 괴리 신호를 적용했다. relationship chain에는
  영업이익→순이익, 차입금→재무활동CF→투자활동CF/CAPEX, 순이익→영업CF→운전자본변동,
  연결 구조·비지배지분 사슬을 추가했다. L4 6관점 live에서 사업결합순현금유출,
  장기차입금차입, 운전자본변동, 기타수익 z-score, 장기금융상품 취득, 기타자본항목 CFS/OFS
  괴리가 queue 상위로 올라왔고, 교차 결과는 사업결합순현금유출 conflict로 나왔다.

## 완료

- 설계 단일 출처 [PLAN.md](PLAN.md) — 아키텍처 L0~L6, 원칙 5개, MVP 1~3
- 결정 D1~D4 ([DECISION.md](DECISION.md))
- 스킬 2종(`disclosure-review`/`disclosure-testing`) + skill-rules.json
- CLAUDE.md, pyproject.toml, config/playbooks, src/ 스캐폴딩, `src/schemas/findings.py`
- Codex/비-Claude 진입점 [../../AGENTS.md](../../AGENTS.md) + [CODEX.md](CODEX.md)
- L0 수집 모듈 [../../src/collect](../../src/collect)
- L0 raw 데이터 `data/companies/00126380/{2022,2023,2024,2025}/raw/`
- Raw 데이터 계약 [DATA_CONTRACT.md](DATA_CONTRACT.md)
- L1 정규화 모듈 [../../src/normalize](../../src/normalize)
- L1 canonical config [../../config/canonical_accounts.yaml](../../config/canonical_accounts.yaml)
- L1 정규화 결과 `data/companies/00126380/{2022,2023,2024,2025}/analysis.duckdb`
- L1 측정 보고서 [NORMALIZE_REPORT.md](NORMALIZE_REPORT.md)
- 결정 D5 ([DECISION.md](DECISION.md))
- L2 tool DSL [../../src/analysis_tools](../../src/analysis_tools)
- L2 MVP1 관계 사슬 계산 [../../src/signals](../../src/signals)
- L2 계산 보고서 [SIGNAL_REPORT.md](SIGNAL_REPORT.md)
- L2 threshold 빨간불 추출 [../../src/signals/red_flags.py](../../src/signals/red_flags.py)
- 수치 분석가 1명 [../../src/agents/numeric_analyst.py](../../src/agents/numeric_analyst.py)
- D82242 주석 인덱서 [../../src/notes/indexer.py](../../src/notes/indexer.py)
- 매출채권 주석 분석가 [../../src/agents/note_analyst.py](../../src/agents/note_analyst.py)
- 매출채권 주석 매핑 [../../config/playbooks/note_mappings.yaml](../../config/playbooks/note_mappings.yaml)
- 외부 맥락 스키마 [../../src/schemas/context.py](../../src/schemas/context.py)
- Google Search grounding ContextBrief [../../src/agents/context_brief.py](../../src/agents/context_brief.py)
- 범용 계정 Finding 파이프라인 [../../src/agents/account_finding.py](../../src/agents/account_finding.py)
- 재고 Finding 실행점 [../../src/agents/first_inventory_finding.py](../../src/agents/first_inventory_finding.py)
- 첫 Finding 실행 기록 [FINDING_REPORT.md](FINDING_REPORT.md)
- Gemini 일시 오류 재시도 테스트 [../../tests/test_red_flags_and_agent.py](../../tests/test_red_flags_and_agent.py)
- 주석 파싱/주석 분석가 mock 테스트 [../../tests/test_notes_and_note_agent.py](../../tests/test_notes_and_note_agent.py)
- 외부 맥락 출처/비오염 테스트 [../../tests/test_context_brief.py](../../tests/test_context_brief.py)
- 재고 계정 파이프라인 mock 테스트 [../../tests/test_account_finding_pipeline.py](../../tests/test_account_finding_pipeline.py)
- 결정 D6 ([DECISION.md](DECISION.md))
- 결정 D8 ([DECISION.md](DECISION.md))
- 감사기준·K-IFRS 근거 평가 [AUDIT_BASIS.md](AUDIT_BASIS.md)
- 관계 사슬별 audit_basis 매핑 [../../config/playbooks/relationship_chains.yaml](../../config/playbooks/relationship_chains.yaml)
- 실무 재무지표 플레이북 [../../config/playbooks/financial_ratios.yaml](../../config/playbooks/financial_ratios.yaml)
- 2단계 기준 선정 방법론 [../user/METHODOLOGY.md](../user/METHODOLOGY.md)
- 기본 합계 계정 7개 추가 [../../config/canonical_accounts.yaml](../../config/canonical_accounts.yaml)
- 실무 재무지표 계산기 [../../src/signals/ratios.py](../../src/signals/ratios.py)
- 삼성 3개년 실무 재무지표 보고서 [RATIO_REPORT.md](RATIO_REPORT.md)
- L4 통합 리포트 조립기 [../../src/report](../../src/report)
- 삼성 L4 통합 리포트 [INTEGRATED_REPORT.md](INTEGRATED_REPORT.md)
- 통합 리포트 결정론/LLM mock 테스트 [../../tests/test_integrated_report.py](../../tests/test_integrated_report.py)
- 결정 D9 ([DECISION.md](DECISION.md))
- 결정 D10 ([DECISION.md](DECISION.md))
- 결정 D11 ([DECISION.md](DECISION.md))
- 결정 D13 ([DECISION.md](DECISION.md))
- 결정 D14 ([DECISION.md](DECISION.md))
- 결정 D15 ([DECISION.md](DECISION.md))
- L4 6관점 live 통합 리포트 [INTEGRATED_REPORT.md](INTEGRATED_REPORT.md)
- 동종업계 피어 config [../../config/industry_peers.yaml](../../config/industry_peers.yaml)
- 피어 지표 baseline [../../src/peers](../../src/peers)
- 남은 주석 카테고리 매핑 [../../config/playbooks/note_mappings.yaml](../../config/playbooks/note_mappings.yaml)
- 장기차입금·사채·충당부채 canonical 보강 [../../config/canonical_accounts.yaml](../../config/canonical_accounts.yaml)
- BS·IS·CF 주요 canonical 확장 [../../config/canonical_accounts.yaml](../../config/canonical_accounts.yaml)
- IS·CF 흐름 관계 사슬 보강 [../../config/playbooks/relationship_chains.yaml](../../config/playbooks/relationship_chains.yaml)
- 전 계정 보편 스캔 [../../src/signals/universal.py](../../src/signals/universal.py)
- 2025 포함 raw contract [DATA_CONTRACT.md](DATA_CONTRACT.md)

## 다음 할 일 (우선순위)

1. 공시 변동 고도화: D82757 및 주요 주석의 전기/당기 텍스트 diff로 우발부채 문구 확대·축소를
   수치 충당부채 변동과 교차한다.
2. CF 흐름 리포트 보강: 사업결합순현금유출, 장기차입금차입, 자기주식취득, 운전자본변동의
   구성과 원천/사용처를 표로 분리한다.
3. `gemini-2.5-flash`로 2025 재고/매출채권 live Finding 재실행:
   `uv run python -m src.agents.first_inventory_finding`

## 열린 이슈 / 주의

- `finstate_all` 응답에는 `fs_div` 컬럼이 없다. 수집 context에서 CFS/OFS를 주입해야 한다.
- `account_id == "-표준계정코드 미사용-"` 행이 존재한다. MVP1/합계 계정에서는 `매입채무`,
  `이자비용`, `당기순이익` 일부 과거 행과 `단기차입금`(2023~2025)이 label alias 보조를
  필요로 했다.
- 전체 raw 행 기준 미매핑 행은 여전히 존재한다. 이제 L4 review queue는 target year CFS의
  금액 큰 미등록 계정을 `unmapped_material_account`로 Low risk 노출하고, 전수 보편 스캔은
  미등록 BS·IS·CF account_id도 label/account_id로 신호화한다.
- 연결 특유 이슈는 별도 에이전트가 아니라 CFS/OFS 괴리와 연결 구조 사슬로 흡수한다. 영업권은
  raw에서 단독 계정이 아니라 `ifrs-full_IntangibleAssetsAndGoodwill`에 포함되어 무형자산으로
  다룬다.
- 주석은 표와 텍스트가 섞인 HTML이다. 단순 TXT만으로는 행/열 구조가 손실된다.
- 현재 주석 인덱서는 8개 카테고리 모두 섹션 단위 텍스트로 보존한다. 행/열 정밀 복원은
  아직 하지 않았다.
- 충당부채는 2025 threshold 기준 수치 red flag가 없어 계정 Finding은 생성되지 않았다.
  대신 D82757 섹션은 L4 주석 관점에서 우발부채 공시 검토 후보로 반영된다.
- ROI는 공시 재무제표 기본 합계 계정에 투자원가가 없어 계산하지 않는다.
- 수치 분석가 prompt는 외부 사실을 쓰지 않는다. 정상 설명은 일반적 가능성으로만 작성해야 한다.
- 외부 업황·뉴스 맥락은 L4 `external` 관점으로 교차에 참여한다. 쿼리 생성과 외부 평가는
  `gemini_external_model == "gemini-3.1-pro-preview"`를 사용하고, 내부 4관점은
  `gemini_model == "gemini-2.5-flash"`를 유지한다. 쿼리 생성은 내부 데이터 기반으로 하되,
  외부 평가는 검색 결과와 출처만 입력받는다. 출처 없는 외부 주장은 버리고 Finding 판단
  필드는 변경하지 않는다. 외부 맥락은 설명용이며 면죄부가 아니다.
- 동종업계 비교는 L4 `industry` 관점으로 교차에 참여한다. 피어는 DART `induty_code == 264`
  config 피어의 재무지표 baseline만 계산하며, 주석·외부·5축 분석을 피어에 적용하지 않는다.
  삼성전자는 사업 다각화 기업이라 단순 업종 비교 한계를 항상 명시한다.
- L4 종합 문단은 결정론 큐와 지표 요약에만 grounding한다. live 호출 실패 시 문단만 보류하고
  결정론 큐는 유지한다.
- L4 관점 LLM은 독립 입력을 받는다. 수치 관점은 queue/ratio, 주석 관점은
  `note_mappings.yaml`의 8개 카테고리 note section material, 흐름 관점은
  BS-IS-CF/활동성·이익의 질 material, 변동 관점은
  전기 대비 변동 material을 받는다. 외부 관점은 내부 데이터로 검색어만 생성하고, 평가는
  Google Search grounded ContextBrief만 받는다. 서로의 결론은 입력으로 받지 않는다.
- 감사기준·K-IFRS 근거는 검토 관점의 출처다. Finding은 부정·분식 확정 표현으로 쓰지 않는다.
- 실무 재무지표도 검토 관점이다. 출처 없는 계산식은 플레이북에 넣지 않고, 계정 부족 지표는
  `mvp1_status: account_missing`으로 표시한다. 현재 ROI만 계정 부족으로 남아 있다.
- 공개 KSA 원문별 링크는 확인하지 못한 항목이 있어 [AUDIT_BASIS.md](AUDIT_BASIS.md)에
  “KSA 원문 미검증”으로 표시했다. ISA/IFRS 제목과 요지는 공식 IAASB/IFRS 출처로 확인했다.
- 메인 LLM 모델 기본값은 `config.settings.gemini_model == "gemini-2.5-flash"`다.
  외부 관점 query/eval 모델은 `config.settings.gemini_external_model == "gemini-3.1-pro-preview"`다.
  Gemini fallback은 `gemini_fallback_model` 설정이 비어 있으면 비활성이다. OpenAI fallback은
  사용하지 않는다.
- 2025 CFS는 IS·CF 계정 확장 후 Medium 관계 red flag가 여럿 있다. 대표 신호는
  사업결합순현금유출 YoY 2102.89%, 장기차입금차입 YoY 593.17%, 자기주식취득 YoY 552.00%,
  운전자본변동 YoY -513.31%, 재무활동CF vs 장기차입금 괴리 -137.49pp다.

## 진입 포인트

- 전체 흐름 → [OVERVIEW.md](OVERVIEW.md) → 상세 [PLAN.md](PLAN.md)
- Codex 작업 지침 → [../../AGENTS.md](../../AGENTS.md) → [CODEX.md](CODEX.md)
- 할 일 → [ROADMAP.md](ROADMAP.md) · 결정·이유 → [DECISION.md](DECISION.md)
- L1 측정 → [NORMALIZE_REPORT.md](NORMALIZE_REPORT.md)
- L2 계산 → [SIGNAL_REPORT.md](SIGNAL_REPORT.md)
- 첫 Finding → [FINDING_REPORT.md](FINDING_REPORT.md)
- 문제 기록(사람용) → [../user/TROUBLESHOOT.md](../user/TROUBLESHOOT.md)
