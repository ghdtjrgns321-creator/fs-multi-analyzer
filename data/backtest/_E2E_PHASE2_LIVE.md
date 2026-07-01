# 실 LLM Phase2 E2E — 비용 + 사각 카드화

단가가정 $2.5/1M(입력)·$10/1M(출력)·₩1,380/$ (gpt-5.4 실단가 미확정).

## 삼성전자 (00126380) target=2025
- 입력: series 864 · note_facts 4215 · sce_cells 150
- **총 비용 ₩1,884** (입력 478,047 · 출력 16,988 토큰 · 호출 7회 · 87초)
- 카드: 계정 17 · 회사 2 / grounded 26 · dropped 1
- 관점별 토큰:
    in=  18,494 out=    22 ₩     64 (3.2s)
    in=   1,414 out=    23 ₩      5 (3.2s)
    in=  72,421 out= 2,276 ₩    281 (17.1s)
    in=  64,441 out= 2,737 ₩    260 (18.9s)
    in=  63,975 out= 2,851 ₩    260 (19.4s)
    in= 250,059 out= 2,608 ₩    899 (20.8s)
    in=   7,243 out= 6,471 ₩    114 (65.7s)
- 사각 관측(grounded 의심건 언급 건수): {'note 특수관계자': 3, 'note 지급보증/약정/우발': 3, 'SCE 자기주식/자본거래': 7}
- occurrence 언급: {'appeared': 1, 'disappeared': 1, 'resumed': 0}
- 계정 카드 상위:
    CFS:매출채권 | receivables_quality | 표수 3/4 | Medium
    CFS:운전자본변동 | earnings_quality | 표수 3/4 | Medium
    CFS:장기차입금 | 기타/차입증가와재무CF역방향 | 표수 3/4 | Medium
    CFS:무형자산 | 기타/무형자산증가 | 표수 1/4 | Medium
    장기차입금 | related_party_concentration | 표수 1/4 | Medium
    CFS:이연법인세자산 | 기타/이연법인세자산증가 | 표수 1/4 | Medium
    CFS:단기차입금 | liquidity_risk | 표수 1/4 | Medium
    CFS:기타포괄손익-공정가치 지정 비유동지분상품투자 | disclosure_change | 표수 1/4 | Medium
    단기차입금 | liquidity_risk | 표수 1/4 | Medium
    CFS:장기금융상품취득 | 기타/장기금융상품취득급증 | 표수 1/4 | Low
    CFS:기타비유동부채 | 기타/기타비유동부채증가 | 표수 1/4 | Medium
    충당부채 | contingent_liability | 표수 1/4 | Medium
- 회사 카드:
    (회사 전체) | contingent_liability | 표수 1/4
    (회사 전체) | related_party_concentration | 표수 1/4

## 대주산업 (00112457) target=2025
- 입력: series 1007 · note_facts 325 · sce_cells 127
- **총 비용 ₩1,037** (입력 244,636 · 출력 13,964 토큰 · 호출 7회 · 71초)
- 카드: 계정 15 · 회사 2 / grounded 25 · dropped 0
- 관점별 토큰:
    in=   1,414 out=    23 ₩      5 (1.2s)
    in=  12,574 out=    22 ₩     44 (2.1s)
    in=  17,208 out=   437 ₩     65 (4.7s)
    in=  66,417 out= 2,271 ₩    260 (14.2s)
    in=  74,027 out= 2,482 ₩    290 (16.4s)
    in=  66,668 out= 3,296 ₩    275 (20.0s)
    in=   6,328 out= 5,433 ₩     97 (51.0s)
- 사각 관측(grounded 의심건 언급 건수): {'note 특수관계자': 1, 'note 지급보증/약정/우발': 1, 'SCE 자기주식/자본거래': 7}
- occurrence 언급: {'appeared': 0, 'disappeared': 0, 'resumed': 0}
- 계정 카드 상위:
    CFS:당기순이익 | earnings_quality | 표수 3/4 | Medium
    CFS:유형자산 | 기타/유형자산급증 | 표수 2/4 | High
    CFS:기타포괄손익누계액 | 기타/기타포괄손익누계액급증 | 표수 2/4 | High
    CFS:이연법인세부채 | 기타/이연법인세부채급증 | 표수 2/4 | Medium
    CFS:재고자산 | inventory_obsolescence | 표수 2/4 | Medium
    CFS:투자부동산 | 기타/투자부동산급증 | 표수 2/4 | Medium
    CFS:법인세비용 | earnings_quality | 표수 2/4 | Medium
    CFS:총포괄손익 | 기타/재평가로 인한 포괄손익 급증 | 표수 1/4 | Medium
    CFS:자산재평가손익 | 기타/자산재평가손익대규모인식 | 표수 1/4 | High
    CFS:매입채무및기타유동채무 | liquidity_risk | 표수 1/4 | Medium
    CFS:투자활동현금흐름 | 기타/투자현금흐름-유형자산취득괴리 | 표수 1/4 | Medium
    CFS:기타비용 | earnings_quality | 표수 1/4 | Low
- 회사 카드:
    (회사 전체) | disclosure_change | 표수 1/4
    (회사 전체) | 기타/비교표시재무제표미작성 | 표수 1/4