# 작업: 배치 러너 병렬화(Phase0) + SCE 부호 정규화 member 셀 누락 수정(본작업)

> 한 프롬프트, 두 페이즈. **Phase0(병렬화)을 먼저 끝내고 검증한 뒤** 본작업(member 부호)으로
> 넘어간다. Phase0이 빨라진 러너로 본작업 §6 검증을 싸게 돌린다.
>
> 발견 경위: 사용자 의심("여태 수정한 것 뭉갠 것 아니냐") → 독립 오라클 전수 감사로
> **-abs 부호 정규화가 grand-total('-') 셀만 뒤집고 member 구성요소 셀은 raw 부호 방치** 확인
> (313 회사연도 중 334건). 과수축/마스킹 무혐의(grand 검산·recall 유효), **얕은 수정**이 문제.
> 오라클: `data/backtest/_sce_overcollapse_audit.py`.

---

# PHASE 0 — 배치 러너 병렬화 (먼저, 독립 검증)

## P0.1 목표
- `data/backtest/_p1_review_all.py`의 회사연도 루프를 병렬화해 회귀 배치를 ~6-8배 단축
  (known 19건 63초→~10초). **출력은 직렬판과 바이트 동일**해야 한다(순서·내용·FAIL 집계).

## P0.2 배경 (검증된 사실)
- 현재 `main()`의 `for corp, fy in tgts:` 루프가 회사연도마다 `subprocess.run`(dump 생성)을
  **직렬** 호출. 회사연도당 ~3.3초, 전 라운드 회귀 ~383건=~21분 직렬.
- 각 회사연도 작업은 완전 독립(독립 duckdb read-only + 독립 subprocess). subprocess.run은
  대기 중 GIL을 놓으므로 **ThreadPoolExecutor로 효과적 병렬**.

## P0.3 설계 (이대로)
- 루프 본문(machine_checks + subprocess + dump 가공 + `_parse_summary`)을 순수 함수
  `_process_one(corp, fy, env) -> (corp, fy, c, dump)`로 추출(부작용 없음 — 파일쓰기/print 제외).
- `from concurrent.futures import ThreadPoolExecutor`, `max_workers = min((os.cpu_count() or 4), 16)`.
- `results = list(ex.map(lambda t: _process_one(t[0], t[1], env), tgts))` — **ex.map은 입력 순서
  보존**하므로 results가 tgts 순서. 그 뒤 기존 순차 블록(dump 파일쓰기·all_dumps append·fail_rows·
  print·matrix)을 results 순회로 그대로 수행 → 출력 순서·내용 불변.
- 다른 로직(판정 기준·포맷·matrix)은 **일절 변경 금지**.

## P0.4 단계 (순서 고정)
- [ ] P0-Step1: **변경 전** known 배치 stdout을 golden 저장:
      `PYTHONPATH=. uv run python data/backtest/_p1_review_all.py > /tmp/golden_known.txt 2>&1`
      증거: 파일 생성 + 줄 수
- [ ] P0-Step2: `_process_one` 추출 + ThreadPool 병렬화 구현.
- [ ] P0-Step3: **변경 후** 동일 명령 재실행 → golden과 diff **빈 차이**:
      `PYTHONPATH=. uv run python data/backtest/_p1_review_all.py > /tmp/after_known.txt 2>&1; diff /tmp/golden_known.txt /tmp/after_known.txt`
      증거: diff 출력 **공백**(완전 동일). 차이 있으면 P0 BLOCKED.
- [ ] P0-Step4: 속도 측정 `time (... known 배치)` — 직렬 대비 단축 확인(증거: real 시간).
※ P0 검증(diff 공백) 통과 전 본작업 진입 금지.

---

# 본작업 — SCE 부호 정규화 member 셀 일관 적용

## 1. 목표
- 차감변동(배당·신종자본증권 등)의 부호 정규화를 grand-total('-') + 전 member 셀에 **동일 적용**
  해 한 변동행 내부 정합(member합 == grand)을 회복.
- 성공 기준: member합≈-grand 시그니처 **334 → 0**, 회귀 무.

## 2. 컨텍스트
- 읽을 파일: `src/normalize/sce.py`(`_as_deduction`/부호 적용 지점 — 현재 bare/grand에만
  적용되는지 확인), `tests/test_normalize.py`.
- 증거(00131054/2023 현금배당금): grand('-')=-5,510(정상), 이익잉여금 member=+5,510(raw 방치).
  전수 334건 member합≈-grand. 검산(§F)은 grand만 봐서 이 불일치를 못 봄.
- 무혐의 확인: 과수축/마스킹 아님 — grand 검산·recall 5/6 유효. member 레이어 정합만 문제.

## 3. 설계 (이대로)
- 차감 판정(`deduction_sign`이 'minus')된 변동행의 **모든 셀(grand '-' + 전 member component_std,
  NaN 제외)에 동일 부호 변환** 적용. 현재 적용 범위를 코드로 먼저 확인하고 member 누락분 포함.
- **N2-d(라운드7) 가드 유지**: 구성요소 부호가 혼재(자본 내 대체, +/-)인 행은 애초에 차감 목록
  밖이어야 함 — 그 행 member 부호 불변. 즉 "차감으로 판정된 행"에 한해 전 셀 -abs.
