# TROUBLESHOOT — 문제 해결 기록 (사람용)

> 프로젝트 진행 중 만난 문제·원인·해결을 **시간순으로 누적**한다.
> 회고·포트폴리오·면접 대비용. AI 작업 상태 스냅샷은 [../agent/STATE.md](../agent/STATE.md).

## 기록 형식

```
### [YYYY-MM-DD] 제목
- 증상: 무엇이 어떻게 안 됐나
- 원인: 근본 원인 (systematic-debugging 4단계)
- 해결: 무엇을 바꿨나
- 교훈: 다음에 어떻게
```

---

## 기록

### [2026-06-02] Gemini 3.5 Flash live Finding 생성 503

- 증상: `uv run python -m src.agents.first_finding` 실행 시 두 번 모두 Google API가
  `503 UNAVAILABLE`을 반환했고 실제 `AccountFinding`이 생성되지 않았다.
- 원인: API 키와 PydanticAI 연결은 동작했지만, `gemini-3.5-flash` 모델이 high demand
  상태였다. 프로젝트 제약상 OpenAI 또는 다른 Gemini 모델로 우회할 수 없었다.
- 해결: L2 threshold 판정, PydanticAI 수치 분석가, EvidenceRef/confirm_question guardrail,
  fake LLM 테스트는 완료했다. live Finding 생성은 [../agent/FINDING_REPORT.md](../agent/FINDING_REPORT.md)에
  보류로 기록했다.
- 교훈: 모델 고정 요구가 있는 단계에서는 실패 원인을 모델 가용성으로 분리 기록하고,
  대체 모델을 임의로 쓰지 않는다. 모델이 회복되면 같은 명령을 재실행한다.

### [2026-06-02] Gemini 일시 오류 자동 재시도 추가 후 첫 Finding 생성

- 증상: `gemini-3.5-flash`의 503/UNAVAILABLE 같은 일시 오류가 발생하면 사람이 같은 명령을
  수동 재실행해야 했다.
- 원인: `src.agents.numeric_analyst`가 PydanticAI `Agent.run()`을 한 번만 호출했고,
  `ModelHTTPError(status_code=503)` 같은 일시 오류를 분류하거나 백오프하지 않았다.
- 해결: Gemini 호출부에 최대 5회 지수 백오프+jitter 재시도를 추가했다. 4xx 영구 오류는
  재시도하지 않으며, 선택 fallback은 `gemini_fallback_model` 설정으로만 켤 수 있고 Gemini
  패밀리로 제한했다. 재시도 테스트와 ruff를 통과했고, `uv run python -m src.agents.first_finding`
  재실행으로 첫 `AccountFinding`을 생성했다.
- 교훈: 라이브 모델 과부하처럼 정상 코드 바깥의 일시 장애는 호출 경계에서 정책화하고,
  fallback은 기본 비활성으로 두어 모델 고정 조건을 깨지 않는다.

### [2026-06-02] D82242 주석 분석가 live 보강 503/timeout

- 증상: 매출채권 D82242 주석 인덱서와 주석 분석가 mock 테스트는 통과했지만,
  `uv run python -m src.agents.first_note_finding` 최종 live 실행에서 Gemini 3.5 Flash가
  503을 5회 반환하거나 장시간 응답하지 않아 timeout됐다.
- 원인: 코드·키·주석 파싱은 동작했으나 모델 가용성이 불안정했다. 주석 분석가도 기존
  Gemini 재시도 정책을 사용하므로 일시 오류는 자동 재시도 후 명확한 오류로 종료된다.
- 해결: live 보강 Finding은 보류했다. 실제 D82242 인덱서는 `note:D82242:CFS:2023:2`,
  `:4`, `:5` 섹션에서 손상·대손·신용위험·연체 키워드를 추출했다.
- 교훈: LLM 보강 전 단계의 주석 인덱싱 결과를 별도 검증 가능하게 두면, 모델 과부하와
  파싱 문제를 분리해 추적할 수 있다.

### [2026-06-02] 외부 ContextBrief Google Search grounding 503

- 증상: 외부 업황·뉴스 맥락을 `ContextBrief`로 수집하는 코드는 mock 테스트를 통과했지만,
  live 실행에서 `gemini-3.5-flash`가 503 high demand를 반복 반환했다.
- 원인: 수치 Finding 재생성 단계와 ContextBrief 단독 호출 모두 모델 가용성 문제로 실패했다.
  코드 경로는 기존 Gemini 재시도 helper를 사용해 5회 재시도 후 명확한 오류로 종료했다.
- 해결: live 외부 맥락은 보류했다. 출처 없는 항목과 grounding URL과 매칭되지 않는 항목을
  버리는 검증, Finding 판단 필드 비오염 테스트는 완료했다.
- 교훈: 외부 검색 맥락은 재무 데이터 기반 판단과 분리하고, 모델 가용성 문제가 있어도
  Finding 자체가 바뀌지 않게 유지한다.
