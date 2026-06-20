# 동의어 dedup + 온보딩 게이트 — Context & Decisions

## Status
- Phase: 설계 완료(미착수)
- Progress: 0 / 6 phases
- Last Updated: 2026-06-14

## Key Files

**Modified(예정)**:
- `config/canonical_accounts.yaml` - 동의어 canonical 통합(생존 블록 흡수 + 중복 키 삭제, minimal edit)
- `src/normalize/config.py` - `load_company_quirks` 로더 신설
- `src/normalize/pipeline.py` - `_apply_company_quirks` 후처리 pass 신설(_arbitrate_conflicts 다음)

**New(예정)**:
- `config/company_quirks.yaml` - 회사 고유 이탈 교정 스키마(corp_code 데이터 키)
- `src/normalize/onboarding_gate.py` - 게이트 러너(G1~G8 순차, 기존 스크립트 부품 재사용)
- `data/backtest/_dedup_candidates.py` - 592쌍 3분류 시드 + 생존자 제안
- `data/backtest/_apply_dedup.py` - decisions → yaml 편집 지시
- `data/backtest/_quirk_promote_scan.py` - 반복 quirk 3회+ 승격 후보 스캔
- `dev/active/synonym-dedup-onboarding-gate/_dedup_decisions.yaml` - 검수 판정(작업 산출물)

**참조(수정 안 함 — 부품화 대상)**:
- `data/backtest/_conflict_canonical_inventory.py` - 충돌 인벤토리(G2)
- `data/backtest/_is_cf_arithmetic.py` - IS/CF 산술검산(G3)
- `data/backtest/_f1_signal_dangling.py` - 신호 dangling(G5)
- `data/backtest/_p1_company_review.py` - 회사 dump(G1/G6)
- `data/backtest/_HOLISTIC_AUDIT_PROMPT.md` - 9렌즈 LLM 통독(G6)
- `src/normalize/pipeline.py:_arbitrate_conflicts` - 표 호환성 심판(선행 작업, 무회귀)

## Key Decisions

1. **선행 작업과 별개 task** (2026-06-14)
   - Rationale: `id-label-conflict-category-arbiter`는 충돌 런타임 심판(채택). 본 작업은 충돌 원인
     제거(dedup) + 잔여 흡수(게이트). 접근·산출물이 달라 분리.
   - Trade-offs: `_arbitrate_conflicts`를 양쪽이 공유 → 본 작업은 무회귀 유지만(수정 안 함).

2. **②동의어/③진짜오매핑 mechanical 분리 포기 → 게이트로 흡수** (2026-06-14, 사용자 측정 확정)
   - Rationale: coarse category·lexical·id 자카드 3종 분리 다 실패. ③은 irreducibly case-by-case.
   - Alternatives: 자동 분류 강행 → 거짓양성. 사용자가 게이트 흡수 채택.

3. **dedup은 사람 검수 전제 + 보수적 자동 후보** (2026-06-14)
   - Rationale: 유사도 신호 부재. 자동은 후보 좁히기(narrower/mistag 제외)만, 최종 synonym 판정은 사람.
   - 생존자 규칙: account_ids 개수 → ifrs-full 우선 → 일반명. 규칙 위반 선택은 reason 기록.

4. **세분화 보존 규제(통합 금지)** (2026-06-14)
   - Rationale: 유동리스부채↔리스부채는 id가 더 정확. 통합 시 정보 손실. 부분문자열+유동/비유동/
     순/총 접두 차이는 narrower로 자동 시드(통합 후보 제외).

5. **company quirk는 config 데이터(코드 분기 금지)** (2026-06-14)
   - Rationale: CLAUDE.md §3 하드코딩 금지. corp_code/year는 데이터 키로 흐름.
   - 3회+ 반복 quirk는 일반 패턴으로 승격(표 호환성처럼). 1~2회는 quirk 유지(YAGNI).

6. **게이트 종료조건: P1결함 0 + 기계검사 PASS, N=3 캡** (2026-06-14)
   - Rationale: LLM 확률성·비용 상한. 결정론 검사(G1~G5) floor, LLM(G6) 잔여만. 3회 미달은 수동 에스컬레이션.

## Known Issues

- **신호 dangling 위험**: dedup으로 canonical name이 사라지면 신호엔진 참조가 죽는다. 생존자 선정 시
  `_f1_signal_dangling.py`의 참조 canonical을 생존자 우선. dedup 직후 Layer A 0 검증 필수.
- **yaml 인코딩**: 11k줄 한글. minimal edit·mojibake 0·전체 재작성 금지. ruamel.yaml round-trip 또는
  Edit 블록 단위(ruamel 미설치 시 §8 확인).
- **게이트 LLM 비용**: G6 subagent 위임, N=3 캡. G1~G5 floor가 대부분 포착.
- **quirk 남용**: 3회+ 반복은 `_quirk_promote_scan.py`로 승격 강제.

## 측정 근거 (사용자 확정 — 재측정 불필요)

| 지표 | 값 |
|------|----|
| same-statement 충돌 distinct canonical | 592쌍 / 4,806행 |
| ②동의어/③진짜오매핑 mechanical 분리 | 불가(3종 신호 실패) |
| 진짜오매핑(③) 규모 | 소수(`_264_triage.md` 진짜충돌 9쌍 / 48행) |
| ① cross-statement | 해결됨(`_arbitrate_conflicts` 게이트 통과) |

## 검증 명령 (회귀 가드)

```bash
# 재정규화
PYTHONPATH=. uv run python -m src.normalize.renormalize_all --force [corp]
# 충돌 인벤토리(dedup 전후 비교)
PYTHONPATH=. uv run python data/backtest/_conflict_canonical_inventory.py
# 산술검산
PYTHONPATH=. uv run python data/backtest/_is_cf_arithmetic.py
# 신호 dangling
PYTHONPATH=. uv run python data/backtest/_f1_signal_dangling.py
# 백테스트 recall 5/6
PYTHONPATH=. uv run python -m src.backtest.run_backtest
# 단위/검산 baseline
uv run pytest tests/ -v
# 회사 dump(케이스 재현)
PYTHONPATH=. uv run python data/backtest/_p1_company_review.py <corp> <year>
# 게이트 러너(신설)
PYTHONPATH=. uv run python -m src.normalize.onboarding_gate <corp> <year>
```