- member 셀이 NaN인 변동(브레이크다운 미공시)은 불변(NaN 유지).
- 설계와 현장 불일치 시 **STATUS: NEEDS_CONTEXT**.

## 4. 단계 (순서 고정)
- [ ] Step1: RED — ①배당 합성행: grand·member 셀 모두 음수 기대(현재 member 양수라 실패)
      ②자본 내 대체(혼재부호) 행 member 불변 가드 ③member합==grand 불변식.
      증거: `uv run python -m pytest tests/ -q -k "member_sign"` 출력(failed 포함)
- [ ] Step2: 전 셀 부호 적용 구현 → GREEN. 증거 원문.
- [ ] Step3: 재정규화 — 전 감사 회사연도(known+round1~12, `--force`). 증거: error=0.
- [ ] Step4(마지막): §6 검증.
※ 단계 증거 원문 필수.

## 5. 금지 사항
- 하드코딩(corp/금액/라벨) 금지. 테스트 약화 금지 — 라운드1~12 검산 OK·recall 무회귀
  (member 부호는 grand 검산을 안 바꿈, member만 정렬).
- 수정 가능: **Phase0** `data/backtest/_p1_review_all.py`(병렬화 한정, 출력 바이트 동일);
  **본작업** `src/normalize/{sce,config}.py`·`tests/`. **건드리면 실패**: 검산 grand 로직,
  signals/backtest, 정답지·표본 json, 하니스의 판정/포맷 로직(병렬화 외).
- 체크리스트 생략·실패를 완료로 보고 금지.

## 6. 최종 검증 (슬림 — 시그니처 1차 + known + 카나리, 병렬 러너로)
- **(1차 지표) 시그니처 0 증명**: member합≈-grand 카운트 스크립트(아래 §6-script) 재실행 →
  **334 → 0**.
- **known 배치**(병렬) → 기계검사 바닥 전수 PASS(recall 가드 baseline).
- **카나리 1개 — round11 배치**(병렬, 차감 보유사 다수: 배당·신종자본증권) → 기존 허용 잔여만,
  신규 FAIL 0.
- **backtest 1회** → recall 5/6(부호 member 변경이 grand 미변경이라 무영향 예상, 확인 사살).
- **pytest 전체 1회**(반복 중엔 `-k member_sign`만) → 전체 passed.
- 전 라운드(round1~10·12) 전수 배치는 위 4개 통과 시 **마지막 1회만**(병렬이라 저렴) — 무회귀.
- (직접 증거) 00131054/2023 duckdb: 현금배당금 이익잉여금 member = **-5,510**.

### §6-script (시그니처 카운트, 그대로 실행)
```
uv run python -c "
import duckdb,json,pandas as pd
from pathlib import Path
from itertools import combinations
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
flip=0
for corp,fy in T:
 db=Path(f'data/companies/{corp}/{fy}/analysis.duckdb')
 if not db.exists(): continue
 con=duckdb.connect(str(db),read_only=True)
 if 'sce_equity_components' not in {r[0] for r in con.execute('SHOW TABLES').fetchall()}: con.close(); continue
 df=con.execute(\"SELECT fs_div,change_label,component_std,amount FROM sce_equity_components WHERE change_role='leaf'\").fetchdf(); con.close()
 if df.empty: continue
 df['amt']=pd.to_numeric(df['amount'],errors='coerce')
 for (fs,lab),g in df.groupby(['fs_div','change_label']):
  gr=g[g['component_std']=='-']['amt'].dropna()
  if gr.empty or abs(float(gr.iloc[0]))<1e6: continue
  gv=float(gr.iloc[0]); mem=g[~g['component_std'].isin(AGG)]['amt'].dropna()
  if mem.empty: continue
  ms=float(mem.sum())
  if abs(ms+gv)<1e6 and abs(ms-gv)>=1e6: flip+=1
print('member합≈-grand 시그니처 =',flip,'(목표 0)')
"
```

## 7. 완료 보고 양식
```
STATUS: DONE | DONE_WITH_CONCERNS | NEEDS_CONTEXT | BLOCKED
Phase0: P0-Step1~4 [x] + diff 공백 증거 + 속도 단축 수치
본작업: Step1~4 [x] + 각 단계 증거 원문
최종 검증(§6 6항) 원문 / 변경 파일 / 미완·우회·우려(201 기타 불일치 분류 포함)
```

---

## 부록: 기록 (대상 아님 — 삭제 금지)
- 교훈: 검사 범위 ≠ 데이터 범위. 검사가 보는 축(grand)만 고치면 안 보는 축(member)은 영영
  방치. 향후 member합==grand 불변식을 검산/하니스에 영구 편입(재발 게이트) — 본작업 후 별도.
- "201 기타 불일치"(부분공시 granularity 추정)는 본 수정으로 일부 해소 가능, 잔여만 별도 보고.
- 후속: 라운드13(20사 재검, seed=13)에서 구조규칙(R12)이 라벨 변주에도 신규 0 내는지 = 진짜 수렴.
