# INTEGRATED_REPORT — L4 멀티에이전트 통합 리포트

> 대상: 삼성전자 `00126380`, 연결(CFS), 2022~2024. 이 리포트는 공시 재무제표와 주석 기반
> 검토 후보 큐이며 부정·분식 확정 근거가 아니다.

## 1. 입력과 구조

- 계정 Finding: [FINDING_REPORT.md](FINDING_REPORT.md)의 매출채권 `AccountFinding`
- 관계사슬 신호: [SIGNAL_REPORT.md](SIGNAL_REPORT.md), `src.signals.red_flags`
- 실무 재무지표: [RATIO_REPORT.md](RATIO_REPORT.md), `config/playbooks/financial_ratios.yaml`
- 근거 체계: [AUDIT_BASIS.md](AUDIT_BASIS.md)
- 독립 관점: 수치 관점, 주석 관점
- 교차 판정: 독립 관점의 `risk_area` 일치/충돌을 결정론으로 판정

정렬은 `risk_level` 순서(`High > Medium > Low`)와 `materiality_score`로 수행한다.
severity 텍스트를 직접 합산하지 않는다.

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

2026-06-02 live 실행에서 `gemini-3.5-flash`가 두 관점 모두 503 `UNAVAILABLE`을 반환했다.
따라서 관점별 LLM 평가는 보류했다. 각 관점은 서로의 출력을 보지 않도록 별도 material board를
받는다.

| 관점 | 상태 | risk | 평가 |
|---|---|---|---|
| numeric | deferred | Low | Gemini temporary error after 1 attempts for gemini-3.5-flash: 503 UNAVAILABLE |
| note | deferred | Low | Gemini temporary error after 1 attempts for gemini-3.5-flash: 503 UNAVAILABLE |

## 5. 일치/충돌

| verdict | risk_area | comment |
|---|---|---|
| insufficient | 관점 평가 | 완료된 독립 관점이 2개 미만이라 일치/충돌 판정은 보류한다. |

## 6. 한 단락 종합

LLM 종합 문단은 보류했다. 결정론 검토 큐와 지표 요약은 완료 상태다.

## 7. 실행

```powershell
uv run python -m src.report.multi_agent
```

LLM을 생략하고 결정론 큐와 deferred 관점 구조만 확인하려면 다음을 실행한다.

```powershell
uv run python -m src.report.multi_agent --no-llm
```
