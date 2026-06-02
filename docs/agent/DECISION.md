# DECISION — ADR 로그

> 아키텍처·정책 결정 기록. 설계 맥락·근거 상세는 [PLAN.md](PLAN.md).

## D1. LLM의 SQL 자유도 → tool DSL 확정

- **결정**: 자유 SQL 미채택. LLM은 안전한 분석 함수(tool DSL)만 호출.
- **이유**: 자유 SQL은 화이트리스트 검증·재현성·에러처리 부담이 크고 설명력이 낮다.
  함수명(`compare_growth` 등)이 분석 근거로 그대로 남는다.
- **영향**: tool DSL은 `src/analysis_tools/`에 격리. (PLAN §8)

## D2. 오케스트레이션 → 순수 Python async + PydanticAI 확정

- **결정**: 별도 프레임워크(LangGraph) 미채택.
- **이유**: #1 ADR-1 경험(LangGraph → PydanticAI 통일). L3 교차검증이 고정 순서 1회
  (수치→주석→흐름→변동→반박)라 상태그래프 불필요.
- **재검토**: 다회 토론(debate-until-consensus)이 필요해지면 LangGraph (PLAN §16).

## D3. 동종업계 비교 → MVP는 단일회사 시계열 확정

- **결정**: 업종 벤치마크 풀 미채택(MVP). materiality baseline을 추상화해 확장 인터페이스만 확보.
- **이유**: 업종 풀은 L1 정규화 부담(최대 난관)을 N배로 키워 MVP를 침몰시킨다.
- **재검토**: 소수 피어 2~3개사 수동 지정 → 업종 벤치마크 순으로 확장 (PLAN §16).

## D4. 공시 변동 → 독립 에이전트(④) 승격 확정

- **결정**: 분석축 통합이 아니라 5번째 역할 에이전트로 승격.
- **이유**: 제품 컨셉(Disclosure Change)을 1급으로 전면화. 원칙2가 금지한 것은
  "데이터 차원(계정)의 에이전트화"이지 "역할 추가"가 아니므로 위반이 아니다.
- **재발 방지**: 에이전트 추가 게이트 명문화 + 역할을 직교 5차원 닫힌 집합으로 고정 +
  변동 에이전트도 계정-agnostic + 흐름(공간축)/변동(시간축) 직교로 경계 분리.
  (PLAN §3 원칙2, §5)

## D5. L1 canonical 매핑 → account_id 1순위 + label alias 보조 확정

- **결정**: canonical 매핑은 `account_id` 표준 ID를 1순위로 사용하고, 표준 ID가 없거나
  MVP1 계정에서 누락될 때만 한글 라벨 alias를 2순위로 사용한다.
- **초기 측정**: 삼성전자 2022~2024 CFS/OFS에서 MVP1 10개 계정은 모든 연도·구분에 1건씩
  같은 canonical로 연결됐다. 각 연도·구분마다 9건은 `exact_taxonomy_match`, 1건은
  `label_alias_match`였다. 2022 CFS의 표준계정코드 미사용 51행 중 MVP1 alias로 구제된
  행은 1건(1.96%)이다.
- **결론**: MVP1 범위에서는 Arelle/원본 XBRL taxonomy 파싱 없이 `finstate_all`의
  `account_id`와 라벨 alias만으로 L2 입력을 만들 수 있다. 단, `매입채무`(2022)와
  `단기차입금`(2023~2025)은 `account_id == "-표준계정코드 미사용-"`이므로 라벨 보조가
  필수다.
- **영향**: 미매핑 행은 제외하지 않고 `기타 중요 계정` + `unmapped_extension_account`로
  보존한다. MVP1 밖 계정까지 확장할 때 매핑률이 부족하면 alias 보강 또는 Arelle 투입을
  재검토한다. 상세 수치는 [NORMALIZE_REPORT.md](NORMALIZE_REPORT.md).
- **2025 갱신**: 삼성전자 2025 CFS/OFS에서도 MVP 계정은 모두 1건씩 매핑됐다.
  `단기차입금`은 2025에도 label alias 보조가 필요했다.

## D6. 첫 수치 분석가 LLM → Gemini family 단일 + OpenAI 미사용

- **결정**: 첫 Finding 수치 분석가는 PydanticAI + `google-genai` + 설정의
  `gemini_model`만 사용한다. OpenAI 모델은 사용하지 않는다.
- **이유**: 이번 단계의 산술·판정은 이미 L2 결정론 코드가 수행한다. LLM은 계산 능력이 아니라
  구조화된 설명, 반대 가능성, 정상일 수 있는 일반적 설명, 확인 질문 생성에만 쓴다.
- **환각 방어**: 입력은 L2 신호와 EvidenceRef로 제한한다. 외부 뉴스·업황·특정 사건을
  단정하지 못하게 system prompt와 result validator를 둔다. 빈 근거 또는 confirm_question
  누락은 재시도한다.
- **재검토**: 더 무거운 회계 추론이 필요해질 때 Gemini family 내 승급을 검토한다. 단,
  숫자 계산은 계속 코드가 담당한다. 현재 모델 전환은 D10을 따른다.

## D7. 반박 에이전트(⑤) 보류 — 반박 기능을 스키마·기준선·가드에 내재화

- **결정**: 별도 반박 에이전트를 지금 만들지 않는다. PLAN의 5개 역할 중 ⑤ 반박은 보류하고,
  역할 에이전트는 수치·주석·흐름·변동 4개로 본다(반박은 내재화).
