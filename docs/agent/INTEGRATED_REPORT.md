# INTEGRATED_REPORT — L4 멀티에이전트 통합 리포트

> 대상: 삼성전자 `00126380`, 연결(CFS), 2022~2025. 이 리포트는 공시 재무제표와 주석 기반
> 검토 후보 큐이며 부정·분식 확정 근거가 아니다.

## 1. 입력과 구조

- 계정 Finding: 최신 연도와 근거 연도가 맞는 항목만 큐에 반영한다.
- 관계사슬 신호: [SIGNAL_REPORT.md](SIGNAL_REPORT.md), `src.signals.red_flags`
- 전수 보편 스캔: `src.signals.universal` — BS·IS·CF 전 계정(account_id)에 YoY,
  z-score, 구성비 급변, CFS/OFS 괴리를 적용한다.
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

BS·IS·CF 주요 계정 canonical 확장과 전 계정 보편 스캔 후 2025 CFS에서는 사업결합,
장기차입금 차입, 자기주식취득, 운전자본변동 등 CF 흐름 항목이 Medium 관계 신호로 큐
상단에 올라왔다. 등록되지 않은 account_id도 보편 스캔과 `unmapped_material_account`로
숨기지 않는다.

| 순위 | 대상 | 유형 | risk | score | 핵심 근거 | 근거 | 출처 |
|---:|---|---|---|---:|---|---|---|
| 1 | 사업결합순현금유출 | relationship_signal | Medium | 2102.89 | single_account_yoy: 2102.89 | ISA/KSA 315, ISA/KSA 520 | - |
| 2 | 장기차입금차입 | relationship_signal | Medium | 593.17 | single_account_yoy: 593.17 | ISA/KSA 315, ISA/KSA 520 | - |
| 3 | 장기차입금차입 | relationship_signal | Medium | 593.17 | universal_yoy: 593.17 | ISA/KSA 315, ISA/KSA 520 | - |
| 4 | 자기주식취득 | relationship_signal | Medium | 552.00 | single_account_yoy: 552.0 | ISA/KSA 315, ISA/KSA 520 | - |
| 5 | 운전자본변동 | relationship_signal | Medium | 513.31 | single_account_yoy: -513.31 | ISA/KSA 315, ISA/KSA 520 | - |
| 6 | 운전자본변동 | relationship_signal | Medium | 513.31 | universal_yoy: -513.31 | ISA/KSA 315, ISA/KSA 520 | - |
| 7 | 기타수익 | relationship_signal | Medium | 353.00 | universal_z_score: 353.0 | ISA/KSA 315, ISA/KSA 520 | - |
| 8 | 장기금융상품의 취득 | relationship_signal | Medium | 239.42 | universal_yoy: 239.42 | ISA/KSA 315, ISA/KSA 520 | - |
| 9 | 장기차입금 | relationship_signal | Medium | 137.49 | growth_divergence: -137.49 | ISA/KSA 315, ISA/KSA 520 | - |
| 10 | 기타자본항목 | relationship_signal | Medium | 132.82 | cfs_ofs_gap: 132.82 | ISA/KSA 315, ISA/KSA 520 | - |

## 3. 회사 전체 지표 요약

- 수익성: ROE 10.78, ROA 8.36, 매출총이익률 39.38, 영업이익률 13.07
- 활동성: 매출채권회전율 7.04, DSO 51.83, 재고회전율 3.87, DIO 94.20, 총자산회전율 0.62
- 안정성: 부채비율 29.94, 유동비율 2.33, 이자보상배율 3.72
- 이익의 질: 영업CF/순이익 1.89, 발생액 비율 -7.42

## 4. 2024→2025 신호 스냅샷

