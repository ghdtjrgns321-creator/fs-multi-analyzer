# 작업: SCE member-sign 수정 검증·마감 (구현 완료됨 — 검증 전용)

> ★중요: 이 작업은 **구현이 아니다.** member-sign 수정은 이미 작업트리에 들어가 있다
> (`src/normalize/sce.py` untracked 신규 + member 테스트 4개). 이 프롬프트는 그 수정이 실제
> corpus에서 효과를 냈는지 **측정·검증**하고 S4 member-sign 트랙을 마감하는 것뿐이다.
> 코드를 새로 고치지 마라(검증 결과 진짜 결함이 남았을 때만 별도 보고).

## 1. 목표
- 이미 구현된 member-sign 부호 정규화가 실제 재생성 corpus에서 **member합≈-grand 시그니처
  334 → 0**을 달성했는지 검증하고, 회귀(pytest·backtest) 무를 확인한 뒤 트랙을 마감한다.
- 성공 기준: ①§6-script 출력 "시그니처 = 0" ②`pytest tests/ -q` = `203 passed, 1 xfailed`
  ③backtest 분식 recall 5/6 ④00131054/2023 이익잉여금 member = -5510(백만).

## 2. 컨텍스트
- 읽을 파일(수정 금지, 이해용):
  - `src/normalize/sce.py` — `_apply_sign`(L78, 차감변동 전셀 -abs) + `_align_member_signs_to_bare`
    (L615, 총계·member합이 정확히 부호반대면 member 뒤집어 정렬). 둘이 member-sign 수정 본체.
  - `tests/test_normalize.py` L496~571 — member_sign 테스트 4개(핵심·혼재가드·합일치·반대부호).
  - `data/backtest/_P1_MEMBER_SIGN_FIX_PROMPT.md` — 원 설계·진단(00131054/2023 grand=-5510,
    member 이익잉여금이 raw +5510 방치였던 결함).
  - `.claude/state/contracts/5372d147-...md` 41차 블록 — 현재까지 검증 진척(pytest -k member_sign
    4 passed·00131054 real -5510 확인 완료).
- 배경(검증된 사실):
  - 수정은 **미커밋 신규 작업**. persist(renormalize_all --force, task 식별자 b490i6d9g)가 이
    코드로 전 corpus(1668 디렉터리) 재생성 중이었다. **이 검증의 전제 = persist 완료.**
  - 22차 독립 오라클 감사가 313 회사연도 중 **334건** member합≈-grand 시그니처를 검출했고,
    그게 이 수정의 baseline(목표 334→0)이다.
  - 이미 확인: `pytest -k member_sign` 4 passed / 00131054/2023 이익잉여금 = -5,510백만(real db).

## 3. 설계 (이대로 — 구현 변경 없음, 측정만)
- persist 완료를 먼저 확인한다(미완 상태 측정은 stale-mix라 무의미 — 최종 보고 금지).
- §6-script를 그대로 실행해 시그니처를 센다. 잠긴 db는 skip(try/except 내장).
- 시그니처가 0이 아니면 **남은 행을 전수 해부**한다: 어느 corp/year/fs/label인지, 그게
  ①혼재부호(자본 내 대체) 정당 잔여인지 ②member NaN(브레이크다운 미공시)인지 ③진짜 미수정
  결함인지 분류. ③이면 그 corp/label과 raw 원천을 첨부해 별도 보고(코드 임의 수정 금지).
- 설계와 현장 불일치 시 STATUS: NEEDS_CONTEXT.

## 4. 단계 체크리스트 (순서 고정)
- [ ] Step1: **audit-set만 --force 재정규화**(전체 persist 대기 불필요 — §6 시그니처는 audit set만
      읽는다. 전체 persist b490i6d9g는 정규화 err=0로 ~1150/1668까지 갔으나 셸 래퍼 exit 127로 죽음
      = 정규화 오류 아님, 단 전 corpus 완주는 못 함. audit-set 신선도만 보장하면 측정 가능).
      ※주의: no-force resume은 "신선해 보이지만 옛 코드로 만든" db를 skip하므로 audit set엔 부적합 —
      반드시 --force로 audit corps만 강제 재정규화. 명령:
      ```
      PYTHONPATH=. uv run python -c "
      import json; from pathlib import Path
      B=Path('data/backtest'); corps=set()
      for c in json.load((B/'known_cases.json').open(encoding='utf-8'))['cases']:
        if c.get('label')=='positive' and c.get('runnable'): corps.add(c['corp_code'])
      for p in B.glob('_round_targets*.json'):
        for c in json.load(p.open(encoding='utf-8')).get('cases',[]): corps.add(c['corp_code'])
      print(' '.join(sorted(corps)))" > /tmp/audit_corps.txt
      PYTHONPATH=. uv run python -m src.normalize.renormalize_all $(cat /tmp/audit_corps.txt) --force
      ```
      증거: 마지막 `[완료]` 줄 `error=0`. ※error>0이면 그 corp 보고하고 BLOCKED.
- [ ] Step2: §6-script(아래) 실행 → 시그니처 카운트. 증거: 출력 원문 `member합≈-grand 시그니처 = N`.
- [ ] Step3: N>0이면 FLIP 목록 전수 해부(§3 분류). N==0이면 이 단계 "해당 없음".
      증거: 분류표 또는 "N=0".
- [ ] Step4: `PYTHONPATH=. uv run python -m pytest tests/ -q`. 증거: `203 passed, 1 xfailed`.
- [ ] Step5: `PYTHONPATH=. uv run python -m src.backtest.run_backtest` → 분식 recall.
      증거: discovered 집계(두산·아스트·디아이동일·모델솔루션·셀트리온 True, 세토피아 False = 5/6).
      ※두산(24조·3년) 첫 회사가 수 분 느림 — hang 아님. 돌리는 중 다른 uv 실행 금지(경합).
