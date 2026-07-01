# AUDIT_BASIS — 회계감사기준·K-IFRS 근거 매핑

> 목적: 공시 재무제표와 주석으로 산출한 review 후보의 근거를 정리한다. 이 문서는 부정·분식 확정 근거가 아니라, 감사인이 검토할 분석 관점의 출처를 연결한다.

## 1. 범위와 판정 기준

2026-06-02 기준으로 IAASB 표준·핸드북 페이지와 IFRS Foundation 표준 목록을 확인했다. KSA는 ISA 기반 한국 감사기준서로 사용하되, 공개 KSA 원문별 링크가 확인되지 않은 항목은 “KSA 원문 미검증”으로 표시한다.

3축 평가는 다음 기준으로 한다.

| 축  | 질문                                                      |
| --- | --------------------------------------------------------- |
| 1   | 재무제표 분석적 절차·계정 관계 검토에 직접 연결되는가     |
| 2   | 공시·주석 리스크 리뷰에 직접 연결되는가                   |
| 3   | 이 도구의 입력인 공시 재무제표와 주석만으로 적용 가능한가 |

등급은 Must(직접 근거), Should(보조 근거), Could(향후 확장), Drop(현재 입력과 무관)으로 둔다.

출처: IAASB Standards & Pronouncements: https://www.iaasb.org/standards-pronouncements, IAASB 2023-2024 Handbook Volume 1: https://ifacweb.blob.core.windows.net/publicfiles/2024-08/IAASB-2023-2024-Handbook-Volume-1.pdf, IFRS Foundation Standards Navigator: https://www.ifrs.org/issued-standards/list-of-standards/

## 2. ISA/KSA 전수 평가표

