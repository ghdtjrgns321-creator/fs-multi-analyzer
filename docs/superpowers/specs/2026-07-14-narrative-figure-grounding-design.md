# 반박 서술 수치 도표 주입 + 감사 (B/예방)

> 2026-07-14 설계 승인. 배경·실증: 메모리 `narrative-figure-grounding`. 발단: 아스트 2020
> 반박 "전체 자산 583.1억 감소"(실제 298.8억) 환각. 검출감사(A) 3종 실패 → 예방(B) 채택.

## 문제

반박 에이전트(`src/report/rebuttal.py`)가 생성하는 4필드(counter_evidence·normal_explanation·
confirm_question·next_procedure)의 **파생숫자를 LLM이 직접 계산** → 산술 환각. reader.py엔
"계산 금지, 원문 인용만" 가드가 있으나 반박엔 없음. 사후 검출은 파생값 특성상 신뢰불가(실증).

## 해결: 코드가 도표 계산 → LLM 주입 → 도표 멤버십 감사

`amounts.annotate_amounts`("코드 병기, LLM 옮겨쓰기") 패턴 확장.

### 컴포넌트

1. **`src/report/figure_sheet.py` (신규, ~100줄)**
   - `card_scope_names(card) -> set[str]`: cluster_key + related_accounts에서 계정명 추출.
   - `build_figure_sheet(scope_names, series_rows, extra_amounts) -> FigureSheet`:
     - series_rows(as-filed 계정×연도)에서 스코프 계정의 원값·YoY/다년 델타·증감율% 계산.
     - + 핵심 총계(자산/부채/자본총계·매출·당기순이익·영업이익·영업CF) 고정 포함.
     - + 카드 자체 근거(numeric_evidence·note_evidence 금액) 통과.
     - `FigureSheet.money`(set[float], 억 반올림 0.1)·`.growth`(set[float], %p 0.1)·`.render()->str`.
   - `extract_figures(text) -> list`: 억/조/백만/원/% 파싱(check_numeric.decode_krw 재사용).
   - `audit_narrative_figures(texts, sheet) -> list[str]`: 각 숫자가 sheet 멤버인지 정확 대조, 미포함 반환.

2. **프롬프트 주입** (`build_rebuttal_input` + `perspective_prompts.yaml` rebuttal)
   - build_rebuttal_input에 `series` 인자 추가 → entry에 `figure_sheet: FigureSheet.render()`.
   - 플레이북 rebuttal.instruction에 "[숫자 도표]의 값만 그대로 옮겨 쓴다. 도표에 없는 증감·비율
     직접 계산 금지" 추가.

3. **감사 배선**: apply_rebuttal 후(또는 card_pipeline) audit_narrative_figures로 빵꾸 flag →
   카드 메타 또는 골든 검사3. (초기: 감사 함수 + 단위테스트, 파이프라인 flag는 후속)

### 데이터 흐름
```
build_cards → build_figure_sheet(card, series) ─┐
build_rebuttal_input(card + figure_sheet 주입) ←┘
  → rebuttal agent("도표 숫자만 인용")
  → apply_rebuttal → audit_narrative_figures(card, sheet) → 빵꾸 0 기대
```

### 왜 신뢰 가능한가
검출(A)은 "전역 DB 어딘가 존재하나"라 파생값이 우연히 맞거나(583.1 흡수) 스코프 좁히면 정당인용
누락. B는 감사가 **LLM에 준 그 작은 도표**에 대한 정확 멤버십이라 well-defined — 583.1은 도표에
없어 반드시 flag.

## 테스트 (TDD)
- 단위: build_figure_sheet(재고 스코프: 1685.3·159.2·298.8 포함, 583.1 미포함, 10.43% 포함),
  audit(583.1 flag=1·도표내 flag=0), extract_figures(억/조/%/콤마 파싱).
- 2케이스: account(재고) + company 카드.
- 회귀: 전체 pytest 0 fail.
- 최종(사용자 승인·비용): 아스트 재생성 → 감사 빵꾸 0.

## 범위 밖(YAGNI)
- normal_explanation의 정성 시나리오(수치 없는 문장)는 감사 대상 아님(숫자만).
- 검사1 통합·카드레벨 ⚠ 렌더는 후속(초기는 감사 함수+테스트까지).
