# FINDING_REPORT — 첫 Finding 리포트 실행 기록

> 범위: 삼성전자(`00126380`) 2023 CFS, MVP1 숫자 신호.
> 상태: 결정론 신호 추출 완료, Gemini 3.5 Flash live Finding 생성 완료.

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

`GOOGLE_API_KEY`는 설정상 존재했다. 최초 실행에서는 Google API 503이 발생했으나,
`src.agents.numeric_analyst`에 503/UNAVAILABLE 일시 오류 자동 재시도를 추가한 뒤
`uv run python -m src.agents.first_finding` 재실행이 성공했다.

검증:

```powershell
uv run python -m pytest -q
# 18 passed

uv run ruff check .
# All checks passed!
```

OpenAI fallback은 사용하지 않았다. `gemini_fallback_model` 설정은 기본 빈 값이라 비활성이고,
설정하더라도 `gemini-` prefix 모델만 허용한다.

## 4. 생성된 Finding

```json
{
  "account": "매출채권",
  "issue_type": "receivables_quality",
  "materiality_score": 80.0,
  "anomaly_score": 75.0,
  "confidence": "High",
  "numeric_evidence": [
    {
      "source": "financial_statement",
      "locator": "매출",
      "year": "2023",
      "value": "YoY -14.33%"
    },
    {
      "source": "financial_statement",
      "locator": "매출채권",
      "year": "2023",
      "value": "YoY 2.59%"
    },
    {
      "source": "financial_statement",
      "locator": "revenue-vs-receivable",
      "year": "2023",
      "value": "divergence -16.92pp"
    },
    {
      "source": "financial_statement",
      "locator": "매출",
      "year": "2023",
      "value": "direction decrease"
    },
    {
      "source": "financial_statement",
      "locator": "매출채권",
      "year": "2023",
      "value": "direction increase"
    }
  ],
  "note_evidence": [],
  "flow_evidence": [
    {
      "source": "financial_statement",
      "locator": "매출채권",
      "year": "2023",
      "value": "direction increase"
    },
    {
      "source": "cash_flow",
      "locator": "영업활동현금흐름",
      "year": "2023",
      "value": "direction decrease"
    }
  ],
  "counter_evidence": [
    "매출채권의 절대적인 증가율 자체는 YoY 2.59% 수준으로 급격한 팽창으로 보기는 어려울 수 있음"
  ],
  "normal_explanation": [
    "기말 시점에 매출이 집중되는 계절적 요인으로 인해 일시적으로 매출채권 잔액이 증가했을 가능성",
    "정상적인 영업 정책의 일환으로 우량 거래처에 대한 신용 공여 기간이 연장되었을 가능성"
  ],
  "confirm_question": [
    "기말 매출채권 연령 분석(Aging Analysis)에서 장기 연체 채권의 비중이 전년 대비 증가하였습니까?",
    "대손충당금 설정 정책 및 대손충당금 설정률이 매출채권 증가 속도에 맞추어 보수적으로 조정되었습니까?"
  ],
  "next_procedure": [
    "매출채권 연령 분석표를 검토하여 장기 미회수 채권의 대손충당금 설정 적정성을 평가한다.",
    "보고기간 후 수금 내역(Subsequent Receipt)을 확인하여 기말 매출채권의 실제 회수 여부를 검증한다.",
    "주요 거래처별 신용 한도 및 신용 정책의 변경 여부를 파악한다."
  ],
  "risk_level": "Medium"
}
```

## 5. 외부 ContextBrief

외부 업황·뉴스 맥락은 Finding 판단과 분리된 `ContextBrief`로만 제시한다. `ContextBrief`
항목은 `claim`, `source_title`, `source_url`을 포함해야 하며, Gemini Google Search
grounding 결과 URL과 매칭되지 않으면 버린다. 외부 맥락은 `risk_level`, `issue_type`,
`materiality_score`, `anomaly_score`를 변경하지 않는다.

실행 진입점:

```powershell
uv run python -m src.agents.first_context_brief
```

2026-06-02 live 실행은 `gemini-3.5-flash` 503 high demand로 보류했다. 따라서 현재
실제 수집된 외부 맥락 항목은 없다.

## 6. 재실행 방법

같은 범위의 첫 Finding은 아래 명령으로 재실행한다.

```powershell
uv run python -m src.agents.first_finding
```

출력은 `signals`와 `finding` JSON이다. `finding`은 `AccountFinding` 스키마를 따라야 하며,
`numeric_evidence` 또는 `flow_evidence`가 비어 있으면 result validator가 재시도한다.
