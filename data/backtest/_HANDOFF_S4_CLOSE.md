# 핸드오프 — Phase1 S4(정규화 정합) 클로즈 + 다음 할 일

> 2026-06-14 작성. **컴팩트 후 이 파일부터 읽고 재개.** 작업 디렉터리:
> C:\Users\ghdtj\workspace\portfolio\fs-multi-analyzer · 진입점: docs/agent/STATE.md 최상단.

---

## A. 닫힌 것 (DONE — 이번 세션 완료·검증)

홀리스틱 공장이 찾은 P1 결함 원장(`data/backtest/_P1_DEFECT_LEDGER.md`)의 **높음 13 중 11 FIXED**.
회귀: **pytest 203 passed,1 xfailed · 클린 백테스트 분식 recall 5/6**(둘 다 실측).

| 결함(회사) | 수정 메커니즘 | 파일 |
|---|---|---|
| 영업이익=매출 (00545716) | company_quirks(영업수익→매출+영업이익복원). ripple로 단일사 확정 | config/company_quirks.yaml (신규) |
| 자본금 소계점유 (27+사) | ①dedup 비충돌우선(Fix A) ②매퍼 `label_priority_ids`(라벨채택) ③`_enforce_capital_decomposition`(자본금≈보통주+주발초 정확일치→납입자본 강등·leaf 승격, 자본잠식/우선주 무영향) | src/normalize/{pipeline,config,mapper}.py + canonical_accounts.yaml |
| 금융업 2부문 BS -52조 (00176914) | 금융업자산/부채 canonical 신설(미분류 52조 표면화)+리뷰 항등식 2부문 인식 | canonical_accounts.yaml, _p1_company_review.py |
| 발행사채→주식발행·만기보유←FVPL·투자부동산유령 | `label_priority_ids` 일반규칙(충돌행만·같은 statement만 작동) + '발행사채의 증가' alias | canonical_accounts.yaml, mapper.py |
| dump 표시착시(89만원→큰숫자) | 일괄 ÷1e6(gpt-5.4 거짓경보도 제거) | _p1_company_review.py |
| 보험비용↔보험서비스비용 이름뒤바뀜 | account_id 맞바꿈 | canonical_accounts.yaml |

**신규 메커니즘(범용·재사용)**:
- `CanonicalAccount.label_priority_ids` (config.py) + 매퍼 충돌분기 라벨채택 + **★statement 가드**(같은 표일 때만 — 자가감사로 CF→SCE 교차표 누수 버그 발견·수정). 부수효과: 110+ 회사연도 충돌행 교정.
- `_enforce_capital_decomposition` (pipeline.py): 값 기반 분해 사니티.
- `company_quirks.yaml` 첫 실가동(이전엔 빈 파일).

**자가 적대감사(40-F) 통과**: Fix A flip 112표본 0건 · 피팅 전수 1사 · 역검증 무회귀 · decomposition 무결 · label_priority 교차표버그 1건 발견·수정.

**⚠ 코드 6파일 미커밋**(git status: M canonical_accounts.yaml·config.py·mapper.py·pipeline.py / ?? company_quirks.yaml·_p1_company_review.py). 커밋은 사용자 지시 시.

---

## B. 진행 중 (async — 차기 세션 첫 확인)

- **corpus persist**: `renormalize_all --force` 백그라운드 실행(task b490i6d9g). 마지막 확인 250사 err=0 순항. **정확성은 코드fix에 이미 반영·검증됨**, 이건 저장 duckdb 새로고침일 뿐.
  - 차기 세션: `tail` task 출력 or `PYTHONPATH=. uv run python -m src.normalize.renormalize_all`(--force 없이 재개) 로 완료 확인. err=0 확인하면 persist DONE.

---

## C. 해야 할 것 (TODO — Phase1 종료까지)

**Phase1 종료 = S11 게이트. 현재 S3~S11 미완.** 단일출처: `docs/agent/COVERAGE_REMEDIATION.md`.

### C-1. S4 잔여 (정합 축 마무리)
- [ ] **member-sign 334건 트랙** (00298687 등): SCE member 셀 부호반전. 전용 프롬프트 `data/backtest/_P1_MEMBER_SIGN_FIX_PROMPT.md`. **단일사 얕은수정 금지**(메모리 member-sign-shallow-fix 교훈) — systematic.
- [ ] **01406618**: CF 4행 idiosyncratic 비표준태깅, 올바른 canonical 모호 → 신중 quirk(저가치·단일사).
- [ ] **S4 literal**: IFRS16 사용권자산·리스부채 alias 보강 + 관계기업투자 alias 16사 확인(COVERAGE_REMEDIATION S4 완료기준).
- [ ] S4 정식 [x] 종료 + COVERAGE_REMEDIATION 갱신.

### C-2. S3 확인
- [ ] S3(CIS/SCE 신호) 최근 커밋 df4e1c8가 했다고 표기되나 문서 [ ] — 실제 완료 검증 후 [x].

### C-3. S5~S10 (미착수 — 신규 수집·신호, Phase1 큰 덩어리)
- [ ] S5 절대수준 이상신호(DIO·부채비율·이자보상배율 절대임계) ← **다음 코딩 진입점 후보**
- [ ] S6 분기·반기 수집(reprt_code 11012~14)
- [ ] S7 사업보고서 원문 주석(개발비·무형자산·관계기업)
- [ ] S8 감사보고서 KAM·감사의견
- [ ] S9 정정공시 이력(=분식 자인 신호)
- [ ] S10 report 28종·event 36종(특수관계자·CB/BW)

### C-4. S11 종료 게이트
- [ ] 16분식사 각 분식이 결정론/LLM 인계 어디로 가는지 빠짐없이 매핑 + 정상사 거짓양성 재측정.

---

## D. 검증 baseline (회귀 가드 — 차기 세션 유지할 것)
- pytest: `PYTHONPATH=. uv run python -m pytest tests/ -q` → **203 passed, 1 xfailed**
- 백테스트: `PYTHONPATH=. uv run python -m src.backtest.run_backtest` → **분식 recall 5/6**(세토피아만 miss "변동미미")
- live 재판정: `PYTHONPATH=. uv run python data/backtest/_p1_ledger_livecheck.py` → **FIXED=11/13**(잔존 2=member-sign·01406618 = 의도적 보류)
- ★주의: 백테스트는 두산(24조·3년) 첫 회사가 느림(~몇 분). hang 아님. **돌리는 중 다른 uv 폴링 금지**(경합으로 느려짐) — jsonl 행수로 진행 확인.

## E. 다음 진입점 (택1)
1. **persist 완료 확인** → S4 잔여(member-sign 334 트랙) 또는
2. **S5(절대수준 이상신호)** 착수 — S4 잔여는 별 트랙으로 두고 Phase1 폭을 넓히는 쪽.

(현재 contract: `.claude/state/contracts/5372d147-...md` — 40-G까지 전 항목 [x]/[~] 통과. 새 회차는 새 블록 선언.)