| 기준        | 제목                                                                                              |   등급 | 3축 평가와 사유                                                                                                                                                                                              | 출처  |
| ----------- | ------------------------------------------------------------------------------------------------- | -----: | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ----- |
| ISA/KSA 200 | Overall Objectives of the Independent Auditor and the Conduct of an Audit in Accordance with ISAs | Should | 1/2/3 보조. 충분하고 적합한 감사증거와 전문적 의구심 원칙은 전체 review queue의 상위 원칙이다. KSA 원문 미검증.                                                                                              | IAASB |
| ISA/KSA 210 | Agreeing the Terms of Audit Engagements                                                           |   Drop | 1/2/3 낮음. 감사계약 조건 기준으로 공시 재무제표 분석 입력과 직접 연결되지 않는다. KSA 원문 미검증.                                                                                                          | IAASB |
| ISA/KSA 220 | Quality Management for an Audit of Financial Statements                                           |   Drop | 1/2/3 낮음. 감사품질관리 절차 기준으로 계정 관계·주석 분석 로직의 직접 근거가 아니다. KSA 원문 미검증.                                                                                                       | IAASB |
| ISA/KSA 230 | Audit Documentation                                                                               | Should | 2/3 보조. EvidenceRef, 근거 위치, 재현 가능한 판단 로그 설계 근거다. KSA 원문 미검증.                                                                                                                        | IAASB |
| ISA/KSA 240 | The Auditor's Responsibilities Relating to Fraud in an Audit of Financial Statements              | Should | 1/2 보조, 3 제한. 부정 확정이 아니라 이상 징후와 경영진 편의 가능성 검토 관점만 차용한다. KSA 원문 미검증.                                                                                                   | IAASB |
| ISA/KSA 250 | Consideration of Laws and Regulations in an Audit of Financial Statements                         |  Could | 2 보조 가능, 3 제한. 법규 위반 공시는 향후 watchlist 대상이나 현재 계정 사슬 직접 근거는 약하다. KSA 원문 미검증.                                                                                            | IAASB |
| ISA/KSA 260 | Communication with Those Charged with Governance                                                  | Should | 2/3 보조. 유의적 발견사항·확인 질문을 감사인에게 전달하는 보고 설계 근거다. KSA 원문 미검증.                                                                                                                 | IAASB |
| ISA/KSA 265 | Communicating Deficiencies in Internal Control                                                    |  Could | 2 가능, 3 낮음. 내부통제 자료가 없어 현재 입력만으로 직접 적용은 어렵다. KSA 원문 미검증.                                                                                                                    | IAASB |
| ISA/KSA 300 | Planning an Audit of Financial Statements                                                         | Should | 1/3 보조. 중요 영역 우선순위와 분석 범위 설정 근거다. KSA 원문 미검증.                                                                                                                                       | IAASB |
| ISA/KSA 315 | Identifying and Assessing the Risks of Material Misstatement                                      |   Must | 1/2/3 직접. 계정 관계, 주석, 공시 패턴으로 위험 후보를 식별하는 핵심 근거다. KSA 원문 미검증.                                                                                                                | IAASB |
| ISA/KSA 320 | Materiality in Planning and Performing an Audit                                                   |   Must | 1/2/3 직접. signal threshold, materiality 보조 판단, 우선순위화 근거다. KSA 원문 미검증.                                                                                                                     | IAASB |
| ISA/KSA 330 | The Auditor's Responses to Assessed Risks                                                         | Should | 1/3 보조. 이 도구의 next_procedure 추천 근거다. KSA 원문 미검증.                                                                                                                                             | IAASB |
| ISA/KSA 402 | Audit Considerations Relating to an Entity Using a Service Organization                           |   Drop | 1/2/3 낮음. 서비스조직 내부통제 자료가 필요하며 현재 공시 입력과 직접 맞지 않는다. KSA 원문 미검증.                                                                                                          | IAASB |
| ISA/KSA 450 | Evaluation of Misstatements Identified during the Audit                                           | Should | 1/3 보조. 왜곡표시 누적·평가와 materiality 연결 근거다. KSA 원문 미검증.                                                                                                                                     | IAASB |
| ISA/KSA 500 | Audit Evidence                                                                                    |   Must | 1/2/3 직접. 숫자 신호, 주석 EvidenceRef, 외부 출처의 충분성·적합성 검토 원칙이다. KSA 원문 미검증.                                                                                                           | IAASB |
| ISA/KSA 501 | Audit Evidence - Specific Considerations for Selected Items                                       | Should | 1/2 보조. 재고, 소송·청구 등 특정 항목 검토 근거로 재고·충당부채 확장에 유용하다. KSA 원문 미검증.                                                                                                           | IAASB |
| ISA/KSA 505 | External Confirmations                                                                            |  Could | 1 가능, 3 낮음. 외부조회는 감사 절차이나 공개 재무제표 입력만으로 수행할 수 없다. KSA 원문 미검증.                                                                                                           | IAASB |
| ISA/KSA 510 | Initial Audit Engagements - Opening Balances                                                      |   Drop | 1 제한, 2 낮음. 초도감사 개시잔액 절차로 현재 3개년 공시 분석과 직접 연결되지 않는다. KSA 원문 미검증.                                                                                                       | IAASB |
| ISA/KSA 520 | Analytical Procedures                                                                             |   Must | 1/3 직접. 매출-채권-CF, 재고-원가, 차입금-이자-CF 관계 사슬의 직접 근거이며, 일반 분석적 절차(전기 대비 추세, 구성비, 비교가능 정보 대비 변동)도 전 계정 다축 프로파일러의 근거로 포함한다. KSA 원문 미검증. | IAASB |
| ISA/KSA 530 | Audit Sampling                                                                                    |  Could | 3 낮음. 표본추출은 원장·증빙 모집단에 맞고 공시 재무제표 전수 입력과 직접 맞지 않는다. KSA 원문 미검증.                                                                                                      | IAASB |
| ISA/KSA 540 | Auditing Accounting Estimates and Related Disclosures                                             |   Must | 1/2/3 직접. 대손충당금, 재고평가손실, 손상, 충당부채 주석 검토 근거다. KSA 원문 미검증.                                                                                                                      | IAASB |
| ISA/KSA 550 | Related Parties                                                                                   |   Must | 2/3 직접. 특수관계자 주석과 비정상 거래 공시 검토 근거다. KSA 원문 미검증.                                                                                                                                   | IAASB |
| ISA/KSA 560 | Subsequent Events                                                                                 | Should | 2/3 보조. 보고기간후 사건과 공시 변동 검토 근거다. KSA 원문 미검증.                                                                                                                                          | IAASB |
| ISA/KSA 570 | Going Concern                                                                                     | Should | 1/2/3 보조. 유동성·차입금·만기 주석 신호의 검토 근거다. KSA 원문 미검증.                                                                                                                                     | IAASB |
| ISA/KSA 580 | Written Representations                                                                           |   Drop | 3 낮음. 경영진 서면진술은 공개 재무제표 입력으로 확인할 수 없다. KSA 원문 미검증.                                                                                                                            | IAASB |
| ISA/KSA 600 | Special Considerations - Audits of Group Financial Statements                                     |  Could | 2 가능, 3 제한. 연결/별도 비교 확장에 유용하나 현 MVP 관계 사슬 직접 근거는 약하다. KSA 원문 미검증.                                                                                                         | IAASB |
| ISA/KSA 610 | Using the Work of Internal Auditors                                                               |   Drop | 3 낮음. 내부감사 업무 자료가 필요하다. KSA 원문 미검증.                                                                                                                                                      | IAASB |
| ISA/KSA 620 | Using the Work of an Auditor's Expert                                                             |  Could | 2 가능, 3 제한. 공정가치·손상 등 전문가 영역 flag에 향후 사용 가능하다. KSA 원문 미검증.                                                                                                                     | IAASB |
| ISA/KSA 700 | Forming an Opinion and Reporting on Financial Statements                                          | Should | 2/3 보조. 감사보고서·재무제표 표시와 의견 유형 확인의 보고 근거다. KSA 원문 미검증.                                                                                                                          | IAASB |
| ISA/KSA 701 | Communicating Key Audit Matters in the Independent Auditor's Report                               | Should | 2/3 보조. KAM과 Finding/context 비교, 공시 변동 추적 근거다. KSA 원문 미검증.                                                                                                                                | IAASB |
| ISA/KSA 705 | Modifications to the Opinion in the Independent Auditor's Report                                  |  Could | 2/3 가능. 의견변형 여부를 외부 맥락으로 분리 확인할 수 있으나 계정 신호를 바꾸지 않는다. KSA 원문 미검증.                                                                                                    | IAASB |
| ISA/KSA 706 | Emphasis of Matter and Other Matter Paragraphs                                                    |  Could | 2/3 가능. 강조사항·기타사항 문단은 공시 맥락으로 사용 가능하다. KSA 원문 미검증.                                                                                                                             | IAASB |
| ISA/KSA 710 | Comparative Information - Corresponding Figures and Comparative Financial Statements              | Should | 1/2/3 보조. 전기 대비 공시·수치 변동 비교 근거다. KSA 원문 미검증.                                                                                                                                           | IAASB |
| ISA/KSA 720 | The Auditor's Responsibilities Relating to Other Information                                      |  Could | 2/3 가능. 사업보고서 기타정보와 재무제표 불일치 검토 확장 근거다. KSA 원문 미검증.                                                                                                                           | IAASB |

