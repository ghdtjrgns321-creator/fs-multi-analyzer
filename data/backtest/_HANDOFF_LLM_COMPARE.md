# 핸드오프 — 내 홀리스틱 LLM vs gpt-5.4 비교 (10 고위험사)

> 2026-06-14 셋업. **컴팩트 후 이 파일부터 읽고 실행.** 작업 디렉터리:
> C:\Users\ghdtj\workspace\portfolio\fs-multi-analyzer

## 목적
같은 10개 고위험 회사에 대해 **두 LLM의 홀리스틱 통독 품질을 비교**한다:
- **A = 내 공장(이번 세션)**: general-purpose 에이전트(세션 모델)가 9렌즈로 통독 → `_holistic_findings/chunk_N.md`에 이미 산출됨.
- **B = gpt-5.4**: `dashboard/onboarding.py:run_llm_holistic`이 쓰는 모델(OpenAIModel, settings.openai_model=gpt-5.4, reasoning_effort). 같은 dump + 같은 9렌즈 프롬프트(`_HOLISTIC_AUDIT_PROMPT.md`)로 **새로 돌려서** B 산출.
- 입력·프롬프트 동일, **모델만 다름** → 모델 차이만 비교.

## 비교 대상 10개사 (corp / 위험사유 / 내 findings 위치)
known 분식 정답지 6 + 강한 P2후보 4:

| # | corp | 종류 | 위험 사유(요약) | 내 findings |
|---|------|------|----------------|-------------|
| 1 | 00153861 | P2★ | PF발 자본잠식(-440,220)·당기순손실 -1.46조·금융보증 우발 ≈9.98조(자산 2배) | chunk_12.md |
| 2 | 00159616 | known | 건설 분식, 매출 소급재작성(2017 14.5조→2018 전기 13.8조) | chunk_13.md |
| 3 | 01091382 | known | 자본잠식(자본 20,435→2,985)·관계기업/영업권 손상 폭탄 | chunk_31.md |
| 4 | 00118345 | known | 분식, 유동파생금융자산 오태깅 동반 | chunk_4.md |
| 5 | 00409681 | known | 자본잠식(원공시 분류) | chunk_23.md |
| 6 | 00413046 | known | 2017 회계정책변경 소급재작성 | chunk_23.md |
| 7 | 00657783 | known | 분식 정답지 | chunk_28.md |
| 8 | 00148504 | P2 | 2025 이익 −57% 급감 vs 자산·현금 급팽창 비정합 | chunk_11.md |
| 9 | 00367844 | P2 | 흑자 vs 영업현금 대규모 마이너스 괴리(건설 매출인식) | chunk_21.md |
| 10 | 00102760 | P2 | 계속기업·결손누적·상환우선주/전환사채 의존 자본구조 | chunk_1.md |

(corp→연도는 `data/backtest/_holistic_chunks.json`의 해당 회사 years. dump는 `data/backtest/_review_dumps/<corp>_<year>.txt`.)

## 실행 절차 (차기 세션)
### 1. B(gpt-5.4) 산출 — 회사별 다년 dump를 9렌즈로 통독
내 공장은 한 회사의 여러 해를 함께 봤으므로, B도 **회사별 전 연도 dump를 합쳐** 같은 조건으로 준다.
```python
# scripts: data/backtest/_run_gpt_compare.py (신규 작성) 또는 인라인
from pathlib import Path
from dashboard.onboarding import run_llm_holistic  # gpt-5.4 + 9렌즈 system_prompt 내장
import json
ROOT=Path('.')
chunks=json.load(open('data/backtest/_holistic_chunks.json',encoding='utf-8'))['chunks']
years={c['corp']:c['years'] for ch in chunks for c in ch['companies']}
TARGETS=['00153861','00159616','01091382','00118345','00409681','00413046','00657783','00148504','00367844','00102760']
out=Path('data/backtest/_llm_compare'); out.mkdir(exist_ok=True)
for corp in TARGETS:
    dumps=[]
    for y in years.get(corp,[]):
        p=Path(f'data/backtest/_review_dumps/{corp}_{y}.txt')
        if p.exists(): dumps.append(p.read_text(encoding='utf-8'))
    if not dumps: continue
    r=run_llm_holistic('\n\n===다음 회사연도===\n\n'.join(dumps))
    (out/f'{corp}_gpt.md').write_text(r.get('findings','') if r['status']=='ok' else f"[{r['status']}] {r['message']}", encoding='utf-8')
    print(corp, r['status'], len(r.get('findings','')))
```
실행: `PYTHONPATH=. uv run python data/backtest/_run_gpt_compare.py`
- ★OPENAI_API_KEY 필요(이 환경엔 설정돼 있어 실호출됨 — 검증 완료). 10회 호출 비용 ~수$ 이하.
- run_llm_holistic은 dump가 매우 길면 토큰 한도 주의 — 회사당 dump가 크면 §A~§I 중 핵심(§A·§B·§E·§F·§H)만 발췌하거나 회사연도별로 나눠 호출 후 합칠 것.

### 2. 비교 — 각 회사: A(내 chunk findings) vs B(gpt 산출) 대조
각 회사마다 표로:
- **A가 잡은 것**: chunk_N.md의 그 회사 [P1결함]/[원공시]/[P2후보] 목록.
- **B가 잡은 것**: `_llm_compare/<corp>_gpt.md`의 findings.
- **판정**: ①B가 A의 핵심을 동일 포착(일치) ②B가 놓침(A만) ③B가 새로 발견(B만, 진짜인지 검증) ④거짓경보 차이.
- 특히 **known 분식 6개사**: 두 모델이 분식 신호(소급재작성·자본잠식·손상·우발)를 잡았는지가 핵심 척도.

### 3. 산출 — `data/backtest/_LLM_COMPARE_RESULTS.md`
회사별 대조표 + 종합 판정(어느 모델이 더 깊은가·놓침 적은가·거짓경보 적은가). gpt-5.4가 충분하면 UI 채택 확정, 부족하면 모델 재고(gemini-3.1-pro 등).

## 주의·맥락
- 공정 비교: A는 general-purpose(세션 모델, Opus 계열), B는 gpt-5.4. **둘 다 같은 dump+9렌즈**라 모델 추론력 비교가 됨.
- A의 findings는 회사가 여러 chunk에 안 걸침(1 corp = 1 chunk). 위 표의 chunk_N이 그 회사 소견 위치.
- §9: B 결과를 곧이곧대로 믿지 말고, B가 "새로 발견"한 건 dump/duckdb로 재현 검증. known 6개사에서 B가 분식을 놓치면 그 자체가 중요 결과.
- 이번 세션 완료물(배경): 온보딩 게이트(`src/normalize/onboarding_gate.py:run_gate`)·dedup(canonical 2028→2013)·quirk·UI(`dashboard/onboarding.py`, LLM=gpt-5.4). 전 회귀 통과(recall 5/6·pytest 203·F1 0·IS/CF 11=11).