- [ ] Step6: 직접증거 재현 —
      `PYTHONPATH=. uv run python -c "import duckdb;c=duckdb.connect('data/companies/00131054/2023/analysis.duckdb',read_only=True);print(c.execute(\"SELECT component_std,amount FROM sce_equity_components WHERE change_label LIKE '%배당%' AND change_role='leaf' AND fs_div='CFS'\").fetchall())"`
      증거: 이익잉여금 행 amount ≈ -5.51e9.
- [ ] Step7(마지막): 종합 — §6 4기준 충족 여부 표 + task#5 판정(전부 충족=[x]) +
      STATE.md·COVERAGE_REMEDIATION.md S4 갱신 문안 제안 + "member합==grand 불변식을 sce_balance/
      하니스에 영구 편입할지" 권고(재발 게이트).

## 5. 금지 사항 (1건이라도 위반 시 실패)
- 코드 임의 수정 금지: 이건 검증 작업. 진짜 결함(③) 발견 시에도 고치지 말고 증거와 함께 보고만.
- 하드코딩 금지: §6-script의 회사·연도는 known_cases.json/_round_targets*.json에서 받는다(이미 그럼).
  특정 corp/year를 손으로 넣어 시그니처를 줄이지 마라.
- 테스트 약화 금지: member_sign 테스트 4개·전체 203 어느 것도 skip/assert완화 금지.
- hollow-PASS 금지: persist 미완 상태에서 측정한 0을 "통과"로 보고 금지. 잠긴 db 다수
  skip된 측정(locked-skipped 큼)을 0으로 둔갑 금지 — locked-skipped도 출력에 명시.
- 범위 밖 수정 금지: STATE/COVERAGE/contract/task 외 파일 변경 금지(검증 작업).

## 6. 최종 검증 (완료 선언 전 필수)
- §6-script → `시그니처 = 0` (locked-skipped=0 또는 0에 가깝고, skip된 것 재측정해도 0)
- `pytest tests/ -q` → `203 passed, 1 xfailed`
- `run_backtest` → 분식 recall **5/6**(세토피아만 miss)
- 00131054/2023 이익잉여금 member ≈ -5.51e9
※ 하나라도 어긋나면 DONE 금지. 시그니처>0이면 DONE_WITH_CONCERNS + 해부표.

### §6-script (시그니처 카운트 — 잠긴 db skip 내장, 그대로 실행)
```
PYTHONPATH=. uv run python -c "
import duckdb,json,pandas as pd
from pathlib import Path
AGG={'지배기업소유주지분','자본총계','자본과부채총계','-'}
B=Path('data/backtest'); seen=set(); T=[]
for jp in [B/'known_cases.json']:
 for c in json.load(jp.open(encoding='utf-8'))['cases']:
  if c.get('label')=='positive' and c.get('runnable'):
   for y in c.get('run_years',[]):
    t=(c['corp_code'],str(y));  T.append(t) if t not in seen else None; seen.add(t)
for p in sorted(B.glob('_round_targets*.json')):
 for c in json.load(p.open(encoding='utf-8')).get('cases',[]):
  for y in c.get('run_years',[]):
   t=(c['corp_code'],str(y)); T.append(t) if t not in seen else None; seen.add(t)
flip=0; n_db=0; locked=0; flips=[]
for corp,fy in T:
 db=Path(f'data/companies/{corp}/{fy}/analysis.duckdb')
 if not db.exists(): continue
 try: con=duckdb.connect(str(db),read_only=True)
 except Exception: locked+=1; continue
 try:
   if 'sce_equity_components' not in {r[0] for r in con.execute('SHOW TABLES').fetchall()}: con.close(); continue
   df=con.execute(\"SELECT fs_div,change_label,component_std,amount FROM sce_equity_components WHERE change_role='leaf'\").fetchdf()
 finally: con.close()
 if df.empty: continue
 n_db+=1; df['amt']=pd.to_numeric(df['amount'],errors='coerce')
 for (fs,lab),g in df.groupby(['fs_div','change_label']):
  gr=g[g['component_std']=='-']['amt'].dropna()
  if gr.empty or abs(float(gr.iloc[0]))<1e6: continue
  gv=float(gr.iloc[0]); mem=g[~g['component_std'].isin(AGG)]['amt'].dropna()
  if mem.empty: continue
  ms=float(mem.sum())
  if abs(ms+gv)<1e6 and abs(ms-gv)>=1e6: flip+=1; flips.append((corp,fy,fs,lab,round(gv),round(ms)))
print('audit targets:',len(T),' dbs scanned:',n_db,' locked-skipped:',locked)
print('member합≈-grand 시그니처 =',flip,'(목표 0)')
for f in flips[:40]: print('  FLIP',f)
"
```

## 7. 완료 보고 양식 (이대로)
```
STATUS: DONE | DONE_WITH_CONCERNS | NEEDS_CONTEXT | BLOCKED
Step1~7: 각 [x]/[ ] + 증거 원문(명령+출력)
최종 검증 4기준: 시그니처 / pytest / backtest / 00131054 각 결과 원문
시그니처 잔여(있으면): corp/year/label별 분류표(혼재정당 / NaN미공시 / 진짜결함)
task#5 판정 + STATE/COVERAGE 갱신 제안 문안
미완·우려: 정직하게 전부
```

신뢰 규칙: 시그니처>0의 정직한 보고(DONE_WITH_CONCERNS + 해부)는 정상 경로다. 0으로
둔갑시킨 거짓 DONE은 재측정에서 드러나고 트랙 전체를 재검증하게 된다.
```
