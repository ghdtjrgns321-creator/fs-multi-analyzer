# TROUBLESHOOT — 문제 해결 기록 (사람용)

> 프로젝트 진행 중 만난 문제·원인·해결을 **시간순으로 누적**한다.
> 회고·포트폴리오·면접 대비용. AI 작업 상태 스냅샷은 [../agent/STATE.md](../agent/STATE.md).

## 기록 형식

```
### [YYYY-MM-DD] 제목
- 증상: 무엇이 어떻게 안 됐나
- 원인: 근본 원인 (systematic-debugging 4단계)
- 해결: 무엇을 바꿨나
- 교훈: 다음에 어떻게
```

---

## 기록

### [2026-06-07] 소급재작성 12/16 baseline과 전 sj_div 확장 결과 불일치

- 증상: S2 restatement 신호를 의뢰 범위대로 BS/IS/CF/CIS/SCE 전부에 적용하자 16개 positive
  회사 중 15개에서 신호가 발생했다. 의뢰서의 기대값은 12/16이고 모델솔루션·본느·이트론·에스엘
  0건이었다.
- 원인: 12/16 baseline은 사실상 BS line item 중심 측정과 일치했다. 전 `sj_div`로 확장하면
  본느·이트론·에스엘에서 CIS/CF/SCE 구성항목 재분류, 자본변동표 표시, 현금흐름 부호 표시 차이가
  1억+1% 임계를 넘는다. 이것도 비교표시 괴리지만 분식 직격 재작성과 같은 의미로 해석하면
  거짓양성 성격이 커진다.
- 해결: 코드는 의뢰서의 전 `sj_div` 탐지를 유지하고, restatement `scan_key`는 canonical보다
  좁은 `account_id+label` line item 기준으로 잡아 서로 다른 표시항목 혼합을 줄였다. 문서에는
  전 `sj_div` 15/16과 BS-only 12/16을 분리 기록했다.
- 교훈: 재작성 신호는 BS 같은 잔액 항목에서는 강한 감사 신호지만, CIS/CF/SCE에서는 재분류·표시
  부호 변경 가능성이 크다. S2 이후 L4 change 관점은 `sj_div`와 evidence를 보고 의미를 분리해야 한다.

### [2026-06-07] 소급재작성 신호 거짓양성 억제

- 증상: S2 restatement 신호가 분식 직격 앵커를 잡지만 정상사에서도 표시 재분류·단위혼입·소계 증식
  성격의 신호가 남았다.
- 원인: 자산총계·자본총계 같은 소계가 구성요소 재작성을 중복 반영했고, `prior_amount`와 전년
  `amount`의 스케일이 100배 이상 벌어지는 단위혼입 후보도 같은 신호로 처리했다. 또한 1억 이상이지만
  대상 회사 자산 규모에는 작은 정당 재분류가 남았다.
- 해결: `restatement.py`에서만 소계 제외, rel 1000% 이상 또는 스케일 100배 이상 제외,
  자산총계 1% floor, 동일 `(account, fs_div, year, diff)` dedup을 적용했다.
- 교훈: 비교표시 재작성은 raw 금액 괴리만으로 충분하지 않다. 잔액 구성요소 중심으로 보고,
  소계·단위·회사 규모를 동시에 통제해야 감사 검토 후보로 쓸 수 있다.

### [2026-06-07] Restatement 결정론 큐 제외

- 증상: 억제 후에도 소급재작성은 회계정책 변경, 중단영업 재분류, EPS 소급재계산, 오류수정,
  사업결합 잠정조정, 연결범위 변동처럼 정상 사유가 많아 결정론 큐에서 거짓양성 후보가 될 수 있었다.
- 원인: 금액 괴리만으로는 "분식성 하향 재작성"과 "정당한 소급 표시"를 결정론적으로 구분할 수 없다.
- 해결: `restatement_signals`를 L4 `review_queue` 합산에서 제거하고, change material의
  `restatement_signals` 단서로만 유지했다. change 관점 프롬프트에는 정상 소급 사유와
  하향 재작성 패턴 판단 기준을 명시했다.
