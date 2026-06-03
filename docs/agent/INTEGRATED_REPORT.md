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

새 canonical과 주석 매핑 반영 후 2025 CFS에서는 장기차입금과 사채 변동이 Medium 관계 신호로
큐 상단에 올라왔다.

| 순위 | 대상 | 유형 | risk | score | 핵심 근거 | 근거 | 출처 |
|---:|---|---|---|---:|---|---|---|
| 1 | 장기차입금 | relationship_signal | Medium | 64.63 | single_account_yoy: 64.63 | ISA/KSA 315, ISA/KSA 520 | - |
| 2 | 사채 | relationship_signal | Medium | 50.90 | single_account_yoy: -50.9 | ISA/KSA 315, ISA/KSA 520 | - |
| 3 | DIO | financial_ratio | Low | 94.20 | 2025: 94.20 | ISA/KSA 501, ISA/KSA 520, K-IFRS 1002 | https://corporatefinanceinstitute.com/resources/accounting/days-inventory-outstanding-dio/ |
| 4 | DSO | financial_ratio | Low | 51.83 | 2025: 51.83 | ISA/KSA 520, K-IFRS 1109, K-IFRS 1107 | https://corporatefinanceinstitute.com/resources/accounting/days-sales-outstanding/ |
| 5 | 매출총이익률 | financial_ratio | Low | 39.38 | 2025: 39.38 | ISA/KSA 520, K-IFRS 1115, K-IFRS 1002 | https://corporatefinanceinstitute.com/resources/accounting/profitability-ratios/ |
| 6 | 부채비율 | financial_ratio | Low | 29.94 | 2025: 29.94 | ISA/KSA 520, ISA/KSA 570 | https://corporatefinanceinstitute.com/resources/knowledge/finance/debt-to-equity-ratio-formula/ |
| 7 | 영업이익률 | financial_ratio | Low | 13.07 | 2025: 13.07 | ISA/KSA 520 | https://corporatefinanceinstitute.com/resources/accounting/operating-profit-margin/ |
| 8 | ROE | financial_ratio | Low | 10.78 | 2025: 10.78 | ISA/KSA 520 | https://corporatefinanceinstitute.com/resources/accounting/what-is-return-on-equity-roe/ |
| 9 | ROA | financial_ratio | Low | 8.36 | 2025: 8.36 | ISA/KSA 520 | https://corporatefinanceinstitute.com/resources/accounting/return-on-assets-roa-formula/ |
| 10 | 발생액 비율 | financial_ratio | Low | 7.42 | 2025: -7.42 | ISA/KSA 520, K-IFRS 1007 | https://www.stockopedia.com/ratios/accrual-ratio-555/ |

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
- 장기차입금 YoY 64.63%, 사채 YoY -50.90%

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
| numeric | completed | Medium | 장기차입금·사채 변동과 매출 대비 매출채권 증가율 괴리를 주요 검토 대상으로 보았다. | 2025 ratio/signals |
| note | completed | High | D82242에서 비유동 매출채권과 대손 관련 변동, D82757에서 우발부채 언급을 확인해 회수가능성·우발부채 공시 검토가 필요하다고 보았다. | D82242/D82638/D82240/D82245/D82757 주석 발췌 |
| flow | completed | Medium | 매출채권 증가율이 매출 증가율을 상회하나 영업CF와 발생액 지표는 양호해 현금흐름 효율성 저하 가능성을 검토 대상으로 보았다. | 2025 signal snapshot |
| change | completed | High | CFS 장기차입금 +64.63%, OFS 장기차입금 고증가, 사채 -50.90%, 단기차입금 증가를 재무구조 변화 후보로 보았다. | 2024→2025 signal snapshot |
| external | completed | Low | 외부 맥락은 매출채권 증가가 매출 증가와 연관된다는 설명 배경을 제공했지만 내부 위험을 약화하지 않는다. | samsung.com, youtube.com |
| industry | completed | Medium | DSO가 피어 중앙값보다 높고, 매출총이익률은 피어 대비 현저히 높아 사업 다각화 한계를 전제로 참고 검토가 필요하다고 보았다. | `config/industry_peers.yaml`, ISA/KSA 520 |

외부 관점 생성 검색어(개선 후, Pro):

1. `"삼성전자" 2025 장기차입금 증가 자금조달`
2. `"삼성전자" 2025 사채 상환 감소`
3. `"삼성전자" 2025 매출채권 증가 원인`

외부 관점 출처: samsung.com, youtube.com grounding URL.

## 7. 일치/충돌

| verdict | risk_area | perspectives | comment |
|---|---|---|---|
| agreement | 매출채권/수익 | numeric, note, flow, change, external, industry | 매출채권/수익에 대해 독립 관점이 같은 방향을 가리켜 신호 강화로 본다. 외부 맥락은 설명용이며 내부 위험을 약화하지 않는다. 동종업계 비교는 참고 신호이며 내부 판단 필드를 바꾸지 않는다. |

## 8. 한 단락 종합

2025년 최신 기준에서는 매출채권 회수가능성과 차입금 구조 변화가 함께 검토 후보로 올라왔다.
DSO는 51.83일로 피어 중앙값 44.39일보다 높고, 매출채권 YoY 17.20%가 매출 YoY 10.88%를
상회했다. 주석 관점은 비유동 매출채권과 대손 관련 변동, D82757의 우발부채 언급을 확인했다.
장기차입금은 64.63% 증가했고 사채는 50.90% 감소해 D82240/D82245 만기·상환 주석과 함께
재무구조 변화 후보로 본다. 외부와 동종업계 관점은 설명·참고 신호로만 사용하며 내부 판단
필드를 바꾸지 않는다.

## 9. 실행

```powershell
uv run python -m src.report.multi_agent
```
