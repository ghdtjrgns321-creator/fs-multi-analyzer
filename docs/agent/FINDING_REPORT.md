# FINDING_REPORT — 첫 Finding 리포트 실행 기록

> 범위: 삼성전자(`00126380`) 2023 CFS, MVP1 숫자 신호.
> 상태: 결정론 신호 추출 완료, Gemini 3.5 Flash live Finding 생성은 모델 503으로 보류.

## 1. 실행 범위

- 신호 판정: [../../src/signals/red_flags.py](../../src/signals/red_flags.py)
- 수치 분석가: [../../src/agents/numeric_analyst.py](../../src/agents/numeric_analyst.py)
- 실행 진입점: [../../src/agents/first_finding.py](../../src/agents/first_finding.py)
- 모델: `gemini-3.5-flash`
- OpenAI: 사용하지 않음

이번 단계는 수치 분석가 1명만 대상으로 했다. 주석·흐름·변동·반박 에이전트는 만들지 않았다.

## 2. 2023 빨간불 신호

| id | account | signal_type | metric_value | evidence |
| --- | --- | --- | --- | --- |
| `divergence:revenue-vs-receivable:2023` | 매출채권 | growth_divergence | -16.92 | 매출 YoY -14.33%, 매출채권 YoY 2.59%, divergence -16.92pp |
| `yoy:단기금융상품:2023` | 단기금융상품 | single_account_yoy | -65.15 | amount 22,690,924,000,000, YoY -65.15% |
| `direction:revenue-down-receivable-up:2023` | 매출채권 | direction_mismatch | decrease/increase | 매출 direction decrease, 매출채권 direction increase |
| `direction:receivable-up-operating-cf-down:2023` | 영업활동현금흐름 | direction_mismatch | increase/decrease | 매출채권 direction increase, 영업활동현금흐름 direction decrease |

LLM 입력에는 위 결정론 신호와 근거만 포함한다. 외부 뉴스, 업황, 특정 사건은 입력하지 않는다.

## 3. Live LLM 실행 결과

`GOOGLE_API_KEY`는 설정상 존재했다. 그러나 `uv run python -m src.agents.first_finding` 실행이
두 번 모두 Google API 503으로 실패했다.

```text
status_code: 503
model_name: gemini-3.5-flash
message: This model is currently experiencing high demand.
```

고정 조건이 `Gemini 3.5 Flash 단일`이고 OpenAI 미사용이므로 다른 모델로 우회하지 않았다.
따라서 실제 `AccountFinding`은 아직 생성되지 않았다.

## 4. 재실행 방법

모델 503이 해소되면 아래 명령을 다시 실행한다.

```powershell
uv run python -m src.agents.first_finding
```

성공 시 출력은 `signals`와 `finding` JSON이다. `finding`은 `AccountFinding` 스키마를 따라야
하며, `numeric_evidence` 또는 `flow_evidence`가 비어 있으면 result validator가 재시도한다.
