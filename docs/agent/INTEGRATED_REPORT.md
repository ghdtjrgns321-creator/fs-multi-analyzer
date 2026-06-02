# INTEGRATED_REPORT — L4 멀티에이전트 통합 리포트

> 대상: 삼성전자 `00126380`, 연결(CFS), 2022~2025. 이 리포트는 공시 재무제표와 주석 기반
> 검토 후보 큐이며 부정·분식 확정 근거가 아니다.

## 1. 입력과 구조

- 계정 Finding: 최신 연도와 근거 연도가 맞는 항목만 큐에 반영한다.
- 관계사슬 신호: [SIGNAL_REPORT.md](SIGNAL_REPORT.md), `src.signals.red_flags`
- 실무 재무지표: [RATIO_REPORT.md](RATIO_REPORT.md), `config/playbooks/financial_ratios.yaml`
- 근거 체계: [AUDIT_BASIS.md](AUDIT_BASIS.md)
- 독립 관점: 수치 관점, 주석 관점, 흐름 관점, 변동 관점, 외부 관점
- 교차 판정: 독립 관점의 `risk_area`와 요약 내 계정 언급을 정규화해 일치/충돌을 결정론으로 판정

외부 관점은 LLM이 내부 분석에서 검색어를 생성한 뒤 Google Search grounding 결과 중 출처
URL이 확인된 항목만 사용한다. 외부 맥락은 설명용이며 내부 위험을 약화하거나 면죄하지 않는다.

## 2. 2025 검토 우선순위 큐

2025 CFS는 현재 threshold 기준 중위험 관계 신호가 없어서 최신 큐가 Low 지표 중심으로 구성됐다.

| 순위 | 대상 | 유형 | risk | score | 핵심 근거 | 근거 | 출처 |
|---:|---|---|---|---:|---|---|---|
| 1 | DIO | financial_ratio | Low | 94.20 | 2025: 94.20 | ISA/KSA 501, ISA/KSA 520, K-IFRS 1002 | https://corporatefinanceinstitute.com/resources/accounting/days-inventory-outstanding-dio/ |
| 2 | DSO | financial_ratio | Low | 51.83 | 2025: 51.83 | ISA/KSA 520, K-IFRS 1109, K-IFRS 1107 | https://corporatefinanceinstitute.com/resources/accounting/days-sales-outstanding/ |
| 3 | 매출총이익률 | financial_ratio | Low | 39.38 | 2025: 39.38 | ISA/KSA 520, K-IFRS 1115, K-IFRS 1002 | https://corporatefinanceinstitute.com/resources/accounting/profitability-ratios/ |
| 4 | 부채비율 | financial_ratio | Low | 29.94 | 2025: 29.94 | ISA/KSA 520, ISA/KSA 570 | https://corporatefinanceinstitute.com/resources/knowledge/finance/debt-to-equity-ratio-formula/ |
| 5 | 영업이익률 | financial_ratio | Low | 13.07 | 2025: 13.07 | ISA/KSA 520 | https://corporatefinanceinstitute.com/resources/accounting/operating-profit-margin/ |
| 6 | ROE | financial_ratio | Low | 10.78 | 2025: 10.78 | ISA/KSA 520 | https://corporatefinanceinstitute.com/resources/accounting/what-is-return-on-equity-roe/ |
| 7 | ROA | financial_ratio | Low | 8.36 | 2025: 8.36 | ISA/KSA 520 | https://corporatefinanceinstitute.com/resources/accounting/return-on-assets-roa-formula/ |
| 8 | 발생액 비율 | financial_ratio | Low | 7.42 | 2025: -7.42 | ISA/KSA 520, K-IFRS 1007 | https://www.stockopedia.com/ratios/accrual-ratio-555/ |
| 9 | 매출채권회전율 | financial_ratio | Low | 7.04 | 2025: 7.04 | ISA/KSA 520, K-IFRS 1109, K-IFRS 1107 | https://corporatefinanceinstitute.com/resources/financial-modeling/accounts-receivable-turnover-ratio-template/ |
| 10 | 재고회전율 | financial_ratio | Low | 3.87 | 2025: 3.87 | ISA/KSA 501, ISA/KSA 520, K-IFRS 1002 | https://corporatefinanceinstitute.com/resources/accounting/inventory-turnover-ratio/ |

## 3. 회사 전체 지표 요약

- 수익성: ROE 10.78, ROA 8.36, 매출총이익률 39.38, 영업이익률 13.07
- 활동성: 매출채권회전율 7.04, DSO 51.83, 재고회전율 3.87, DIO 94.20, 총자산회전율 0.62
- 안정성: 부채비율 29.94, 유동비율 2.33, 이자보상배율 3.72
- 이익의 질: 영업CF/순이익 1.89, 발생액 비율 -7.42

## 4. 2024→2025 신호 스냅샷