요약: ISA/KSA 34개 평가. Must 6, Should 13, Could 9, Drop 6.

## 3. K-IFRS/IFRS 재무제표·공시 후보 평가표

| 기준                  | 제목                                                         |   등급 | 3축 평가와 사유                                                                                   | 출처 |
| --------------------- | ------------------------------------------------------------ | -----: | ------------------------------------------------------------------------------------------------- | ---- |
| K-IFRS 1001 / IAS 1   | Presentation of Financial Statements                         |   Must | 1/2/3 직접. 재무제표 표시, 비교정보, 주석 표시의 기본 근거다.                                     | IFRS |
| K-IFRS 1002 / IAS 2   | Inventories                                                  |   Must | 1/2/3 직접. 재고자산-매출원가-평가손실 사슬과 재고 주석 근거다.                                   | IFRS |
| K-IFRS 1007 / IAS 7   | Statement of Cash Flows                                      |   Must | 1/3 직접. 영업CF와 매출·채권·차입금 사슬 검토 근거다.                                             | IFRS |
| K-IFRS 1008 / IAS 8   | Basis of Preparation of Financial Statements                 | Should | 2/3 보조. 회계정책·추정 변경과 오류 공시 변동 검토 근거다.                                        | IFRS |
| K-IFRS 1010 / IAS 10  | Events after the Reporting Period                            | Should | 2/3 보조. 보고기간후 사건 주석 검토 근거다.                                                       | IFRS |
| K-IFRS 1016 / IAS 16  | Property Plant and Equipment                                 |  Could | 1/2 가능. 유형자산·감가상각·손상 확장에 유용하나 현 MVP 계정은 아니다.                            | IFRS |
| K-IFRS 1021 / IAS 21  | The Effects of Changes in Foreign Exchange Rates             |  Could | 1/2 가능. 환율 민감 계정 확장에 유용하나 현 MVP 직접 근거는 약하다.                               | IFRS |
| K-IFRS 1023 / IAS 23  | Borrowing Costs                                              |  Could | 1 가능. 차입금 확장 보조이나 현재는 이자비용·CF 관계가 우선이다.                                  | IFRS |
| K-IFRS 1024 / IAS 24  | Related Party Disclosures                                    |   Must | 2/3 직접. 특수관계자 거래·잔액 주석 검토 근거다.                                                  | IFRS |
| K-IFRS 1032 / IAS 32  | Financial Instruments: Presentation                          | Should | 1/2 보조. 금융부채·자본 분류와 표시 검토 근거다.                                                  | IFRS |
| K-IFRS 1036 / IAS 36  | Impairment of Assets                                         |   Must | 1/2/3 직접. 손상·회수가능액·손상차손 주석 검토 근거다.                                            | IFRS |
| K-IFRS 1037 / IAS 37  | Provisions, Contingent Liabilities and Contingent Assets     |   Must | 2/3 직접. 충당부채·우발부채 주석 리스크 근거다.                                                   | IFRS |
| K-IFRS 1038 / IAS 38  | Intangible Assets                                            |  Could | 1/2 가능. 무형자산·손상 확장에 유용하나 현 MVP 계정은 아니다.                                     | IFRS |
| K-IFRS 1102 / IFRS 2  | Share-based Payment                                          |   Drop | 1/2/3 낮음. 공시 입력으로 확인 가능하나 현 계정 사슬·주석 리스크 우선순위와 직접 연결되지 않는다. | IFRS |
| K-IFRS 1105 / IFRS 5  | Non-current Assets Held for Sale and Discontinued Operations |  Could | 1/2 가능. 중단영업·매각예정 분류 확장에 유용하다.                                                 | IFRS |
| K-IFRS 1107 / IFRS 7  | Financial Instruments: Disclosures                           |   Must | 2/3 직접. 신용위험, 유동성위험, 금융상품 주석 근거다.                                             | IFRS |
| K-IFRS 1108 / IFRS 8  | Operating Segments                                           |  Could | 2/3 가능. 부문별 공시와 업황 비교 확장 근거다.                                                    | IFRS |
| K-IFRS 1112 / IFRS 12 | Disclosure of Interests in Other Entities                    |  Could | 2 가능. 관계기업·종속기업 주석 확장에 유용하나 현 MVP 직접 근거는 약하다.                         | IFRS |
| K-IFRS 1113 / IFRS 13 | Fair Value Measurement                                       | Should | 1/2 보조. 공정가치 측정·공시와 평가 불확실성 검토 근거다.                                         | IFRS |
| K-IFRS 1115 / IFRS 15 | Revenue from Contracts with Customers                        |   Must | 1/2/3 직접. 매출 인식과 계약자산·수취채권 관련 주석 검토 근거다.                                  | IFRS |
| K-IFRS 1116 / IFRS 16 | Leases                                                       |  Could | 1/2 가능. 리스부채·사용권자산 확장에 유용하나 현 MVP 직접 근거는 약하다.                          | IFRS |