- **이유**: 반박의 목적(과잉지적 방지·근거 검증)이 이미 세 곳에 분산 내재화돼 있다.
  1. 신호 추출 단계의 결정론 threshold가 약한 신호를 사전 차단
  2. 각 에이전트의 자기검열 — grounding 강제 + 확정·외부사실 표현 차단 guardrail
  3. Finding 스키마의 counter_evidence / normal_explanation / confirm_question(자기반박 강제)
  → 별도 반박가는 중복이며 현 구조에서 한계효용이 작다.
- **무한 반복 우려 해소**: 1회 검증 구조(D2, 다회 토론 미채택)이므로 반박-재반박 핑퐁
  무한루프는 발생하지 않는다.
- **재검토**: Finding이 수십 건으로 늘고 자유도가 커지면 "최종 1회 검증 게이트"로 가볍게
  재도입을 검토한다.

## D8. 외부 맥락 → 출처 기반 참고용 ContextBrief로 분리

- **결정**: Google Search grounding으로 수집한 외부 업황·뉴스 맥락은 `ContextBrief`로
  Finding과 분리한다. 각 항목은 `claim`, `source_title`, `source_url`을 포함해야 하며,
  grounding 결과 URL과 매칭되지 않는 항목은 버린다.
- **이유**: 외부 정보는 회수가능성·업황을 이해하는 참고 자료일 수 있지만, 프로젝트의
  판단 근거는 L1/L2 재무 데이터와 주석 EvidenceRef다. 외부 뉴스가 `risk_level`,
  `issue_type`, `materiality_score`, `anomaly_score`를 오염시키면 PLAN §3 원칙4와
  §15 포지셔닝을 위반한다.
- **영향**: 외부 맥락은 `src/agents/context_brief.py`와 `src/schemas/context.py`에 격리한다.
  Finding 생성 결과에는 별도 `context_brief` 키로 붙이며, Finding 객체는 변경하지 않는다.
  출처가 없거나 grounding URL과 매칭되지 않는 외부 주장은 표시하지 않는다.

## D9. L4 통합 → 멀티에이전트 독립 평가 + 교차 판정으로 확정

- **결정**: L4는 한 LLM이 모든 재료를 단순 요약하는 방식이 아니라, 수치 관점과 주석 관점이
  독립적으로 회사 전체를 평가한 뒤 별도 결정론 단계가 일치/충돌을 판정하는 구조로 확정한다.
- **이유**: 프로젝트 정체성은 여러 관점이 각자 보고 교차검증하는 Disclosure Review Agent다.
  단일 종합 LLM은 관점 간 독립성을 잃고, 주석이 잠잠한데 숫자만 위험한 상황 같은 충돌을
  명시적으로 드러내기 어렵다.
- **영향**: `src/report/perspectives.py`는 관점별 LLM 평가만 담당하고, 서로의 출력을 입력으로
  받지 않는다. `src/report/crosscheck.py`는 risk_area 일치/충돌을 결정론으로 판정한다.
  일부 관점이 503 등으로 실패해도 결정론 review queue는 유지하고, 완료된 관점만으로 교차를
  수행한다.
- **재검토**: 흐름·변동 관점이 준비되면 동일한 인터페이스로 관점을 추가한다. 관점 추가는
  데이터 차원의 에이전트 증식이 아니라 PLAN §5의 역할 차원 확장으로 제한한다.

## D10. 메인 Gemini 모델 → `gemini-2.5-flash`로 전환

- **결정**: 메인 LLM 모델 기본값을 `gemini-3.5-flash`에서 `gemini-2.5-flash`로 변경한다.
  모델명은 `config.settings.gemini_model` 한 곳에서 관리하고, `src.agents.gemini_retry.MODEL_NAME`은
  그 설정을 참조한다.
- **이유**: 개발 기간 동안 `gemini-3.5-flash`가 반복적으로 503 `UNAVAILABLE` high demand를
  반환해 L4 live 멀티에이전트 평가를 검증하지 못했다. 사용자가 Gemini family 내 전환을
  결정했다.
- **영향**: 기존 503 재시도 정책(최대 5회, 지수 백오프+jitter)은 유지한다. OpenAI fallback은
  계속 사용하지 않으며, 선택 fallback도 Gemini family로만 제한한다.
- **검증**: `gemini-2.5-flash`로 L4 수치·주석·흐름·변동 4관점 live 평가를 완료했다.

## D11. 외부 맥락 → L4 5번째 관점으로 승격

- **결정**: D8의 `ContextBrief`를 L4의 5번째 독립 관점(`external`)으로 승격한다. 외부 관점은
  Google Search grounding으로 회사·연도·상위 검토 항목 관련 맥락을 수집하고,
  출처가 확인된 항목만 `PerspectiveAssessment.evidence`에 남긴다.
- **이유**: 외부 뉴스·업황은 ISA/KSA 520 분석적 절차의 외부 정보 비교에 해당하는 보조
  관점이다. 내부 수치·주석·흐름·변동 신호와 독립적으로 확인하면, 내부 신호가 업황 맥락과
  같은 방향인지 또는 회사 고유 가능성인지 구분해 볼 수 있다.
- **비오염 원칙**: 외부 관점은 `risk_level`, `issue_type`, `materiality_score`,
  `anomaly_score` 같은 내부 판단 필드를 변경하지 않는다. 외부 맥락은 설명용이며 면죄부가
  아니다. 외부가 잠잠해도 내부 위험은 지우지 않고, 교차 판정에서 "회사 고유 가능성"으로
  표시한다.
- **영향**: L4 관점은 수치·주석·흐름·변동·외부 5축이다. 외부 grounding 실패 또는 503은
  외부 관점만 deferred로 두고 내부 4관점 교차와 결정론 큐는 유지한다.
