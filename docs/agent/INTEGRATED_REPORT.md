# INTEGRATED_REPORT — L4 멀티에이전트 통합 리포트

> 대상: 삼성전자 `00126380`, 연결(CFS), 2022~2025. 이 리포트는 공시 재무제표와 주석 기반
> 검토 후보 큐이며 부정·분식 확정 근거가 아니다.

## 1. 입력과 구조

- 계정 Finding: 최신 연도와 근거 연도가 맞는 항목만 큐에 반영한다.
- 관계사슬 신호: [SIGNAL_REPORT.md](SIGNAL_REPORT.md), `src.signals.red_flags`
- 실무 재무지표: [RATIO_REPORT.md](RATIO_REPORT.md), `config/playbooks/financial_ratios.yaml`
- 근거 체계: [AUDIT_BASIS.md](AUDIT_BASIS.md)
- 독립 관점: 수치 관점, 주석 관점, 흐름 관점, 변동 관점, 외부 관점, 동종업계 관점
- 교차 판정: 독립 관점의 `risk_area`와 요약 내 계정 언급을 정규화해 일치/충돌을 결정론으로 판정

외부 관점은 `gemini-3.1-pro-preview`가 내부 분석에서 검색어를 생성한 뒤 Google Search
grounding 결과 중 출처 URL이 확인된 항목만 사용한다. 외부 맥락은 설명용이며 내부 위험을
약화하거나 면죄하지 않는다.

동종업계 관점은 DART `induty_code == 264` config 피어의 재무지표 baseline만 사용한다.
피어에는 주석·외부·5축 분석을 적용하지 않는다. 삼성전자는 사업 다각화 기업이라 단순 업종코드
비교에는 한계가 있으며, 업종 비교는 ISA/KSA 520 분석적 절차의 참고 신호로만 사용한다.

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

## 5. 동종업계 baseline

피어: LG전자 `00401731`, 가온그룹 `00441304` (DART 회사개황 `induty_code == 264`).

| 지표 | 삼성전자 2025 | 피어 중앙값 | 삼성 분위 위치 | 피어 수 |
|---|---:|---:|---:|---:|
| ROE | 10.78 | 4.71 | 100.0 | 2 |
| 영업이익률 | 13.07 | 2.60 | 100.0 | 2 |
| DSO | 51.83 | 44.39 | 100.0 | 1 |
| DIO | 94.20 | 95.30 | 50.0 | 2 |
| 부채비율 | 29.94 | 183.51 | 0.0 | 2 |
| 유동비율 | 2.33 | 1.27 | 100.0 | 2 |

해석: 수익성·유동성은 피어보다 높은 위치, 부채비율은 낮은 위치다. DSO는 피어 중앙값보다
높아 매출채권 회수 기간 관점의 참고 검토 신호로 남는다. 단, 피어 수가 작고 삼성전자의 사업
구조가 다각화되어 단순 비교 한계가 있다.

## 6. 관점별 독립 평가

2026-06-03 live 실행에서 내부 4관점과 동종업계 관점은 `gemini-2.5-flash`, 외부 query/eval은
`gemini-3.1-pro-preview`로 completed가 나왔다. 각 관점은 서로의 출력을 보지 않고 별도
material board만 받았다.

| 관점 | 상태 | risk | 평가 | 출처 |
|---|---|---|---|---|
| numeric | completed | Medium | 2025년 활동성 지표와 매출채권 증가율이 매출 증가율을 상회하는 점, 단기차입금 증가가 추가 검토 필요성을 시사한다고 보았다. | 2025 ratio/signals |
| note | completed | High | 2025년 금융자산 관련 대손상각(환입) 금액이 2024년 대비 크게 증가해 채권 손상 관련 검토가 필요하다고 보았다. | D82242/D82638 주석 발췌 |
| flow | completed | Medium | 매출채권 증가율이 매출 증가율을 상회하고, 단기차입금 증가와 OFS 현금및현금성자산 증가도 추가 확인 대상으로 보았다. | 2025 signal snapshot |
| change | completed | High | 매출 대비 매출채권 증가율, 현금흐름 부담 가능성, 재고자산 관리를 전기 대비 변화 관점 검토 후보로 보았다. | 2024→2025 signal snapshot |
| external | completed | Low | 출처가 확인된 관련 외부 맥락 없음. 내부 위험은 그대로 유지한다. | Google Search grounding |
| industry | completed | Low | 대부분의 수익성·안정성 지표는 피어 중앙값보다 우수하거나 유사했다. 다만 DSO는 피어 중앙값보다 높아 추가 검토 참고 신호로 보았다. 사업 다각화로 단순 비교 한계를 명시했다. | `config/industry_peers.yaml`, ISA/KSA 520 |

외부 관점 생성 검색어(개선 후, Pro):

1. `삼성전자 2025 매출채권 증가 사유`
2. `삼성전자 2025 단기차입금 및 현금성자산 증가 배경`
3. `삼성전자 2025 매출 증가 및 재고자산 현황`

외부 관점 출처: 이번 live에서 출처가 확인된 관련 외부 맥락 없음.

## 7. 일치/충돌

| verdict | risk_area | perspectives | comment |
|---|---|---|---|
| conflict | 활동성 지표 관련 리스크(매출채권, 재고자산) | numeric, note, flow, change, external, industry | 활동성 지표는 내부 위험이나 외부 맥락은 잠잠해 회사 고유 가능성으로 주목한다. 동종업계 관점은 낮은 위험이나 사업구조 차이를 고려해 참고로만 본다. |

## 8. 한 단락 종합

2025년 최신 기준에서는 threshold를 넘는 중위험 관계 신호는 없지만, 활동성 지표와 2024→2025
신호 스냅샷에서 추가 검토 후보가 남아 있다. DSO는 48.69일에서 51.83일로 늘었고, 매출채권
YoY 17.20%가 매출 YoY 10.88%를 상회했다. 단기차입금은 33.42% 증가했고, 부채비율은
27.93%에서 29.94%로 상승했다. 주석 관점은 2025년 비유동 매출채권과 대손상각 비용 증가를
채권 회수 가능성 확인 대상으로 보았다. 외부 Pro 관점은 출처가 확인된 관련 외부 맥락을
찾지 못했으므로 내부 위험은 그대로 유지한다. 따라서 내부에서
식별된 활동성 후보는 회사 고유 가능성으로 계속 주목한다. 동종업계 baseline에서는 DSO가
피어 중앙값 44.39일보다 높은 51.83일로 나타나 매출채권 회수 기간 검토 신호를 보강하지만,
피어 수와 사업구조 차이 때문에 참고 관점으로만 사용한다.

## 9. 실행

```powershell
uv run python -m src.report.multi_agent
```
