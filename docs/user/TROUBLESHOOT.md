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
