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
- **측정**: 삼성전자 2022~2024 CFS/OFS에서 MVP1 10개 계정은 모든 연도·구분에 1건씩
  같은 canonical로 연결됐다. 각 연도·구분마다 9건은 `exact_taxonomy_match`, 1건은
  `label_alias_match`였다. 2022 CFS의 표준계정코드 미사용 51행 중 MVP1 alias로 구제된
  행은 1건(1.96%)이다.
- **결론**: MVP1 범위에서는 Arelle/원본 XBRL taxonomy 파싱 없이 `finstate_all`의
  `account_id`와 라벨 alias만으로 L2 입력을 만들 수 있다. 단, `매입채무`(2022)와
  `단기차입금`(2023~2024)은 `account_id == "-표준계정코드 미사용-"`이므로 라벨 보조가
  필수다.
- **영향**: 미매핑 행은 제외하지 않고 `기타 중요 계정` + `unmapped_extension_account`로
  보존한다. MVP1 밖 계정까지 확장할 때 매핑률이 부족하면 alias 보강 또는 Arelle 투입을
  재검토한다. 상세 수치는 [NORMALIZE_REPORT.md](NORMALIZE_REPORT.md).