- 교훈: Restatement는 좋은 단서지만 결정론 점수는 아니다. LLM/사람 검토가 재작성 사유와
  계정 성격을 함께 판단해야 한다.

### [2026-06-07] DART 커버리지 감사 범위 축소 오판

- 증상: DART 데이터 커버리지 "전수 감사" 요청에 대해 최초 산출물이 표본 마지막 대상연도와
  preferred fs_div 중심의 부분 감사로 작성됐다.
- 원인: 전수 범위를 시간·API 호출 부담 관점에서 임의 축소했고, 로컬 데이터 기반 코드 대조를
  DART API/전연도/CFS·OFS 전수 확인의 대체물처럼 취급했다.
- 해결: `COVERAGE_AUDIT2.md`를 재작성했다. positive 16사 + 정상 10사 + 삼성전자 1사의
  회사-연도 119개, CFS/OFS raw 계정 39,612행을 전수 운명표로 재집계하고, report code 4종,
  report API 28종, event/regstate/share/list API 행수 확인을 추가했다.
- 교훈: "전수/전체/all/full" 요청은 비용·시간·rate limit 때문에 샘플·부분·로컬 캐시 분석으로
  대체하지 않는다. 완료 전 요청 모집단과 실제 커버 모집단을 비교한다.

### [2026-06-02] Gemini 3.5 Flash live Finding 생성 503

- 증상: `uv run python -m src.agents.first_finding` 실행 시 두 번 모두 Google API가
  `503 UNAVAILABLE`을 반환했고 실제 `AccountFinding`이 생성되지 않았다.
- 원인: API 키와 PydanticAI 연결은 동작했지만, `gemini-3.5-flash` 모델이 high demand
  상태였다. 프로젝트 제약상 OpenAI 또는 다른 Gemini 모델로 우회할 수 없었다.
- 해결: L2 threshold 판정, PydanticAI 수치 분석가, EvidenceRef/confirm_question guardrail,
  fake LLM 테스트는 완료했다. live Finding 생성은 [../agent/FINDING_REPORT.md](../agent/FINDING_REPORT.md)에
  보류로 기록했다.
- 교훈: 모델 고정 요구가 있는 단계에서는 실패 원인을 모델 가용성으로 분리 기록하고,
  대체 모델을 임의로 쓰지 않는다. 모델이 회복되면 같은 명령을 재실행한다.

### [2026-06-02] Gemini 일시 오류 자동 재시도 추가 후 첫 Finding 생성

- 증상: `gemini-3.5-flash`의 503/UNAVAILABLE 같은 일시 오류가 발생하면 사람이 같은 명령을
  수동 재실행해야 했다.
- 원인: `src.agents.numeric_analyst`가 PydanticAI `Agent.run()`을 한 번만 호출했고,
  `ModelHTTPError(status_code=503)` 같은 일시 오류를 분류하거나 백오프하지 않았다.
- 해결: Gemini 호출부에 최대 5회 지수 백오프+jitter 재시도를 추가했다. 4xx 영구 오류는
  재시도하지 않으며, 선택 fallback은 `gemini_fallback_model` 설정으로만 켤 수 있고 Gemini
  패밀리로 제한했다. 재시도 테스트와 ruff를 통과했고, `uv run python -m src.agents.first_finding`
  재실행으로 첫 `AccountFinding`을 생성했다.
- 교훈: 라이브 모델 과부하처럼 정상 코드 바깥의 일시 장애는 호출 경계에서 정책화하고,
  fallback은 기본 비활성으로 두어 모델 고정 조건을 깨지 않는다.

### [2026-06-02] D82242 주석 분석가 live 보강 503/timeout

- 증상: 매출채권 D82242 주석 인덱서와 주석 분석가 mock 테스트는 통과했지만,
  `uv run python -m src.agents.first_note_finding` 최종 live 실행에서 Gemini 3.5 Flash가
  503을 5회 반환하거나 장시간 응답하지 않아 timeout됐다.
