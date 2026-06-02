# INTEGRATED_REPORT — L4 멀티에이전트 통합 리포트

> 대상: 삼성전자 `00126380`, 연결(CFS), 2022~2024. 이 리포트는 공시 재무제표와 주석 기반
> 검토 후보 큐이며 부정·분식 확정 근거가 아니다.

## 1. 입력과 구조

- 계정 Finding: [FINDING_REPORT.md](FINDING_REPORT.md)의 매출채권 `AccountFinding`
- 관계사슬 신호: [SIGNAL_REPORT.md](SIGNAL_REPORT.md), `src.signals.red_flags`
- 실무 재무지표: [RATIO_REPORT.md](RATIO_REPORT.md), `config/playbooks/financial_ratios.yaml`
- 근거 체계: [AUDIT_BASIS.md](AUDIT_BASIS.md)
- 독립 관점: 수치 관점, 주석 관점, 흐름 관점, 변동 관점, 외부 관점
- 교차 판정: 독립 관점의 `risk_area`와 요약 내 계정 언급을 정규화해 일치/충돌을 결정론으로 판정

외부 관점은 Google Search grounding 결과 중 출처 URL이 확인된 항목만 사용한다. 외부 맥락은
설명용이며 내부 위험을 약화하거나 면죄하지 않는다.

## 2. 검토 우선순위 큐

| 순위 | 대상 | 유형 | risk | score | 핵심 근거 | 근거 | 출처 |
|---:|---|---|---|---:|---|---|---|
| 1 | 단기금융상품 | relationship_signal | Medium | 159.62 | single_account_yoy: 159.62 | ISA/KSA 315, ISA/KSA 520 | - |
| 2 | 단기차입금 | relationship_signal | Medium | 85.15 | single_account_yoy: 85.15 | ISA/KSA 315, ISA/KSA 520 | - |
| 3 | 매출채권 | account_finding | Medium | 80.00 | YoY -14.33% | ISA/KSA 315, ISA/KSA 500, ISA/KSA 520 | - |
| 4 | 영업활동현금흐름 | relationship_signal | Medium | 65.35 | single_account_yoy: 65.35 | ISA/KSA 315, ISA/KSA 520 | - |
| 5 | 단기금융상품 | relationship_signal | Medium | 65.15 | single_account_yoy: -65.15 | ISA/KSA 315, ISA/KSA 520 | - |
| 6 | 매출채권 | relationship_signal | Medium | 16.92 | growth_divergence: -16.92 | ISA/KSA 315, ISA/KSA 520 | - |
| 7 | 재고자산 | relationship_signal | Medium | 15.95 | growth_divergence: 15.95 | ISA/KSA 315, ISA/KSA 520 | - |
| 8 | DIO | financial_ratio | Low | 101.13 | 2024: 101.13 | ISA/KSA 501, ISA/KSA 520, K-IFRS 1002 | https://corporatefinanceinstitute.com/resources/accounting/days-inventory-outstanding-dio/ |
| 9 | DSO | financial_ratio | Low | 48.69 | 2024: 48.69 | ISA/KSA 520, K-IFRS 1109, K-IFRS 1107 | https://corporatefinanceinstitute.com/resources/accounting/days-sales-outstanding/ |
| 10 | 매출총이익률 | financial_ratio | Low | 37.99 | 2024: 37.99 | ISA/KSA 520, K-IFRS 1115, K-IFRS 1002 | https://corporatefinanceinstitute.com/resources/accounting/profitability-ratios/ |

## 3. 회사 전체 지표 요약

- 수익성: ROE 9.00, ROA 7.10, 매출총이익률 37.99, 영업이익률 10.88
- 활동성: 매출채권회전율 7.50, DSO 48.69, 재고회전율 3.61, DIO 101.13, 총자산회전율 0.62
- 안정성: 부채비율 27.93, 유동비율 2.43, 이자보상배율 2.52
- 이익의 질: 영업CF/순이익 2.12, 발생액 비율 -7.94

## 4. 관점별 독립 평가

2026-06-02 live 실행에서 `gemini-2.5-flash`로 5관점 모두 completed가 나왔다. 각 관점은 서로의
출력을 보지 않고 별도 material board만 받았다.

| 관점 | 상태 | risk | 평가 | 출처 |
|---|---|---|---|---|
| numeric | completed | Medium | 단기금융상품, 단기차입금, 영업활동현금흐름에서 전년 대비 변동폭이 기준을 초과했다. 매출채권 품질 저하와 매출 대비 매출채권·재고자산 성장률 괴리가 관찰됐다. | - |
| note | completed | High | 매출채권 및 미수금 규모 증가, 대손상각(환입) 증가 추세, 재고자산 평가손실 키워드가 확인되어 채권 회수 가능성과 평가손실 검토가 필요하다. | D82242/D82638 주석 발췌 |
| flow | completed | Medium | 매출채권 변동, 매출과 매출채권 증가율 괴리, 매출채권과 영업활동현금흐름 방향 불일치, 재고자산 증가율 괴리가 흐름 관점 검토 후보로 묶였다. | - |
| change | completed | Medium | 단기금융상품, 단기차입금, 영업활동현금흐름의 전년 대비 기준 초과 변동과 매출 대비 매출채권·재고자산 괴리를 변동 리스크로 보았다. | - |
| external | completed | Low | 출처가 확인된 관련 외부 맥락 없음. 내부 위험은 그대로 유지한다. | - |

## 5. 일치/충돌

| verdict | risk_area | perspectives | comment |
|---|---|---|---|
| conflict | 단기금융상품 | numeric, note, flow, change, external | 단기금융상품은 내부 위험이나 외부 맥락은 잠잠해 회사 고유 가능성으로 주목한다. |

## 6. 한 단락 종합

종합적인 재무제표 검토 결과, 여러 핵심 계정에서 유의미한 변동과 잠재적 위험 징후가 식별됐다.
단기금융상품은 전년 대비 절대값 기준 159.62% 및 -65.15%의 변동을 보였고, 단기차입금 85.15%와
영업활동현금흐름 65.35%도 기준치를 초과했다. 매출채권은 전년 대비 -14.33% 감소했고,
매출과 매출채권 증가율 간 괴리(-16.92)가 확인됐다. 주석 관점에서는 매출채권 및 미수금 규모,
대손상각(환입), 재고자산 평가손실 키워드가 확인되어 채권 회수 가능성과 재고 평가에 대한
추가 검토가 필요할 수 있다. 외부 관점은 출처가 확인된 관련 외부 맥락을 찾지 못했으므로,
내부에서 식별된 단기금융상품 변동은 외부 업황으로 설명하지 않고 회사 고유 가능성으로 주목한다.

## 7. 실행

```powershell
uv run python -m src.report.multi_agent
```

LLM을 생략하고 결정론 큐와 deferred 관점 구조만 확인하려면 다음을 실행한다.

```powershell
uv run python -m src.report.multi_agent --no-llm
```