- 매출 YoY 10.88%, 매출채권 YoY 17.20%, 괴리 -6.32pp
- 매출 YoY 10.88%, 재고자산 YoY 1.70%, 괴리 9.18pp
- 매출원가 YoY 8.40%, 재고자산 YoY 1.70%, 괴리 6.70pp
- 단기차입금 YoY 33.42%, 영업활동현금흐름 YoY 16.90%

## 5. 관점별 독립 평가

2026-06-03 live 실행에서 `gemini-2.5-flash`로 5관점 모두 completed가 나왔다. 각 관점은 서로의
출력을 보지 않고 별도 material board만 받았다.

| 관점 | 상태 | risk | 평가 | 출처 |
|---|---|---|---|---|
| numeric | completed | Medium | 2025년 활동성 지표와 매출채권 증가율이 매출 증가율을 상회하는 점, 단기차입금 증가가 추가 검토 필요성을 시사한다고 보았다. | 2025 ratio/signals |
| note | completed | High | 2025년 금융자산 관련 대손상각(환입) 금액이 2024년 대비 크게 증가해 채권 손상 관련 검토가 필요하다고 보았다. | D82242/D82638 주석 발췌 |
| flow | completed | Medium | 매출채권 증가율이 매출 증가율을 상회하고, 단기차입금 증가와 OFS 현금및현금성자산 증가도 추가 확인 대상으로 보았다. | 2025 signal snapshot |
| change | completed | High | 매출 대비 매출채권 증가율, 현금흐름 부담 가능성, 재고자산 관리를 전기 대비 변화 관점 검토 후보로 보았다. | 2024→2025 signal snapshot |
| external | completed | Low | 외부 자료에서는 부채비율이 낮은 수준이고 2025년 상반기 단기차입금이 전년 말 대비 감소했다는 맥락이 확인됐다. 내부 매출채권·활동성 위험을 면죄하지 않는다. | Samsung, GSIFN, Digital Today |

외부 관점 생성 검색어:

1. `삼성전자 2025 DIO DSO 재고자산 매출채권`
2. `삼성전자 2025 매출총이익률 영업이익률`
3. `삼성전자 2025 부채비율 유동부채 단기차입금`

외부 관점 출처:

- samsung.com: https://vertexaisearch.cloud.google.com/grounding-api-redirect/AUZIYQEWJSSj8vG_0y1aZZg3QyuX8Xol8Oev8QdRipa8EJTIsgcRm2Nng1cD7ZhCzyaEJsbfVYwmRR2YUtNXp2c984NzQlxAG8aGTTWeGNegpVHza5ad7II-8BrHKPBCwfDe4oY9NuXbjtfXOjq5nTed-iVRgVJxt-6Jk1eUGFbq7Da1KakiKtB4dWPhor70
- gsifn.io: https://vertexaisearch.cloud.google.com/grounding-api-redirect/AUZIYQGN6Iq8af4XMYQfIUt3aGWPFRzn5n248btv3t6DYoBFJVRosjggM1S9Y9scJms81bFbnYPQ5rH4Wrc0xMEbC3F3ZhglATMZVrVtTXHqjlaSMP3dD_W_N0CgyctF72YgZfE1vO4zTA==
- digitaltoday.co.kr: https://vertexaisearch.cloud.google.com/grounding-api-redirect/AUZIYQFzGFbg-JWnk_2R_QTGfTukIhzHcUhCPVk8Ezyxu_ildaq2Lz0NsLC62oN-xTRv-2onEPllc3t7yO6EOnazaMewxkdIXTWuhL9UvW_tIYl-z2Is-_e8XUG5jJhomcqbC5FHn0pVgiq9f0ip_6Hf-t0yNhtJmeavljNJQOXV

## 6. 일치/충돌

| verdict | risk_area | perspectives | comment |
|---|---|---|---|
| conflict | 매출채권 관리 및 현금 회수 | numeric, note, flow, change, external | 매출채권 관리 및 현금 회수는 내부 위험이나 외부 맥락은 잠잠해 회사 고유 가능성으로 주목한다. |

## 7. 한 단락 종합

2025년 최신 기준에서는 threshold를 넘는 중위험 관계 신호는 없지만, 활동성 지표와 2024→2025
신호 스냅샷에서 추가 검토 후보가 남아 있다. DSO는 48.69일에서 51.83일로 늘었고, 매출채권
YoY 17.20%가 매출 YoY 10.88%를 상회했다. 단기차입금은 33.42% 증가했고, 부채비율은
27.93%에서 29.94%로 상승했다. 주석 관점은 2025년 금융자산 관련 대손상각(환입) 증가를
채권 손상 관련 확인 대상으로 보았다. 외부 관점은 부채비율·단기차입금 관련 출처 기반
맥락을 제공했지만, 매출채권 관리 및 현금 회수 위험을 약화하지는 않는다. 따라서 내부에서
식별된 매출채권·활동성 후보는 회사 고유 가능성으로 계속 주목한다.

## 8. 실행

```powershell
uv run python -m src.report.multi_agent
```