- 원인: 코드·키·주석 파싱은 동작했으나 모델 가용성이 불안정했다. 주석 분석가도 기존
  Gemini 재시도 정책을 사용하므로 일시 오류는 자동 재시도 후 명확한 오류로 종료된다.
- 해결: live 보강 Finding은 보류했다. 실제 D82242 인덱서는 `note:D82242:CFS:2023:2`,
  `:4`, `:5` 섹션에서 손상·대손·신용위험·연체 키워드를 추출했다.
- 교훈: LLM 보강 전 단계의 주석 인덱싱 결과를 별도 검증 가능하게 두면, 모델 과부하와
  파싱 문제를 분리해 추적할 수 있다.

### [2026-06-02] 외부 ContextBrief Google Search grounding 503

- 증상: 외부 업황·뉴스 맥락을 `ContextBrief`로 수집하는 코드는 mock 테스트를 통과했지만,
  live 실행에서 `gemini-3.5-flash`가 503 high demand를 반복 반환했다.
- 원인: 수치 Finding 재생성 단계와 ContextBrief 단독 호출 모두 모델 가용성 문제로 실패했다.
  코드 경로는 기존 Gemini 재시도 helper를 사용해 5회 재시도 후 명확한 오류로 종료했다.
- 해결: live 외부 맥락은 보류했다. 출처 없는 항목과 grounding URL과 매칭되지 않는 항목을
  버리는 검증, Finding 판단 필드 비오염 테스트는 완료했다.
- 교훈: 외부 검색 맥락은 재무 데이터 기반 판단과 분리하고, 모델 가용성 문제가 있어도
  Finding 자체가 바뀌지 않게 유지한다.

### [2026-06-02] 재고자산 Finding live 생성 503

- 증상: 재고자산 L2 신호와 D82638 주석 섹션은 추출됐지만,
  `uv run python -m src.agents.first_inventory_finding` 실행에서 Gemini 3.5 Flash가
  503 high demand를 5회 반환했다.
- 원인: 재고 파이프라인 코드와 설정은 mock 테스트로 동작 확인됐고, 실패 지점은 수치 분석가
  live LLM 호출이었다.
- 해결: 실제 L2 신호와 실제 D82638 주석 섹션을 사용하고 numeric/note 분석가만 mock으로
  대체해 재고 Finding 산출 형태를 검증했다. 범용 계정 파이프라인을 추가해 다음 계정은
  config 추가 중심으로 진행할 수 있게 했다.
- 교훈: 계정 확장 검증은 결정론 신호·주석 인덱싱·LLM 호출을 분리해야 한다. 모델 과부하가
  있어도 계정 추가 비용과 일반화 상태는 mock으로 검증할 수 있다.

### [2026-06-02] L4 멀티에이전트 관점 평가 503

- 증상: `src.report.multi_agent` live 실행에서 수치 관점과 주석 관점 모두
  `gemini-3.5-flash` 503 `UNAVAILABLE`을 반환했다.
- 원인: 모델 일시 과부하로 추정한다. 코드·키 문제로 단정하지 않는다.
- 해결: 관점별 LLM 호출에 per-call timeout과 deferred assessment를 추가했다. 결정론
  review queue와 지표 요약은 유지하고, 완료된 관점이 2개 미만이면 교차 판정은
  `insufficient`로 표시한다.
- 교훈: L4에서도 모델 호출 실패는 관점 단위로 격리해야 하며, 결정론 큐를 LLM 성공 여부와
  분리해야 한다.

### [2026-06-02] L4 모델 전환 후 4관점 live 완료

- 증상: `gemini-3.5-flash` 지속 503 때문에 L4 live 멀티에이전트 결과를 확인하지 못했다.
- 원인: 코드 문제가 아니라 특정 모델의 high demand로 판단했다.
- 해결: 메인 모델 기본값을 `gemini-2.5-flash`로 바꾸고, L4 실행점도 공용 5회 재시도
  정책을 사용하게 했다. 주석 관점 material은 실제 섹션 위치를 유지하되 발췌 길이를 줄이고,
  발췌 누락을 공시 누락으로 단정하지 못하게 프롬프트를 보강했다. 이후 수치·주석·흐름·변동
  4관점 live 평가가 completed로 나왔다.
