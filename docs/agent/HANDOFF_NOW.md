# HANDOFF_NOW — 지금 작업 (컴팩트용 한 장)

> 컴팩트 후 이 파일부터. 상세는 `STATE.md`. 작성 2026-06-21.

## 지금 하는 것
**전과정 파이프라인 측정** — 실제 회사를 DART 수집→정규화→온보딩→Phase1→Phase2까지 돌려
결과·비용·시간을 측정. 회사 3개 예정. 하니스 `data/backtest/_e2e_measure.py`(corp·year 인자화).

## 어디까지 왔나
- ✅ **회사 #1 대주산업(00112457/2024) 완료**:
  - 측정: **158초·₩1,365·LLM 10회** (`data/backtest/_E2E_MEASURE_00112457_2024.md`)
  - 독립 회계분석 vs 산출물 평가 (`_E2E_EVAL_00112457_2024.md`/`.json`)
  - 사용자 코드 수정으로 개선 확인: **SCE 자본 거짓양성 3→0, capex(+177%) 큐 진입, pytest 363 무회귀**
  - user 문서 기록: `docs/user/VERIFICATION.md` 맨 끝 "전과정 E2E 평가(대주산업) before→after"

## 남은 것
- **회사 #2 삼성전자(00126380)** 측정 — `PYTHONPATH=. uv run python data/backtest/_e2e_measure.py 00126380 2024` (대기업이라 S7 본문 커서 #1보다 비용·시간↑)
- **회사 #3 금융사(예 대신증권 00110893)** 측정 — worst-case 비용
- (보류) 다축 신호엔진 재설계 — 스코프 과대로 일시중단, `docs/agent/HANDOFF_SIGNAL_REDESIGN.md`로 이관

## 목적 재정의 (사용자, 고정)
이 도구는 **분식 탐지가 아니라 "이상 변화·감사인이 볼 검토 큐"를 정한다.** 백테스트 분식 recall(5/6)은
회귀가드일 뿐 목적 잣대가 아님. capex 같은 비-분식 이상변화도 큐에 있어야 하되, 정당한 의심점이 위·
비-분식은 반박 "정상우세"로 하단.

## 핵심 파일
- 측정 하니스: `data/backtest/_e2e_measure.py` (비용=Agent.run usage 래핑, 단가 $2.5/$10·₩1,380 가정)
- 평가 스크립트: `data/backtest/_e2e_eval.py` (전처리 1:1 + Phase1 + Phase2 관점별)
- 상태 진입점: `docs/agent/STATE.md`
