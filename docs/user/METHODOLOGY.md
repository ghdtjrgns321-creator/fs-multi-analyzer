# 분석 기준을 어떻게 정하는가 — 인과관계 도출 방법론

> 이 도구가 "어떤 계정·지표를 엮어서 볼지"를 **누가, 어떻게, 왜** 그렇게 정하는지 설명한다.
> 누구에게든 이 문서 하나로 설명할 수 있다. 설계 상세는 [../agent/PLAN.md](../agent/PLAN.md),
> 감사기준 근거 목록은 [../agent/AUDIT_BASIS.md](../agent/AUDIT_BASIS.md)를 참조한다.

## 풀어야 할 문제

재무제표 분석에서는 *"매출이랑 매출채권을 엮어 본다", "ROE를 본다"* 같은 **무엇과 무엇을
연결해서 볼지(인과관계·지표)**를 누군가 정해야 한다. 이걸 **임의로 정하면** 두 가지 문제가 생긴다.

- "왜 그 연결을 보나?"에 답을 못 한다 (근거 없음 → 신뢰성 문제)
- 봐야 할 걸 빠뜨린다 (한 사람의 머리로는 누락 발생)

## 우리의 답: 2단계로 정한다

### 1차 — 회계감사기준 (권위 있는 골격)

감사인이 실제로 쓰는 **회계감사기준(ISA / 한국 KSA)을 전수로 훑어**, 재무제표 분석·공시
리뷰에 관련된 근거를 **다 끌어오고**, 무관한 건 **사유와 함께 처낸다.**

- 예: ISA 520(분석적 절차)이 *"매출 대비 매출채권 비율을 보라"*고 직접 명시 → 우리 연결의 근거.
- 결과: *"왜 이 연결을 보나 = 어느 기준 몇 조"*가 박힌다. **신뢰성 + 빠짐없는 뼈대.**

### 2차 — 웹검색 + LLM 분석 (실무 지표 보강)

감사기준에 일일이 적혀 있진 않지만 **실무에서 자주 쓰는 재무지표와 계정 조합**을
웹검색 + LLM으로 발굴한다. 2026-06-02에 `config/playbooks/financial_ratios.yaml`로 외부화했다.

| 분류 | 채택 지표 | 엮는 계정 조합 | MVP1 상태 |
|------|-----------|----------------|-----------|
| 수익성 | ROE | 당기순이익↔자본총계 | 계산 가능 |
| 수익성 | ROA | 당기순이익↔자산총계 | 계산 가능 |
| 수익성 | ROI | 당기순이익↔투자원가 | 계정 부족 |
| 수익성 | 매출총이익률 | 매출↔매출원가 | 계산 가능 |
| 수익성 | 영업이익률 | 영업이익↔매출 | 계산 가능 |
| 활동성 | 매출채권회전율 | 순외상매출↔평균매출채권 | 매출 대용 계산 가능 |
| 활동성 | DSO | 매출채권↔순외상매출 | 매출 대용 계산 가능 |
| 활동성 | 재고회전율 | 매출원가↔평균재고자산 | 계산 가능 |
| 활동성 | DIO | 평균재고자산↔매출원가 | 계산 가능 |
| 활동성 | 총자산회전율 | 매출↔자산총계 | 계산 가능 |
| 안정성 | 부채비율 | 부채총계↔자본총계 | 계산 가능 |
| 안정성 | 유동비율 | 유동자산↔유동부채 | 계산 가능 |
| 안정성 | 이자보상배율 | 영업이익↔이자비용 | 계산 가능 |
| 이익의 질 | 영업CF/순이익 | 영업활동현금흐름↔당기순이익 | 계산 가능 |
| 이익의 질 | 발생액 비율 | 당기순이익↔영업활동현금흐름↔자산총계 | 계산 가능 |

출처 확인 결과는 다음과 같다.

- CFI: ROE, ROA, ROI, 매출총이익률, 영업이익률, 매출채권회전율, DSO, 재고회전율, DIO, 총자산회전율, 부채비율, 유동비율, 이자보상배율.
- Wall Street Prep: 영업CF/순이익, Quality of Earnings Ratio.
- Stockopedia: 발생액 비율.