요약: K-IFRS/IFRS 후보 21개 평가. Must 9, Should 4, Could 7, Drop 1.

## 4. 채택 기준 매핑

| 분석 요소               | 채택 근거                                           | 적용 방식                                                                          |
| ----------------------- | --------------------------------------------------- | ---------------------------------------------------------------------------------- |
| 관계 사슬 공통          | ISA/KSA 315, 500, 520                               | 계정 간 비정상 관계를 위험 후보로 올리고, 숫자·주석 근거를 EvidenceRef로 분리한다. |
| `revenue-receivable-cf` | ISA/KSA 520, 540; K-IFRS 1007, 1107, 1109, 1115     | 매출 증가와 채권·대손·영업CF 괴리를 분석하고 신용위험·대손 주석과 교차검증한다.    |
| `inventory-cogs`        | ISA/KSA 501, 520, 540; K-IFRS 1002, 1036            | 재고와 매출원가·평가손실 괴리를 분석하고 진부화·손상 주석과 교차검증한다.          |
| `debt-interest-cf`      | ISA/KSA 520, 570; K-IFRS 1001, 1007, 1107, 1109     | 차입금, 이자비용, CF, 만기·유동성위험 주석을 함께 본다.                            |
| materiality             | ISA/KSA 320, 450, 200                               | 임계값은 판단 보조이며, 발견된 신호는 중요성 관점으로 우선순위화한다.              |
| 공시 변동               | ISA/KSA 560, 701, 710; K-IFRS 1001, 1008, 1010      | 전기 대비 주석 변화, 보고기간후 사건, KAM 변화를 별도 참고 맥락으로 제시한다.      |
| 주석 리스크             | ISA/KSA 500, 540, 550, 570; K-IFRS 1024, 1037, 1107 | 주석에 실제 존재하는 문구만 인용하고, 없는 내용은 confirm_question으로 남긴다.     |

## 5. 제외·제한 원칙

Drop 기준은 현재 입력(공시 재무제표 + 주석)으로 검증할 수 없는 계약, 내부통제, 내부감사, 서면진술, 서비스조직 절차를 제외한다. Could 기준은 향후 원장, 감사보고서 본문, 사업보고서 기타정보, 내부 자료가 들어오면 확장할 수 있으나 현 Finding 판단 필드를 직접 바꾸지 않는다.