- 교훈: live LLM 검증은 모델명 중앙화, 공용 재시도 정책 적용, 관점별 입력 크기 관리가 함께
  필요하다.

### [2026-06-02] Google Search grounding JSON schema 조합 400

- 증상: 외부 맥락을 L4 5번째 관점으로 승격한 뒤 live 실행에서 Google API가
  `400 INVALID_ARGUMENT`와 함께 `Tool use with a response mime type: 'application/json' is unsupported`를
  반환했다.
- 원인: Google Search tool 사용 시 `responseMimeType="application/json"`과 `responseSchema`를
  함께 지정한 조합이 지원되지 않았다.
- 해결: Search grounding tool은 유지하고, JSON 강제는 프롬프트와 응답 텍스트 파서로 처리했다.
  출처 URL이 grounding chunk와 매칭되지 않는 항목은 기존처럼 버린다.
- 교훈: grounding tool 호출은 구조화 출력 제약이 일반 LLM 호출과 다를 수 있으므로, 출처 검증과
  스키마 파싱을 분리해 둔다.

### [2026-06-03] 장기차입금 주석 live grounding 공백 차이

- 증상: `uv run python -m src.agents.account_finding --account 장기차입금 --year 2025`에서
  LLM이 D82240 주석의 실제 문구를 인용했지만 줄바꿈과 공백 차이 때문에
  `note_evidence value must be copied from the note section` 재시도가 반복되어 실패했다.
- 원인: 주석 텍스트는 표에서 추출되어 줄바꿈이 많고, LLM은 같은 문구를 한 줄로 합쳐 반환할 수
  있다. 기존 validator는 완전한 substring만 허용해 공백만 다른 실제 인용도 거부했다.
- 해결: `src.agents.note_analyst`의 grounding 검증을 공백 정규화 후 포함 여부로 바꾸었다.
  값 자체가 주석에 없으면 여전히 거부하므로 환각 방어는 유지된다.
- 교훈: HTML 표 기반 주석 grounding은 의미 없는 공백 차이를 허용하되, 숫자·단어 순서가
  바뀌는 인용까지 허용하지 않도록 좁게 정규화한다.

### [2026-06-06] 정상 노이즈 309개의 진짜 원인 — 하한선(floor) 계산 버그

- 증상: 전수 백테스트에서 정상회사 110사의 top10에 강도10(만점) 신호가 309개 쏟아졌고,
  분식계정(아스트 재고)이 0근처-% 폭발 신호에 밀려 16위로 매몰됐다. 이를 보고 "신호 순위
  재정렬(FIX 3)이 필요하다"고 판단했다.
- 원인: universal 스캔의 materiality 하한선 계산에서, 자산총계가 소계 제외 단계
  (`_exclude_subtotal_rows`)를 먼저 거쳐 빠진 뒤 `scale_floors`가 호출됐다. 자산총계가
  없으니 상대 하한(자산×1%)이 0으로 계산되고 절대 하한 1억만 남아, 회사 규모와 무관하게
  floor가 1억으로 추락했다. 그래서 먼지 계정의 %폭발이 전부 통과해 강도10을 도배했다.
- 해결: 소계 제외 *전* frame으로 floor를 계산하도록 순서를 바꿔 자산×1% 상대 하한을 복원했다
  (현대건설 2023 자산 237,145억 → floor 2,371억, 자산1% 정확 일치). 강도10 신호 309→109개로
  격감, 아스트 재고 16→6위·셀트리온 재고 13→3위로 *옛 잣대에서도* 상승했다.
- 교훈: "정상 노이즈처럼 보이는 대량 신호"를 신호 로직 문제로 단정하기 전에 **하한선·정규화
  같은 전처리 입력을 먼저 의심한다.** 재정렬(FIX 3)이 필요하다고 본 근거의 상당부분이 사실
  floor 버그였다 — 한 케이스(아스트)가 아니라 분포 전체(309개)가 흔들릴 땐 개별 신호가 아니라
  공통 입력(floor)을 본다.