- 등록 canonical: BS 34개, IS 17개, CF 18개.
- 매출 YoY 10.88%, 매출채권 YoY 17.20%, 괴리 -6.32pp
- 매출 YoY 10.88%, 재고자산 YoY 1.70%, 괴리 9.18pp
- 매출원가 YoY 8.40%, 재고자산 YoY 1.70%, 괴리 6.70pp
- 단기차입금 YoY 33.42%, 영업활동현금흐름 YoY 16.90%
- 장기차입금 YoY 64.63%, 사채 YoY -50.90%
- 재무활동CF YoY -72.86%, 장기차입금 YoY 64.63%, 괴리 -137.49pp
- 투자활동CF YoY 19.76%, 유형자산취득 YoY -7.56%, 괴리 27.32pp
- 사업결합순현금유출 YoY 2102.89%, 장기차입금차입 YoY 593.17%
- 운전자본변동 YoY -513.31%, 자기주식취득 YoY 552.00%
- 전수 보편 스캔: 장기차입금차입 universal_yoy 593.17%, 운전자본변동 -513.31%,
  기타수익 universal_z_score 353.0, 장기금융상품의 취득 universal_yoy 239.42%,
  무형자산취득 universal_yoy 98.30%
- CFS/OFS 연결·별도 괴리: 기타자본항목 132.82%, 법인세비용 105.86%,
  당기손익-공정가치금융자산 100.00%, 단기금융상품 81.85%
- 기타 중요 계정(unmapped material): 부채와자본총계 566,942,110백만원, 기초자본
  402,192,070백만원·391,687,603백만원·370,513,188백만원, 기말의 현금및현금성자산
  57,856,378백만원

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
| numeric | completed | Medium | 사업결합순현금유출, 장기차입금차입, 자기주식취득, 운전자본변동, 기타수익, 장기금융상품의 취득, 기타자본항목 CFS/OFS 괴리를 검토 대상으로 보았다. | 2025 ratio/signals |
| note | completed | High | 비유동 매출채권 급증, 대손상각비 증가, 매출채권 담보 제공, 유동성장기차입금 공시 불명확성을 검토 대상으로 보았다. | D82242/D82638/D82240/D82245/D82757 주석 발췌 |
| flow | completed | Medium | 사업결합순현금유출, 장기차입금 차입, 비유동차입금 상환, 자기주식취득, 운전자본변동, 재무활동CF와 장기차입금 괴리, 법인세비용·배당금수입·이자수취 CFS/OFS 괴리를 보았다. | 2025 IS/CF signal snapshot |
| change | completed | Medium | 2025년 사업결합순현금유출, 장기차입금 차입, 자기주식취득, 운전자본변동의 큰 전기 대비 변화를 자금 흐름 검토 후보로 보았다. | 2024→2025 signal snapshot |
| external | completed | Low | 외부 출처는 2025년 자사주 매입과 임직원 주식보상 활용 맥락을 제공했지만 내부 위험을 약화하지 않는다. | hani.co.kr, einfomax.co.kr |
| industry | completed | Medium | 수익성·안정성은 피어 대비 우수하나 DSO, 총자산회전율, 발생액 비율 편차와 CF 변동 신호를 참고 검토 대상으로 보았다. | `config/industry_peers.yaml`, ISA/KSA 520 |

외부 관점 생성 검색어(개선 후, Pro):

1. `"삼성전자" 2025 인수합병 OR 사업결합 OR 지분투자`
2. `"삼성전자" 2025 장기차입금 차입 OR 자금조달`
3. `"삼성전자" 2025 자사주 매입 OR 자기주식 취득`

외부 관점 출처: hani.co.kr, einfomax.co.kr grounding URL.

## 7. 일치/충돌

| verdict | risk_area | perspectives | comment |
|---|---|---|---|
| conflict | 사업결합순현금유출 | numeric, note, flow, change, external, industry | 사업결합순현금유출은 내부 위험이나 외부 맥락은 잠잠해 회사 고유 가능성으로 주목한다. |

## 8. 한 단락 종합

2025년 재무제표 검토 결과, 사업결합순현금유출은 전년 대비 2102.89% 증가했고
장기차입금차입도 593.17% 증가했다. 재무활동현금흐름과 장기차입금 증가율 간 괴리,
운전자본변동 급증, 기타자본항목 CFS/OFS 괴리가 함께 관찰되어 자금 조달과 사용처,
연결·별도 차이의 설명 가능성을 추가 검토할 필요가 있다. 외부 관점은 자사주 매입 맥락만
출처 기반으로 확인했으며, 사업결합순현금유출에 대해서는 외부 설명이 충분하지 않아 회사
고유 가능성으로 남긴다. 외부와 동종업계 관점은 설명·참고 신호로만 사용하며 내부 판단
필드를 바꾸지 않는다.

## 9. 실행

```powershell
uv run python -m src.report.multi_agent
```
