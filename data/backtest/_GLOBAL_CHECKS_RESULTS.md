# 글로벌 검사 결과 — F1 신호 dangling · IS/CF 산술검산 (2026-06-14)

> per-chunk 홀리스틱으로 **못 잡는** 전사(글로벌) 사각을 일회성 스크립트로 메운 결과.
> 두 스크립트는 회귀 검사로 재실행 가능(영구 보존).

## 1. F1 신호 dangling — `_f1_signal_dangling.py`

**질문:** 신호엔진(코드·playbook)이 참조하는 canonical 이름이 lump/rename으로 죽지 않았나?
죽으면 매칭 0행 → 분식 신호가 에러 없이 조용히 사망.

**방법:** 신호엔진이 참조하는 canonical 문자열을 전 출처에서 추출 → config 대조.
- 출처: `relationship_chains.yaml`(yoy_accounts·growth_divergences·direction_checks·direction_red_flags),
  `financial_ratios.yaml`(ratios.accounts), 코드 하드코딩(자산총계·부채총계·자본총계·매출채권·영업활동현금흐름).
- 2계층: Layer A(config 키 존재) = 게이트 / Layer B(corpus 실제 생성) = WARN.

**결과: 진성 dangling 0 — PASS.**
- 참조 56개 고유 canonical 전부 config 키에 존재(Layer A 0건).
- Layer B 1건(`공사손실충당부채`)은 감사 corpus 313cy에 0회였으나, **전체 모집단 4,771 DB 스캔으로
  정상 매핑 입증**: `dart_CurrentProvisionForConstructionLosses` → 공사손실충당부채 35행(+비유동 3행).
  건설사가 분식후보 corpus에 없을 뿐, 리네임 잔재 아님 → 게이트 제외.

**부수 관찰(별개 트랙):** 같은 account_id가 모집단에서 3 canonical로 갈림(공사손실충당부채 35 /
기타 중요 계정 21 / 충당부채 1). peer DB 구버전 정규화 잔재 의심 — F1 dangling과 무관, 추후 점검.

## 2. IS·CF 산술검산 — `_is_cf_arithmetic.py`

**질문:** BS(항등식)·SCE(roll-forward)만 산술검사가 있고 손익·현금흐름은 "금액 존재"만 봤다.
정의식(매출총이익=매출−원가 등)을 한 번도 기계로 안 걸었다 → 그 공백을 메운다.

**핵심 교훈 — 부호 규약이 회사마다 다르다(케이스 해부로 확정):**
- `매출원가`: 00117577 **+1,837B** vs 00861997 **−46B** (양수/음수 양쪽 저장)
- `법인세비용`: 00728638 **+28.9B** vs 00124106 **−126B**
- → raw 뺄셈도 abs도 단독으론 거짓경보. **차감계정은 −abs(항상 차감), 세금은 magnitude
  관계(|순익−세전|=|세금|)**로 흡수. 중단영업이 끼면 세후 계속영업 소계(계속영업당기순이익)를
  target으로, 그것도 없고 중단영업 P&L 있으면 SKIP.

**검산 식:**
- IS1: 매출총이익 = 매출 − |매출원가|  (경성)
- IS_tax: | |target − 세전| − |세금| | ≤ 100만원, target = 계속영업당기순이익(있으면) 또는 당기순이익 (경성)
- CF: 기말=기초+순증감, 순증감=영업+투자+재무+환율 (정보성 — 회사별 조정라인으로 잔차 정상)
- 제외: IS2(영업이익=매출총이익−판관비) — 판관비 외 영업비용 라인이 따로라 정의식 아님.

**결과: 313cy 중 302 통과, 11 잔차 — 전부 진짜 P1 후보(거짓경보 아님).**
수렴 과정(검사 자체를 4번 의심·수정): 235 → 53 → 13 → **11**.
- 11건 전부 보험/지주(00356361·00120526·00130772·00249502)에 집중.
- **근본 원인(00356361/2021 완전 해부):** `계속영업손익`(3,654,862B = 세전−세금)·`중단영업손익`
  (299,042B = 잔차) 두 소계가 **라벨·커스텀 account_id**라 config에 없어 `기타 중요 계정`으로 빠짐.
  `당기순이익 = 계속영업손익 + 중단영업손익` 정확 성립 → 검사가 **미매핑 소계를 정확히 적발**.
- **교차확인:** 00120526은 홀리스틱 chunk5가 독립적으로 "계속영업이익 중복매핑 P1후보"로 검출 →
  기계검사와 LLM 통독이 같은 결함을 양방향 확인.

**조치(P1 수정 후보):** config에 `계속영업손익`·`중단영업손익` 라벨 alias 보강
(→ 계속영업당기순이익·중단영업이익). 보강 후 IS_tax 잔차 0 수렴 기대.

## 실행

```
F1     PYTHONPATH=. uv run python data/backtest/_f1_signal_dangling.py
IS/CF  PYTHONPATH=. uv run python data/backtest/_is_cf_arithmetic.py        # 감사 corpus
       PYTHONPATH=. uv run python data/backtest/_is_cf_arithmetic.py --all  # 전체 모집단
```
