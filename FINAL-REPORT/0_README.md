# Disclosure Review Agent — 최종 보고서

![status](https://img.shields.io/badge/status-MVP_구현완료-2ea44f)
![python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)
![package](https://img.shields.io/badge/uv-dependency--groups-DE5FE9)
![db](https://img.shields.io/badge/DuckDB-회사·연도_격리-FFF000?logo=duckdb&logoColor=black)
![agent](https://img.shields.io/badge/PydanticAI-구조화_출력-E92063)
![llm](https://img.shields.io/badge/LLM-gpt--5.4·gemini--2.5-412991?logo=openai&logoColor=white)
![xbrl](https://img.shields.io/badge/XBRL-Arelle-005571)
![ui](https://img.shields.io/badge/Streamlit-리뷰_UI-FF4B4B?logo=streamlit&logoColor=white)
![tests](https://img.shields.io/badge/pytest-tests+golden-0A9EDC?logo=pytest&logoColor=white)
![backtest](https://img.shields.io/badge/발굴_recall-5%2F6-2ea44f)
![positioning](https://img.shields.io/badge/포지셔닝-부정_확정_안함-important)

> **한 줄 요약** — OpenDART 공시 재무제표·주석을 결정론 코드로 전량 계산하고, **발견만** 5개 관점 LLM에 맡겨 교차검증하고 카드 확정 후 외부검증을 거친 뒤, 감사인이 검토할 **리스크 후보 카드**를 근거·반박·다음절차와 함께 제시하는 Human-in-the-Loop 리뷰 도구다. **부정을 확정하지 않는다.**

---

## 시스템 한눈에

```
  회사명 검색            OpenDART 수집(L0)          정규화(L1)              온보딩 게이트
  ─────────      →      finstate JSON            XBRL→canonical    →   G1~G9·통화 결정론 점검
  (~12만 회사)          + 주석 XBRL(2023~)          2,017 표준계정          ([분석 실행]이 자동 실행)
                        + 사업보고서 원문 XML
                                                  회사/연도 격리 DuckDB
                                                                              │ 통과
                                                                              ▼
     [LLM 전처리]  본문 서술 11파트 읽기(III 주석은 글자수 청킹·연결/별도 축 부착) → 게이트 재점검 → 별칭 3단 분업(코드 후보→LLM 선택→신뢰도≥0.7만 자동 등록) — 완료 마커가 카드 단계 진입 조건
                                                                              │
                                                                              ▼
  ┌───────────────────────── L2 신호엔진 (결정론, LLM 0) ─────────────────────────┐
  │  전수 스캔 universal · 다축 프로파일러(self 4축) · 관계사슬 11개 · 비율 15개     │
  │  변동분해 6브리지 · 커버리지 원장(계정층+파생층 진입) · SCE 2D 검산              │
  └────────────────────────────────────┬───────────────────────────────────────┘
                                        │  materials.py 관점별 발췌(등수 힌트 없음)
                                        ▼
      ┌────────┐┌────────┐┌────────┐┌────────┐   ← 내부 4관점 병렬 발견 (GPT-5.4)
      │ 수치   ││ 주석   ││ 흐름   ││ 추세   │      + industry(동종·GPT) = 발견 5관점
                                                     ※ external(Gemini)은 카드 확정 후 검증자
      └────────┘└────────┘└────────┘└────────┘
                    │  grounding: 원 단위 복원 대조로 환각 탈락 (silent drop 0)
                    ▼
              계정/관계/회사 카드 클러스터 (표수 N/4 · 사전식 정렬)
                    │  변동분해 부착 → 조사원(도구 루프) → 반박 + 외부검증(병렬)
                    ▼
   ┌──────────────────────────────────────────────────────────────────┐
   │  의심건 카드 목록 (Streamlit)                                        │
   │  ① 주장(무엇이 의심스러운가)  ② 결과 분해(표·근거)  ③ 시각자료        │
   │  + 반박은 ① 아래 접기(반대근거·정상설명·확인질문·다음절차)           │
   └──────────────────────────────────────────────────────────────────┘
                    │
                    ▼   L5 Human — 검토 큐로 게시된 카드를 감사인이 검토 (Streamlit)
```

**골든 테스트(외부 정답 2검사)** 로 이 파이프라인을 상시 검증한다 — 검사1은 최종 카드 수치를 DART 원천값과 전자동 대조, 검사2는 as-filed 원본을 넣어 실제 제재·재작성 계정이 카드 큐에 뜨는지 채점한다.

---

## 읽는 순서

| #   | 파일                          | 무엇을 담나                                                             |
| --- | ----------------------------- | ----------------------------------------------------------------------- |
| 0   | `0_README.md`                 | 표지 · 한눈 다이어그램 · 핵심 수치 (이 문서)                            |
| 1   | `1_OVERVIEW.md`               | 문제 정의 → 왜 이 접근 → 5원칙 → 기술 스택                              |
| 2   | `2_PIPELINE.md`               | 전체 파이프라인 L0~L5 end-to-end + 실증 예시 1건                        |
| 3   | `3_COLLECT-NORMALIZE.md`      | L0 수집 · L1 정규화 · 온보딩 게이트 (계산 레이어)                       |
| 4   | `4_SIGNAL-ENGINE.md`          | L2 결정론 신호엔진 — 전수 스캔·self 4축·관계사슬·변동분해·커버리지 원장 |
| 5   | `5_PERSPECTIVES-CARDS.md`     | L3/L4 5관점 발견 → grounding → 카드 → 조사 → 반박·외부검증              |
| 6   | `6_GROUNDING-GUARDRAILS.md`   | 환각 방지 4중 장치 — tool DSL·grounding·어휘게이트·금액환산             |
| 7   | `7_UI-DASHBOARD.md`           | L5 Streamlit — 상태머신·카드 3섹션·타입별 차트                          |
| 8   | `8_DIFFERENTIATION.md`        | 기존 접근 대비 차별점·특장점·한계                                       |
| 9   | `9_GOLDEN-TESTS-DECISIONS.md` | 골든 2검사·검증 M/N·ADR                                                 |
| 10  | `10_JOURNEY.md`               | 아키텍처 전환 여정 (폐기·승계)                                          |
| 11  | `11_TROUBLESHOOTING.md`       | 운영 사고·근본원인·복구                                                 |
| 12  | `12_COVERAGE.md`              | 전수 커버리지 부록 (census N/N)                                         |

---

## 핵심 수치 (as-built 실측)

| 지표                                   | 값                                                         | 상세                               |
| -------------------------------------- | ---------------------------------------------------------- | ---------------------------------- |
| 표준 계정 매핑                         | 약 **2,017개** canonical (BS/IS/CIS/CF/SCE)                | [4장](4_SIGNAL-ENGINE.md)          |
| 검증 관점                              | **6개** (내부 4 + 외부·동종 2), 닫힌 집합                  | [5장](5_PERSPECTIVES-CARDS.md)     |
| 관계 사슬 · 재무비율 · 변동분해 브리지 | **11 · 15 · 6**                                            | [4장](4_SIGNAL-ENGINE.md)          |
| 실 LLM E2E (전과정)                    | 삼성 **231초·₩1,981·10호출**, 대주 **158초·₩1,365·10호출** | [9장](9_GOLDEN-TESTS-DECISIONS.md) |
| 백테스트 발굴 recall                   | **5/6** (결정론 신호만)                                    | [9장](9_GOLDEN-TESTS-DECISIONS.md) |
| 골든 검사1(수치)                       | LG생활건강 **N=72 전량 match**, 아스트 **N=59 전량 match** | [9장](9_GOLDEN-TESTS-DECISIONS.md) |
| 골든 검사2(적중)                       | 아스트 재고자산 **rank1·recall@5=2/3**                     | [9장](9_GOLDEN-TESTS-DECISIONS.md) |
| 코드 정독 분모 N                       | **1,626** 파일 (핵심 306 + backtest 1,320)                 | [12장](12_COVERAGE.md)             |

> **검증 스코어카드 · 적용 범위**: 위 검증 수치는 **비금융 일반 상장사(제조·판매·건설)** 대상이다 — 관계사슬·비율·분해가 매출–매출원가–재고 구조를 전제해 금융·보험·지주·리츠 등은 미대응. 검증을 "정답 유무"로 계층화한 스코어카드(①수치충실도 ②제재적중 ③회귀 baseline ④정답부재)는 [9장](9_GOLDEN-TESTS-DECISIONS.md).

> **포지셔닝(최우선·고정)**: 이 도구는 "분식 확정 / 부정 자동 적발 / 운영 성능 검증 완료" 같은 확정·성능보장 표현을 쓰지 않는다. 모든 Finding은 반대근거·정상설명·확인질문·다음절차를 포함한다.