각 지표는 가능한 경우 1차 근거의 ISA/KSA 520(분석적 절차)과 연결했다. 재고 지표는 ISA/KSA
501과 K-IFRS 1002, 채권 지표는 K-IFRS 1109·1107, 현금흐름 지표는 K-IFRS 1007과 함께
매핑한다. 지표는 검토 관점이며 Finding의 부정·분식 확정 근거가 아니다.
계정 추가 후 실제 삼성 3개년 계산 결과는 [../agent/RATIO_REPORT.md](../agent/RATIO_REPORT.md)에
기록했다.

## 왜 이 순서·이 방법인가

| 방식 | 결과 |
|------|------|
| 1차(감사기준)만 | 기준서에 없는 **실무 지표 누락** |
| 2차(웹+LLM)만 | 근거 없는 임의 지표 → **신뢰성 문제** |
| **1차 → 2차 (채택)** | 권위 있는 골격 먼저 + 실무 보강. **둘의 약점을 서로 메움** |

**순서가 1차 먼저인 이유**: 권위 있는 뼈대를 깔아 신뢰 기반을 만든 뒤, 그 위에 실무 지표를
얹는다. 거꾸로 하면 "근거 없는 지표"가 먼저 자리 잡아 정합성이 흔들린다.

그리고 이 2단계는 이 프로젝트의 **큰 원칙과 같은 결**이다 — *확립된 것은 근거(기준)로,
발견은 탐색(웹·LLM)으로.* (PLAN 원칙1 "계산·확립은 코드, 발견은 LLM"의 연장)

## 환각·신뢰 방어

- **1차**: 기준 조항·문구는 출처로 확인하고, 미확인은 "미검증"으로 표시한다(지어내기 금지).
- **2차**: 웹검색 결과 + 출처를 함께 남기고, LLM이 기억만으로 단정하지 않는다.
- 둘 다 근거는 **"감사인이 검토할 관점의 출처"**이지 *"부정 확정 근거"*가 아니다
  (포지셔닝: [../agent/PLAN.md §15](../agent/PLAN.md)).

## 현재 상태

- **1차 (감사기준 전수 → 선별 → 매핑)**: 완료. 결과는 [../agent/AUDIT_BASIS.md](../agent/AUDIT_BASIS.md).
- **2차 (웹+LLM 실무 지표·계정 조합 발굴)**: 완료. 결과는
  [../../config/playbooks/financial_ratios.yaml](../../config/playbooks/financial_ratios.yaml).

## 2차 출처 목록

- CFI Return on Equity: https://corporatefinanceinstitute.com/resources/accounting/what-is-return-on-equity-roe/
- CFI Return on Assets: https://corporatefinanceinstitute.com/resources/accounting/return-on-assets-roa-formula/
- CFI Return on Investment: https://corporatefinanceinstitute.com/resources/knowledge/finance/return-on-investment-roi-formula/
- CFI Profitability Ratios: https://corporatefinanceinstitute.com/resources/accounting/profitability-ratios/
- CFI Operating Profit Margin: https://corporatefinanceinstitute.com/resources/accounting/operating-profit-margin/
- CFI Accounts Receivable Turnover Ratio: https://corporatefinanceinstitute.com/resources/financial-modeling/accounts-receivable-turnover-ratio-template/
- CFI Days Sales Outstanding: https://corporatefinanceinstitute.com/resources/accounting/days-sales-outstanding/
- CFI Inventory Turnover: https://corporatefinanceinstitute.com/resources/accounting/inventory-turnover-ratio/
- CFI Days Inventory Outstanding: https://corporatefinanceinstitute.com/resources/accounting/days-inventory-outstanding-dio/
- CFI Asset Turnover Ratio: https://corporatefinanceinstitute.com/resources/accounting/asset-turnover-ratio/
- CFI Debt to Equity Ratio: https://corporatefinanceinstitute.com/resources/knowledge/finance/debt-to-equity-ratio-formula/
- CFI Current Ratio Formula: https://corporatefinanceinstitute.com/resources/accounting/current-ratio-formula/
- CFI Interest Coverage Ratio: https://corporatefinanceinstitute.com/resources/knowledge/finance/interest-coverage-ratio/
- Wall Street Prep Quality of Earnings Ratio: https://www.wallstreetprep.com/knowledge/quality-of-earnings-ratio/
- Stockopedia Accrual Ratio: https://www.stockopedia.com/ratios/accrual-ratio-555/
