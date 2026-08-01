# STATE — 현재 작업 상태

> 새 세션·다른 프롬프트는 **이 파일부터** 읽는다. "지금 어디까지 됐고 다음은 무엇인가."
> 작업 종료 시 반드시 갱신한다. 전체 흐름은 [OVERVIEW.md](OVERVIEW.md), 상세 설계는
> [PLAN.md](PLAN.md), 할 일 전체는 [ROADMAP.md](ROADMAP.md).

## 현재 위치

- **✅ 아스트 2020 마스킹 실행 재실행 + 실행 산출물 단일화** (2026-08-01, `develop`). README·
  FINAL-REPORT가 정체 공개 실행(24장·53/53)과 마스킹 실행(21장)의 수치를 섞어 쓰던 혼선을 종결.
  - **재실행**: `blind_materials` 마스킹 + 외부검색 차단, 148초, 5관점 완주(실패 0), 검토 계정 296.
    결과 **카드 24장(계정13·관계4·회사7)**, recall@5=2/3(재고자산 rank1·매출원가 rank1·자기자본
    미적중), 검사1 **59/59 match PASS**. 이전 마스킹 실행의 21장은 재현되지 않았다(한계 #6).
  - **레거시 폐기**: 정체 공개 실행 산출물(`_score_00409681_2020.md` 구본·`_ast_2020_cards.json`)과
    카드목록 없는 마스킹 실행(`_rerun.md`), 구 수치 리포트를 삭제하고 이번 실행분을 정규 파일명으로
    승격. 아스트 2020의 근거는 `golden/hit/_score_00409681_2020.md` +
    `golden/numeric/_report_00409681_2020.md` **둘뿐**이다.
  - **반영**: README(카드수·59/59·영역별 표를 `issue_type` 집계로 재작성)·FINAL-REPORT
    0/2/9장·본 STATE. 영역별 표는 수기 분류 금지 — 이전 12/5/7 오기의 원인이 수기 분류였다.
  - **⏭ 미실행**: 골든 실데이터 테스트(`test_real_saved_cards_reconcile_clean`)를 새 저장 카드로
    아직 안 돌렸다. `uv run pytest golden/ -v`로 확인 필요.
- **✅ README 전면 재작성 — 개요 강화판** (2026-07-31, `develop`). 원기(k-ifrs-1115 README)
  골격을 따라 **개요(6소절) → 목차 → 본문 1~8**로 재편. 개요 6소절 = 프로젝트 소개 · 문제 인식 ·
  얻을 수 있는 것 · 핵심 설계 · 주요 성능 평가(아스트 1사 집중) · 실제 사용 스크린샷.
  본문은 원기 순서를 따라 **실증 예시(아스트 2020)를 기술 설명 앞**으로 이동, 기술 설명은
  3-1~3-5(수집·정규화 / 정합성 검증·LLM 전처리 / 계산엔진 / 멀티에이전트 5관점 / 카드·근거 대조).
  - **스크린샷 4장 신규 촬영**(playwright, 아스트 2020 저장 결과) — `docs/images/ui-flow-1~4*.png`.
    "카드만 있으면 뭐하는 프로젝트인지 모르겠다"는 피드백 반영해 검색→연도선택·실행→검토 큐→카드 순.
  - 계약 `_workspace/readme-outline.md` · 실측 대조 `_workspace/readme-factcheck.md`.
    대조로 확인: 표준계정 2,017 · dart 1,313 · ifrs 1,453 · 별칭 1,805 · 관계사슬 11 · 재무비율 15 ·
    발견 관점 5(+외부검증 1) · 아스트 카드 24(계정12·관계5·회사7).
  - 게이트: `align_diagrams --check-only` ALL OK, `check_style` FAIL 1건(§8 빠른 시작 — 사용자
    명시 요청에 의한 계약 예외). 714줄.
  - ⚠ 발견한 결함: `uv run streamlit run dashboard/app.py`가 `PYTHONPATH` 없이는
    `ModuleNotFoundError: dashboard`로 죽는다(Docker만 `ENV PYTHONPATH=/app`로 해결). README
    빠른 시작에 `PYTHONPATH=.`를 병기했으나, **근본 해결(패키지 설치 또는 `.streamlit` 설정)은 미착수**.
- **✅ 검증 스코어카드 신설 — README·FINAL-REPORT** (2026-07-20). 사용자 통찰("정답 없는
  프로젝트인데 recall/FP 성능표는 뭘 기준으로?")을 반영해 단일 성능표 대신 **정답 유무로 4축
  계층화**: ①수치충실도(DART 원천, 완전객관 — LG생건 72/72·아스트 59/59·환각0) ②제재적중(확정분식
  8사 좁은정답 — 아스트 재고 rank1·recall@5=2/3·셀트리온 2/2) ③신호 회귀 baseline(5/6, 성능아닌
  무회귀가드) ④큐 정밀도=**정답부재·측정안함**(이상변화 큐라 FP 부적합). **적용 범위 헤더**를
  스코어카드 위에 명시 — 관계사슬·비율·분해가 매출–매출원가–재고–공사진행 구조 전제라 **비금융
  (제조·판매·건설) 한정, 금융·보험·지주·리츠 미대응**(config id·정답지 계정으로 재현 확인).
  삽입: `README.md §4`(쉬운말·"뜻"컬럼)·`FINAL-REPORT/9_...md §9.0`(적용범위+표)·`0_README.md`
  핵심수치 아래 참조. README 한계 #3 "제조업 한정"→"비금융(제조·판매·건설)"로 정합.
- **✅ FINAL-REPORT 2차 전수 정합성 감사·교정** (2026-07-20). 7 근원 종결 후 "또 다른 불일치
  없나" 전면 재감사(분모 13문서, census PASS 13/13, 병렬 감사관 4인 + 설계자 재현 검증). 실질
  불일치 2계열 교정: ①**카운트 드리프트** — 관계사슬 9→11·변동분해 브리지 4→6·소계/대사 9·4→10·8
  (코드가 진실, 최근 커밋 미반영. 0_README·3·4·8장, 다수는 본문 옳고 표/도식만 어긋난 자기모순).
  ②**UI 2건 정직화** — 커버리지/blocked 경고가 markdown 리포트엔 있으나 Streamlit 카드섹션 미배선
  (`render_header_html`이 `render()`에서 미호출)·승인기각 판정기록 UI 미구현(7장).
  - **핵심 반전**: 감사관 A·D가 "골든 72/53이 틀렸다(실제 57/61)"고 봤으나, 낡은 건 문서가 아니라
    golden/numeric 산출물 파일이었다. 07-18 저장 카드로 `run_saved_cards` 재실행하니 문서 72/53이
    정확 → 산출물 2종 재생성으로 해소(문서 유지). figure_sheet와 동일 함정을 결정론 재현이 또 걸러냄.
  - 원장 `_workspace/final-report-audit/CLOSURE-FULL-2026-07-20.md`. 재무비율 15·2017계정 등 재현 일치.
  - ⚠ 잔여(경미): 정독 분모 파일수(1,626)는 census 스냅샷이라 재실행 시 자연 드리프트(12장 명시).
- **✅ FINAL-REPORT 치명 7 근원 종결** (2026-07-20). 2026-07-16 감사(SUMMARY.md)가 "현재 동작
  서술 신뢰 불가"로 지목한 치명 근원 7개를 현재 코드·문서로 재검증(병렬 감사관 2인, file:line +
  호출부 역참조). **6개는 07-18~20 후속 작업에서 이미 정합화됨**(발견 5관점·별칭 자동등록·
  external URL 미도달 명시·annotate 2곳·guardrails 구경로·head 상한 제거 — 전부 코드와 문서 일치).
  근원 5(figure_sheet)만 미배선 장치가 문서 3곳에서 활성으로 오독될 여지 잔존 → 교정
  (`6장:27` 표 ④에서 제거·`0장:69` 4중장치를 tool DSL로·`11장:16` "배선 보류" 부기). 6장:69
  본문은 기존에 이미 정직. 종결 원장 `_workspace/final-report-audit/CLOSURE-7ROOTS.md`.
  → **FINAL-REPORT 동작 서술이 코드 실체와 정합, 발표·README 재료로 사용 가능.**
  - **figure_sheet "583.1억 환각" 사건도 종결**: 결정론 데이터로 재현 — 583.1억은 as-filed
    series(아스트 2019 자산총계 578,756,230,211 → 2020 520,443,461,969 = YoY 583.1억)에 실재하는
    grounded 값, "환각 아님" 확정. "298.8억"은 재작성 비교치(prior 5,503.3억) 기준이라 도표밖.
    낡은 전제 4곳 교정(`11장:16` 행 재작성 · `figure_sheet.py` docstring+주석 · `test_figure_sheet.py`
    fixture/단언 뒤집기 7 passed · spec 정정 배너). 오판이 배선 보류의 근거였음이 확증됨.
- **✅ 사전지식 오염(data leakage) 점검 — blind 실행 대조** (2026-07-19). 정답지가 실명 확정
  사건이라 LLM 사전지식으로 정답을 찍었을 가능성을 실험으로 검증했다.
  - **신설 `src/report/blind.py`** — 관점 material에서 회사 정체만 제거(계정·금액 불변).
    파이프라인 무수정: `build_suspicion_cards`가 materials·external_verifier를 주입받으므로
    마스킹 재료를 넘기고 외부검색을 끄면 된다. 테스트 8건(`tests/test_blind.py`).
  - **실측(아스트 2020, 163초)**: 정체를 지워도 재고자산이 **최상위·숫자/추세 2관점 겹침**으로
    동일하게 잡히고, 매출↔매출원가↔재고 관계 카드도 흐름 관점에서 동일 생성. 카드 수는
    24 → 21(LLM 비결정성, 하위 3장 차이). **사전지식 의존 근거 없음.**
  - **마스킹 1차 구멍 3건 실측·보완**: 접두어 없는 맨 계열사명("오르비텍") · 프로필 원본 필드
    (종목코드·법인번호·대표자·영문명) · 영문 사명. 보완 후 5관점 재료 정체 표식 0건.
  - **조사에서 드러난 오염 경로(미차단, 스위치 없음)**: ① 업종 관점이 자사 실명+동종사 실명을
    필드로 받고 grounding 탈락도 면제 ② 사업보고서 발췌에 계열사명 원문 노출(주석 XBRL 회사명
    태그는 메타 제외로 이미 차단) ③ external_verify가 실명으로 구글 실검색(대상연도 이후 기사
    컷 없음). 사용자 지시로 README 8장 한계에는 안 넣고 4.7에만 기술.
  - ⚠ 미검증: 1회 실행 대조. 반복 실행 안정성·타사 blind 대조 미실시.
- **✅ 파생층 커버리지 원장 신설 — 미매핑의 사슬·비율 미진입을 계측** (2026-07-19).
  계정층 원장은 미매핑도 원문 라벨 키로 패널에 실리므로 '분석됨'으로 셌다. 그런데 관계사슬·
  재무비율은 **표준 계정명**으로 조회하므로 미매핑은 진입 자체가 불가 → 계정층 원장만 보면
  안 보이는 조용한 드롭이었다. `build_derived_ledger`(src/report/coverage.py)로 계측.
  - **항등식**: `population == entered + excluded + blocked`. blocked = 표준 이름이 없어 진입
    불가. excluded = 표준 이름은 있으나 사슬·비율 정의에 없음(정당) + 표 간 중복 방지 강등.
  - **작업 중 발견**: 원장 초안이 `series_key`로 세다 미매핑 N종이 `fs:기타 중요 계정` 1건으로
    뭉쳐 과소 집계(삼성 2건). universal.py·metrics_panel.py의 기존 규칙(**미매핑=원문 라벨**)에
    맞춰 정체성을 복원 → 삼성 9건으로 정정. 회귀 테스트로 고정.
  - **과대계상도 차단**: 현금흐름표의 `당기순이익`처럼 제 표(손익계산서)에서 이미 진입한
    동명 계정은 정당제외로 분류(삼성 9 → 7).
  - **실측**: 삼성 2024 모집단 208 = 진입 66 + 정당제외 135 + 진입불가 7(45.3조) ·
    대주 2024 모집단 237 = 49 + 176 + 12. 항등식 True.
  - **표면화**: `review_scope.derived_blocked`로 실어 마크다운 리포트·대시보드가 같이 읽는다.
    렌더 문구는 "관계사슬·재무비율 미진입 N건(금액) — 계정별 지표·카드에는 포함된다".
  - 테스트 `tests/test_coverage_derived.py` 8건 신설, 전체 **683 passed·1 xfailed**.
  - **판정 기준 교정(2차)**: 라벨 일치 휴리스틱을 버리고 **표준코드 보유 여부**로 갈랐다
    (alias_suggest.unmapped_accounts와 같은 기준). 오탐 실례 — 삼성 `보통주자본금`은 사전
    누락이 아니라 `자본금` 총계가 이미 매핑돼 이중계상을 막으려 강등된 것인데 누락으로 셌다.
    이제 blocked = **별칭 제안기가 실제로 고칠 수 있는 몫**과 같은 모집단이다.
    실측: 삼성 208 = 66 + 137 + **5** · 대주 237 = 49 + 178 + **10**(fs_div별 계수).
  - **교정 루프 연결**: 전처리 별칭 제안 화면이 제안 canonical이 사슬·비율 조회 계정(47종)에
    속하면 "★ 등록하면 관계사슬·재무비율에 편입되는 계정"을 표시한다. 처음엔 원장 blocked
    목록을 UI로 넘기려 했으나 두 가지로 폐기 — ⓐ save_cards가 원장을 저장하지 않고
    ⓑ 별칭 등록은 카드 생성 **전** 단계라 목록이 아직 없다. 게다가 제안 대상은 전부 미매핑이라
    "진입불가" 표시가 정보가 아니다. 실제 신호는 "등록 후 편입되는가"였다.
  - ⚠ 미검증: 대시보드 실화면 렌더는 눈으로 확인하지 않았다(코드 배선·임포트만 확인).
- **✅ README 4장(검증)을 아스트 단일 케이스 스토리로 재작성** (2026-07-19). 사용자 지시로 다른
  회사 M/N 로그·실 LLM E2E 실측 표는 삭제하고 아스트 2020 한 건만 남겼다(제재 경위 → 정정 전
  원본 입력 고정 → 카드 24장·정답 순위 → 못 잡은 것 → 수치 대조).
  - **재측정으로 드리프트 확인**: `golden/numeric/_report_00409681_2020.md`(07-14 생성)는
    N=61·대사불능 1건으로 낡았다. 저장 카드(07-18 실행) 재계산 결과 **53/53 match PASS**가 맞고,
    매출원가 순위는 기록된 5위가 아니라 **4위**(관계 카드). 근거는 `_workspace/readme-factcheck.md`.
  - **스크린샷 신규 1장** — `docs/images/ui-cards-04.png`(아스트 2020 재고자산 1위 카드 펼침).
  - ⚠ 미조치: 위 골든 리포트 파일 2종은 재생성하지 않았다(본문 수치는 재측정값 사용).
- **✅ 우선순위 가중치 폐지 — 정렬을 사전식 비교로 단일화** (2026-07-19). 사용자 판단:
  가중치(materiality 0.35·votes 0.30·anomaly 0.15·confidence 0.20)는 성분별 근거를 댈 수
  없어 자의적이다. `src/report/priority.py` 삭제, `AccountFinding.priority_score` 필드 제거,
  `config/investigation.yaml`의 `priority.weights` 블록 제거.
  - **신설 `src/report/card_order.py`** — 정렬 단일 출처. 사전식 3단: ①반박 정상우세는 하단
    (강등이지 제거 아님) ②표수 내림 ③금액 내림. 회사 카드는 금액 앵커가 없어 3축이 계정명.
    객체·dict 양쪽 지원(저장 카드가 dict로 흐르는 경로 때문).
  - **부수 발견·해소 — 화면과 리포트가 다른 순서였다**: 마크다운 리포트는 (정상우세, 표수, 금액)
    사전식인데 Streamlit `sort_cards`만 가중합 점수 내림이라 같은 분석 결과의 1등 카드가 보는
    곳마다 달랐다. 이제 화면·리포트·외부검증 선정이 `card_order` 하나를 쓴다(실측 확인).
  - **UI**: 카드 우측 "우선순위 0.87" 배지 삭제(사용자 선택) — 순서 자체가 우선순위를 말한다.
    마크다운 카드 표의 `점수` 컬럼도 제거.
  - 테스트: `tests/test_priority.py` 삭제, 정렬·저장·외부검증 테스트를 정렬 성분(vote_count·
    materiality_score) 기준으로 이관. **660 passed·1 xfailed**(가중치 테스트 1건이 폐지 단언
    테스트로 교체됨).
  - ⚠ 미검증: 실 LLM E2E 재실행은 안 했다(비용). 정렬 변경은 표시 계층이라 카드 생성 결과
    자체는 불변이지만, 외부검증 대상 집합은 순서 기준이 바뀌어 달라질 수 있다.
- **✅ 문서·스크린샷 최종 동기화** (2026-07-18 마감). README 실제 화면을 아스트 2020 실측 3장으로
  교체(검토큐·재고카드·관계카드 — 스트림릿 headless + playwright 촬영, 재생성 카드 기준). 골든
  검사1 수치 갱신(LG생건 72/72·아스트 53/53), 검증 로그에 G7/G9 실측 행 추가, 트러블슈팅에 오늘
  사고 3건(자본거래 병합·통독 0건 오진·카드 파괴) 반영 — README·FINAL-REPORT 0/7/8/9/11 동기화.
- **✅ 잔여 3작업 전부 완료** (2026-07-18, 크레딧 충전 후 종결). 00356370 카드 재생성 성공 —
  5관점 완주(실패 0)·27장(계정14·관계8·회사5)·316초, 저장 가드 통과. **golden 실데이터 테스트
  복구**(11/11 passed), 전체 662 passed·1 xfailed. 데모 3사 모두 SCE 이름 복원 반영 카드 보유.
  - **✅ 백테스트 재실행**: recall 5/6·삼성 FP 14·핵심계정 강도순위(아스트 재고 10.0/3위·두산
    미청구 3.21/5위) baseline 동일. fired 216→214는 별칭 매핑 이동분(채점 불변) — 재정규화 회귀 0.
  - **✅ 셀트리온 전처리 완결**: gate PASS + 별칭 제안(신규 등록 0) + 완료 마커(chunks=104,
    오늘 Layer1 실측분 재사용으로 ₩400 절약). 이제 UI에서 "✅ 전처리 완료".
  - **✅ 아스트 카드 재생성**: 24장(계정12·관계5·회사7), 재고자산 카드 유지, 163초.
  - **❌ 00356370 카드 재생성 — OpenAI 크레딧 소진(429 insufficient_quota)**: 아스트 재생성까지
    쓰고 바닥. 5관점 전멸 실행이 **기존 정상 카드를 빈 파일로 덮어 파괴** → golden 실데이터 테스트
    `test_real_saved_cards_reconcile_clean` **FAIL 상태**(정직 유지 — 크레딧 충전 후 카드 재생성하면
    복구). **재발 방지 2건 반영**: ①`save_cards`가 "관점 실패>0 & 카드 0장"이면 저장 거부(None) —
    이전 정상본 보존 ②관점 예외를 무언 삼킴 → logging.warning으로 사유 표면화(429가 '0건'으로만
    보이던 원인). 신규 테스트 2, 전체 **662 passed·1 xfailed**(+golden 1 FAIL은 위 사유).
  - **⏭ 크레딧 충전 후**: 00356370 카드 재생성 1회(₩1~2천) → golden 테스트 복구 확인.
- **✅ SCE 별칭 코퍼스 확충 + G9 연도 간 대사 신설** (2026-07-18, 이어서).
  - **별칭 확충(데이터·config)**: 전 코퍼스 센서스(`_sce_unmapped_census.json`, 1,494개 SCE DB·
    미매핑 라벨 1,198종) → 뜻 명확한 군집만 2회 큐레이션으로 `canonical_accounts.yaml` 별칭 17건+
    추가(당기순이익→순이익 키 절단 보정·연결범위 3표기·자기주식 매입·주식매수선택권 인식/행사및소멸·
    신주인수권부사채 행사·전환사채 전환 등). 코퍼스 회수 2,164행(13%) — 꼬리는 1~2사 고유 라벨로
    구조적 한계. 데모 재정규화(재수집 0) 후 표준분류 밖: 아스트 32%→**5%**·셀트리온 35%→**0%**·
    00356370 0%. 사용자 "10~14%도 괜찮은 거냐" 추궁 → role 검증으로 2차 조임: ①셀트리온 잔존은
    전부 restated_begin **마커**(거래 아님, role 기계가 이미 처리) → G8 지표 모집단을 leaf로 교정
    ②아스트 잔존 3종 중 2종은 코퍼스 동류 다수라 canonical 신설(재평가잉여금변동·신종자본증권변동).
    최종 보류 1종: 전환사채의 조기상환(−1억, 자본총계 0.05%) — 기존 선례("전환사채 조기상환"→
    연결대상범위변동)가 의미상 어긋나 전파·교정 모두 안 함(원문 라벨로 정상 흐름).
  - **G9 연도 간 대사**(`gate_yoy.py`): 올해 보고서 prior_amount vs 작년 DB amount를 (fs_div,
    sj_div, canonical) 키로 대사. 일치/표기변경(부호만)/재표시 후보 3분류, **차단 안 함**(재표시=
    회사 사실, 셀트리온·아스트 실사례). '기타 중요 계정' 버킷은 이질 합계라 제외. 실측: 아스트
    재표시 36건(무형자산 1,761억→1,438억 — 2019 재작성 사실 자동 포착)·셀트리온 1건·00356370 0건.
  - 문서: README §3.3(거짓 71~88% 문단 교체·G9 행·검문 블록)·FINAL-REPORT 0/1/2/3 G1~G9 동기화.
    테스트: gate_yoy 5 신규, 전체 **660 passed·1 xfailed**(별칭 전역 적용 회귀 0).
  - **⏭ 잔여**: 저장 카드 재생성(아스트·00356370 — SCE 이름 복원 반영), 셀트리온 UI 전처리 1회
    (완료 마커), 백테스트 스크립트 재실행(아스트 재정규화가 신호에 미치는 영향 미실측 — pytest는 무회귀).
- **✅ SCE 정체성 복원 + Layer1 실패 위장 3중 차단** (2026-07-18). 게이트 확장(G7/G8) 실측이
  끌어낸 두 결함의 근본 수리.
  - **결함 A(SCE 자본거래 병합)**: 미매핑 강등이 canonical을 상수 `"기타 중요 계정"`으로 덮어
    → `_compact_sce_cells`·`sce_occurrence_states`의 `canonical or label` 폴백이 영영 label을
    못 봄 → 서로 다른 자본거래 7종(셀트리온 자기주식 매입 582억·주식매수선택권, 아스트 신종자본
    증권·전환사채)이 한 이름으로 병합, LLM 식별 불가 + 신규/소멸 신호 뒤섞임. **수정**:
    `sce_change_identity`(metrics_panel) — 미매핑이면 원문 라벨이 정체성(universal.py:373과 동일
    규칙). 실측: 셀트리온 셀 147개 거래명 32종·병합 잔존 0, 자기주식 매입 −582억 이름 복원.
  - **결함 B(Layer1 실패→"0건" 위장)**: run_layer1이 전 파트 실패/미실행이어도 status="ok"·추출
    0건 반환 + UI가 실패에도 완료 마커 기록 + 빈 replace가 기존 추출분 파괴 가능. **셀트리온
    2019 "추출 0건" 몇 주 오진의 실체 = report_extracts 테이블 자체 부재**(저장 미도달, 마커도
    없음 — 지금까지 셀트리온 분석은 서술형 없이 돈 것). **수정 3중**: ①전부 실패=status
    "error"/전부 무키="skipped"(저장 안 함, 이전 데이터 보존) ②완주 0건="empty"(빈 테이블 저장
    = "진짜 0건" 증거) ③UI는 ok/empty만 완료 마커(실패는 st.error 후 재실행 가능 유지).
  - **G8 SCE 지표 교정**: normalized_financials SCE 행(분석 비경로)으로 재던 71~88% 경고는
    거짓/과대(00356370은 2D 기준 0%) → `sce_2d_quality`가 실경로(sce_equity_components) 기준
    거래종 단위로 측정. 실측: 아스트 32%·셀트리온 35%(원문 라벨로 흐르므로 손실 아닌 표준분류 밖).
  - 신규 테스트 8(metrics_panel 2·gate_quality 2·layer1 3 재작성 포함), 전체 **655 passed·
    1 xfailed**(회귀 0).
  - **✅ 셀트리온 2019 라이브 재실행으로 원인 확정** (2026-07-18): 10/10 전 파트 ok ·
    **104건 추출**(특수관계자 독점판매권·자기주식 취득·연구개발비 소급 등 감사 고가치 다수) ·
    188초 · in 89k/out 24k(~₩400) · report_extracts 104행 영속 · G8 "서술 추출 0건" 경고 소멸.
    → 입력·프롬프트·모델 전부 정상 = **과거 "0건"은 콘텐츠 문제가 아니라 실행 실패가 ok·0건으로
    위장된 것**(수정 전 결함 B 경로). 정확한 당시 실패 사유(타임아웃/한도/미완주)는 로그 미영속
    구조라 재구성 불가 — 그 구조 자체가 이번에 고쳐짐.
  - **⏭ 남은 것**: 셀트리온 완료 마커는 UI 경로라 아직 없음(전처리 버튼 1회로 마커+별칭까지 완료
    가능). 저장 카드(아스트·00356370)는 재생성해야 SCE 이름 복원이 카드에 반영됨.
- **✅ 온보딩 서술 코드 대조 교정 — README·FINAL-REPORT 7파일** (2026-07-18). 사용자 질문("온보딩이
  하는 게 있나, 사람 선택 UI도 없앴는데")에 코드 대조로 답 확정 후 문서 전수 교정.
  - **확정한 실동작**: ① 결정론 게이트(G1~G5·통화)는 UI [분석 준비](`prep.prepare_company`)가
    수집·정규화 직후 자동 실행 — 통과 연도만 준비완료. ② UI 온보딩 버튼(`run_full_onboarding`) =
    LLM 전처리 3종: 게이트 재검문 + Layer1 본문 통독(→`report_extracts`, 주석 관점 입력) + 별칭
    제안·신뢰도≥0.7 자동 등록+5개년 재정규화(보류=기타 중요 계정). 완료 마커 `onboarding.json`이
    카드 단계 진입 조건. ③ 사람 수동 등록 폼은 별도 정비 페이지(`dashboard/onboarding.py` 단독
    구동)에만 잔존. ④ G6 dump는 생성되나 통독 LLM 미배선.
  - **교정 파일**: README(개요 6단계화·분리도식·파이프라인 도식에 온보딩 전처리 박스 신설·상세설명
    블록 신설·§3.4 전처리 소절 추가·한계#3·E2E 표기), FINAL-REPORT 0(한눈도식)·1(레이어)·2(mermaid·
    단계표 행 분리)·3(위치·3.1·3.5)·7(§7.1·§7.5 "사람 확인 필수"→"자동 전처리" 재작성)·8(한계#3)·
    9(에이전트 구성 표기). 낡은 표현("코드→LLM→사람"·"사람 확인 필수"·"R4 예정") grep 잔존 0 확인.
  - **명명 확정(사용자 지시)**: LLM 단계명 "온보딩"→"**LLM 전처리**"로 개명 — 문서 전체 +
    화면 표시 문자열(report_view.py 헤딩·버튼·배지, onboarding.py 정비 페이지 제목 "신규회사 정비").
    "온보딩 게이트"(결정론 검문)는 코드명(`onboarding_gate.py`)과 일치해 유지. 함수·마커 파일명
    (`run_full_onboarding`·`onboarding.json`)은 내부 식별자라 미변경(파급 회피).
  - **잔여**: `onboarding_gate.py` 자체의 낡은 주석("최종 판정은 G6 LLM·R4")은 코드 주석이라 미수정.
- **✅ 게이트 SHARES 통화 오판 수정 — 아스트2020·셀트리온2019 스트림릿 준비완료 복구** (2026-07-14).
  사용자가 두 회사 온보딩이 "망가졌다"(2018로 들어감·0개 파싱)고 보고 → **재조사 결과 진짜 원인은
  `_currency_ok`가 SHARES(주당이익 단위)를 외화로 오판**해 G_currency FAIL → prep.json 미생성 →
  스트림릿 "준비완료 없음". 회계항등식·산술·신호 게이트는 전부 PASS.
  - **데이터 상태 규명**: 두 회사 raw는 **CSV=as-filed 원본(아스트 재고 168.5B·셀트리온 무형 1.040T,
    분식 보이는 과대값) / JSON=정정본(미사용)**로 갈려 있음. 정규화는 CSV를 읽으므로 duckdb·골든카드가
    이미 as-filed. rcept: 아스트 원본 20210322000920 / 정정 20240208001322(재고 과대계상 자진정정),
    셀트리온 원본 20200330003829 / 정정 20220512000850(재무제표 재작성). **정정 전 데이터는 이미 DB에
    있어 별도 수집 불필요** — 골든 메모리의 "정정=OFS만" 서술은 부정확하나 DB값==as-filed 결론은 유효.
  - **수정(TDD)**: `_NON_CURRENCY_UNITS={KRW,SHARES}` — SHARES는 통화 아닌 단위라 외화 차단 대상 제외
    (USD 등 실외화는 차단 유지). `_currency_ok` + 테스트 `test_currency_ok_shares_unit_passes`.
  - **검증(2/2)**: 재-prepare 후 gate_passed=True·duckdb as-filed 값 유지·CSV rcept 원본 불변(재수집
    없음)·prep.json 생성·prepared_years=[2020]/[2019]. 전체 **624 passed·1 xfailed**(회귀 0).
  - **미재현/잔여**: "2018로 들어감"=현재 코드 미재현(문서·정규화 모두 2020 원본 정확). "0개 파싱"=
    본문 11파트 정상로드, layer1 **LLM 추출 0건**(파싱 실패 아님)—셀트리온 라이브 온보딩 재확인 필요(비용).
    주석 HTML 빈 껍데기(singlnote 서비스가 이 회사/연도 빈 셸 반환, note XBRL 숫자는 정상)—별개 갭.
  - **⏭ 사용자 스크린샷 경로**: 스트림릿에서 아스트 2020/셀트리온 2019 선택→준비완료→온보딩(선택)→
    검증실행(또는 저장카드 자동로드)→as-filed(분식 보이는) 카드 스크린샷. **주의: 이 두 연도는 재수집 금지**
    (정상 수집이 CSV를 정정본으로 덮어씀). 메모리 `[[golden-test-strategy]]` 관련.
- **✅ 골든테스트 설계 + 검사1(수치 골든) 하니스 구현** (2026-07-12, 설계 단일출처:
  [golden/DESIGN.md](../../golden/DESIGN.md), 메모리 `[[golden-test-strategy]]`). 사용자 문제제기:
  "PHASE2를 '숫자 맞고 LLM 그럴듯함'으로는 검증 못 한다 — 내 이전 실행 봉인=순환(버그 잠금),
  사람이 filing마다 정답지=불가능." → 골든을 **외부정답 2검사**로 확정. **검사1(전자동)**: 최종 카드
  표시 수치를 DART 원천값과 대조 — grounding `build_account_index`·`_sig`(스케일 무관 유효숫자)를
  **최종 카드**(모든 변환 후)에 재적용, grounding이 못 보는 변환 버그(억/조 ÷10·부호) 겨냥.
  **검사2(as-filed 벤치마크·후속)**: 원본 접수분 입력으로 재작성·제재 계정 적중 채점(존재+순위,
  텍스트 비교 금지). 전후꼬임(사용자 지적)은 **DART 원본 서빙 실측으로 해소** — 정정 후에도 원본
  rcept로 본문·XBRL 서빙(00117212 실측: document 4.37MB·XBRL 252KB·정정본 해시 상이).
  - **검사1 하니스 구현**: `golden/numeric/check_numeric.py`(1a 원값 실재·1b 환산 무결 convert_ok·
    분해 항등·대사불능 버킷), `test_numeric_golden.py` 10(단위 9+실데이터 1). 실데이터 00356370/2025
    저장카드 27장 → **N=57 전량 match**(value_mismatch·convert_fail·unreconcilable 0, 6.4조까지 환산
    정확, `_report_00356370_2025.md`). 구축 중 하니스 한계 2건 실측 수정(claim 형제계정 인용=전역대조·
    주석 네임스페이스=전역 주석값대조). pytest **628 passed·1 xfailed**(baseline 618+10, 회귀 0).
  - **✅ 검사2(의심 적중 골든) 코드 구축 — 실행 없이** (2026-07-12): 사용자 지시 "생성하되 실제 실행은
    아직 하지마." 채점 엔진·정답지 로직·원본 식별은 순수함수라 실행 없이 완결. `golden/asfiled/
    resolve_original.py`(원본 rcept 식별), `golden/hit/build_labels.py`(재표시 계정 추출 + 유의성
    필터 파라미터 + 등록조건 게이트 DB값==asfiled), `golden/hit/check_hit.py`(recall@K·hit_rank·존재+순위
    채점, 텍스트 비교 없음), `golden/hit/run_benchmark.py`(오케스트레이터, execute=False 기본 dry-run —
    실LLM/실DART 미호출), `benchmarks.yaml`(후보 2사 verified=false). 신규 test 17, 전체 **645 passed·
    1 xfailed**(회귀 0). **실데이터 발견·수정**: 정답지 빌더가 대형사 재표시 576건 중 대부분 22.9조→22.9조
    (0.0005%) 반올림 노이즈 → 유의성 필터(상대변화 임계) 추가, 121건으로 정제(매출 17.0조→11.1조 Δ35%
    등 진짜 중대재작성만 잔존). 원본 XBRL 본표 추출(기재정정 포함 사례)은 설계 §4 확장 미구현 — 게이트
    통과분은 기존 build_company_report로 충분(기재정정 안 된 본표는 JSON API가 이미 as-filed).
  - **✅ 검사2 첫 실행 — 아스트(00409681) 재고분식 as-filed 채점** (2026-07-12): 정답지 재정의(restated_later
    311 잡음 기각 → known_cases.json 증선위/법원 확정 분식 8사가 진짜 답지, `_benchmark_candidates.md`).
    효과 측정으로 아스트 선정(재고자산 4배 단조증가, 정답계정 완전 커버 — 두산에너빌리티는 건설 특수계정
    매핑 사각·디아이동일은 매칭 아티팩트로 탈락, `_effect_ranking.md`). **as-filed 검증**: 아스트 2018·2019
    "유상사급 재작성" 발견 → 원본 vs 재작성 XBRL 직접대조로 **CFS 재고자산 원본==우리DB 실증**(재작성은 OFS만).
    target 2020·[2015..2020] 로드(미래 재표시 누수 차단). **결과: recall@5=2/3, 재고자산 rank1**(재고회전율
    0.84→0.3·5년 누적 서술로 분식 정확 포착)·매출원가 rank5·자기자본 미카드. 검사1 교차 N=64 전량 as-filed 일치.
    `golden/hit/_score_00409681_2020.md`. **하니스 버그 3건 실데이터로 발견·수정**(check_hit fs접두 미매칭→이름매칭·
    검사1 주석근거 동명계정 오매칭→전역대조·병기포맷 파싱실패 N=8 hollow→N=64). 신규 테스트 2, 전체 647 passed 회귀0.
  - **⏭ 다음(사용자 결정·비용)**: 나머지 분식 5사(셀트리온·모델솔루션 등) 배치 채점 + 통제군(삼성·KAI) 거짓양성
    측정 → recall/FP baseline 고정. build_labels에 known_cases(labels.csv) sanction 로더 배선(현재 restated_later만).
    두산에너빌리티 건설 진행률 계정 정규화 커버 갭은 별도 과제.
- **✅ 변환 경계 권위 승격 — LG생건 감사 4결함 구조 해결** (2026-07-11, 설계:
  [docs/superpowers/specs/2026-07-11-transform-boundary-authority-design.md](../superpowers/specs/2026-07-11-transform-boundary-authority-design.md)).
  원칙: 사후 정규식 검사 발명이 아니라 **이미 보유한 데이터를 각 변환 경계의 권위로 승격**.
  ①시계열 표기변경 정규화(`src/report/series_normalize.py`): t년 당기값 vs t+1·t+2 보고서의
  재표시 전기값(prior_amount·prior2_amount — 저장만 되고 안 쓰이던 데이터) 대조, 부호만 다르면
  최신 표기로 정규화(presentation_change)·절대값 다르면 재표시 신호(restated_later).
  LG생건 실측: 투자활동 현금유출 CFS·OFS 부호 아티팩트 정규화 + 진짜 재표시 6건 신규 포착.
  ②금액 환산은 코드(`src/report/amounts.py` format_krw·annotate_amounts): LLM 입력 경계
  (관점 material·조사 payload·조사 도구 4종)에서 원값에 "1조 2,534.7억" 병기, 프롬프트는
  "그대로 옮겨 쓰기"로 교체 — LLM 나누기 오류(1/10 축소) 원천 제거. ③라벨 권위=공시 원문:
  패널·조사 payload·카드 제목에 disclosed_label(공시 계정명), 정준명은 내부 키로 강등.
  전수 감사 `src/normalize/label_audit.py` → [CANONICAL_LABEL_AUDIT.md](CANONICAL_LABEL_AUDIT.md)
  (1,659사·35,126조합, 오라벨 후보 1,153건 — '이자비용'←금융비용/금융원가가 1,594사 시스템성
  최대 건). ④외부 경계 대사: figures 구조화 출력→내부 공시값 대조(figure_check
  match/mismatch/uncheckable, UI ⚠ 마킹). 외부검사 대상은 조사 미해결 카드 전부
  + 리다이렉트 URL 해소(resolve_final_url). pytest 618 passed·1 xfailed(신규 26+, 회귀 0).
  **⏭ 남은 결정(사용자)**: 오라벨 후보 1,153건 중 정준명 개명 범위(특히 '이자비용'→'금융원가'와
  이자보상배율 분자 문제 — 진짜 이자비용 매핑 dart_InterestExpenseFinanceExpense로 교체 여부).
  기존 저장 카드(LG생건 27장 등)는 재생성해야 새 경로가 반영된다.
- **✅ 조사원 파이프라인 1단계 구현 완료** (2026-07-11, PLAN §5 '조사 단계' 설계 반영).
  구현 4항목: ①브리지 병합(부모-자식 카드 한 장, `merge_bridge_cards`) ②카드별 조사원
  — 결정론 게이트 `needs_tool_loop`가 미해결 카드만 도구 루프(캡 5~8회)로 넘김, 도구 4종은
  `src/report/investigation_tools.py`, 루프 본체는 `src/report/investigator.py`, 설정은
  `config/investigation.yaml` ③조사 결론을 카드 최상단에 렌더 + 반박 에이전트 입력으로 공급
  (`card_pipeline` 배선) ④High/Medium/Low 위험도 라벨 폐지 — `src/report/priority.py`가
  유의성·표수·이상신호·확신도로 연속 점수(`priority_score`) 산정, 컷 없이 정렬만.
  pytest 559 passed·1 xfailed(착수 전 536 대비 +23, 회귀 0). **⏭ 실 LLM 프로브
  미실행**: `data/backtest/_probe_investigator.py`는 스크립트만 커밋, 조사원 실호출 품질·
  비용은 미검증(사용자 실행 대기, 비용 발생). 남은 백로그: 반박을 "도구 쥔 반대 조사원"으로
  승격 / 카드 횡단 스토리 종합 / `needs_tool_loop` 하위 잔차 leaf 엣지 / 빈 headline 라벨 폴백 /
  병합된 자식 카드의 원 suspicion 텍스트가 반박 context에 미전달(claims는 병합됨 — 최종 리뷰 관찰).
- **✅ 변동 분해 엔진(1단계) — 카드의 "왜"를 코드가 계산** (2026-07-10, PLAN §6.5 신설).
  사용자 지적: "영업이익 급감" 카드가 원인(판관비? 원가?)을 안 줌 — 멀티에이전트 깊이 부재.
  실측 조사(4,782 corp-year): GP 항등식 99.98%·OP 표준형 92.1% 재료 충분, 주석 판관비 내역은
  3.7%뿐(가설 기각 — 세부는 IS 개별계정·동행계정 폴백). 구현: `config/decomposition.yaml`
  (GP·OP 브리지, 변형 2종) + `src/report/decomposition.py`(회사별 |잔차| 최소 변형 선택,
  미설명 잔차 정직 표시) + 카드 "왜 움직였나" 표 + 반박 입력 decomposition 공급.
  pytest 500 무회귀. **⏭ 2단계(승인됨·미구현)**: external을 발견자→카드별 타깃 검증자로
  재배치(분해 결과=검색 쿼리 재료, PLAN §5 '카드 후속 검증 단계' 설계 반영 완료).
  - **후속 보강(사용자 피드백 3회)**: ①동의 canonical 슬롯(판매 및 일반관리비[ifrs]↔판매비와
    관리비[dart] 갈림 흡수, OP 통과 3,836/4,159) ②재귀 펼침(GP→매출·원가, 순환 가드,
    부호·기여율 최상위 정렬) ③부모 값 명시(얼마→얼마·변화율 타이틀+전체 행) ④세전(변형3,
    63.3%)·순이익(85.7%) 브리지 확장 — 영업외(기타비용) 단계까지 사다리 완성. pytest 507.
- **✅ 카드 3섹션 통일 + 타입별 차트(a단계)** (2026-07-10). 카드 = ①무엇이 의심스러운가
  ②결과 분해(분해표+근거수치+external_evidence 자리) ③시각자료. 차트를 폼에 맞게:
  분해 카드=**워터폴**(전기→leaf 기여→당기, waterfall_leaves 평탄화로 소계 이중계상 방지),
  관계 카드=**지수화 라인**(첫해=100)+2다리 괴리 음영, 일반 계정=추이 바+YoY% 라벨.
  humanize_amounts(서술 12자리 원숫자→억/조, 사용자 추가). use_container_width 전량
  width="stretch". pytest 511.
- **✅ 두괄식 검토포인트 + 외부 검증 에이전트(b단계) 완성** (2026-07-10). ①카드 첫 줄
  "🔎 검토 포인트"(결정론: 매출 vs 부모 변화율 ≥2배 괴리 명제 + 주도·방어 요인 —
  card_data.review_point) ②근거 수치 표에서 분해 표 중복 계정 제외(decomposition_accounts)
  ③**external 재배치 완료**: ALL_PERSPECTIVES 5관점(발견)으로 축소, 카드 확정 후
  `src/report/external_verify.py`가 위험도 상위 5카드만 타깃 검색(카드당 ≤2쿼리, 분해 주도
  요인 포함) → external_evidence/checked 기록, 반박과 병렬 실행. 렌더 3분기(근거/미발견/
  미수행). 분해 차트는 발산 가로막대(contribution_figure, 워터폴 오독 교체 — 사용자 개선).
  pytest 527. external.py 구경로(run_external_suspicions)는 integrated_report 경로가 아직
  사용해 보존.
- **✅ 의심건 카드 대형 리디자인 — 주장·수치·차트** (2026-07-10). 사용자 지적: 카드가 줄글뿐이라
  사실확인 불가 + "반박만 보여 뭐라는지 모름". 근본원인 2: (a) 관점 주장(description·cited_value)이
  반박 에이전트에만 가고 카드에서 탈락 — `Claim` 스키마 신설, card_builder 3지점서 claims 채움(질문
  없이 답변만 보이던 구조 해소). (b) numeric_evidence(grounding 대조 수치)가 카드에 실려 있는데
  렌더러가 미표시 — 근거 수치 표로 렌더. 신규 `dashboard/card_data.py`(순수 가공)+`card_view.py`
  (전폭 카드: 주장→근거표|5개년 추이차트(당기 강조)→반박 expander). 관계 카드는 다리 상위 4개
  멀티라인(dataviz validator PASS ΔE 24.2). 구 HTML 카드 렌더러(render_card_html 등) 삭제 컷오버.
  라벨 명확화(표수 N/4→"지적 4관점 중 N", 반박: 접두). pytest 489 무회귀.
  - **후속: 카드 결과 영속화** — 세션 메모리에만 있어 새로고침 시 LLM 재실행(₩1~2천) 필요하던 갭.
    `src/report/cards_store.py`(suspicion_cards.json, 회사/연도 격리, 카드+시계열 스냅샷) + report_view
    자동 저장·재방문 자동 로드("저장된 검증 결과" 캡션, 버튼 '검증 다시 실행'). pytest 492 무회귀.
- **✅ 별칭 자동 등록 컷오버 — 감사인 확인 딸깍 제거** (2026-07-10). 사용자 결정: 메인 앱의
  계정 이름 제안 확인·등록 UI는 무의미(판단재료 없는 딸깍=자동과 동일+마찰) → 감사인에게 아예
  숨김. `dashboard/onboarding.py`에 `auto_register_aliases`(신뢰도 ≥0.7·非기타만 window 전 연도
  quirk 등록, reason=auto 표기, 멱등) + `_auto_register_stage`(등록 ≥1이면 raw 보유 window 재정규화
  — 별칭은 다음 정규화부터 반영되는 잠복문제 해소, report_extracts는 별도 테이블이라 보존).
  보류(저신뢰·기타)는 기존 '기타 중요 계정' 경로 — 자산 5%↑면 UNMAPPED_MATERIAL_ACCOUNT 카드로
  표면화. 수동 교정은 전처리 페이지(onboarding.py) 유지. report_view 확인 UI 삭제.
  pytest 477 무회귀. docs: LIMITATIONS §2·UI.md 갱신.
- **✅ issue_type B 재편 — 재무제표 영역 축으로 전면 교체** (2026-07-01). 사용자 대화로 설계 교정:
  처음 제안한 축(수준/변화/관계)은 perspective와 중복이라 기각 → issue_type은 "누가 찾았나"(perspective)와
  별개인 "무엇에 대한 우려인가"(공유 라벨, 관점별 배분 아님). **재무제표 영역 축**(revenue_receivables·
  cost_inventory·asset_valuation·liability_liquidity·equity_capital·contingency_related_party·earnings_tax·
  cash_flow·unmapped_material_account·기타)으로 enum 교체. 분식프레임(receivables_quality·going_concern 등)
  제거, 구체 위험은 subtype 자유서술로 내림. 재무제표 구조라 닫힘(전수커버, "기타" 극소수).
  - 파급: findings.py enum + tests ~30곳(sed, 옛 멤버 잔존0) + perspective_prompts.yaml output + PLAN.md.
    값문자열 grep 8건은 다른 네임스페이스(비율category·워치리스트·관계사슬)라 비대상. pytest 394 무회귀.
  - 커버 증명: 실 E2E "기타" 카드 표본 13/13 매핑(분모명시, 전수아님) + 구조적 전수성(재무제표 표준구조 권위,
    음의공간=공시+OTHER). `_ISSUETYPE_B_MAPPING.md`. 한계: 런타임 "기타"비율 실감소는 실LLM 재측정 필요(비범위).
  - 메모리 `[[issuetype-fs-area-axis]]`.
- **✅ 실 LLM Phase2 E2E 최초 측정** (2026-07-01, `_E2E_PHASE2_LIVE.md`). 근본구조(OFS·주석전량·SCE·
  occurrence·중립라벨)를 처음 실 6관점+반박에 태움. **비용**: 삼성 ₩1,884(478k입력·87초·7호출, note관점이
  250k=₩899로 지배)·대주 ₩1,037(245k·71초). 단가가정 $2.5/$10·₩1380(실단가 미확정). **사각 검증**: 주석
  특수관계자·지급보증·우발, SCE 자본거래가 **grounded로 실제 도달**(환각 미탈락) — 근거색인 작업 실증.
  핵심 사각 I(특수관계자·우발) **카드화 성공**(충당부채 card + 회사카드 contingent_liability·related_party).
  OFS F·자기주식 G는 grounded되나 top카드 미부상(LLM 우선순위·비결정). **부수 실측: B(어휘 비대칭) 확인** —
  비-분식 이상이 "기타/subtype"로 대량(대주 계정카드 12중 ~7 기타: 유형자산급증·투자부동산급증·자산재평가 등).
  중립라벨 A수정 반영됨(카드에 contingent_liability, understatement 없음).
  - **⏭ 다음(사용자 결정)**: B(issue_type 중립·목적정렬 축 재편) — 이제 증거 있음 / 다른 회사 확대 / UI 배선.
- **✅ issue_type 분식프레임 분석 + A수정(방향라벨 중립화)** (2026-07-01). 사용자 "issue_type 분식프레임
  분석" 요청. **분석 결론**: "6관점 분식프레임 수렴" 진단은 대체로 낡음(수렴 원인=데이터 동일성, OFS·주석·
  SCE·occurrence로 해소. 프롬프트는 OTHER·"억지로 욱여넣지 마"·관점별 focus로 반-쏠림. 계정카드는
  cluster_key로 묶지 issue_type 아님). **진짜 문제 2**: (A) `CONTINGENT_LIABILITY_UNDERSTATEMENT`가
  '과소계상' 방향 확정 = 최우선 포지셔닝(부정 확정 안 함) 위반 — **수정**: `CONTINGENT_LIABILITY`로 중립화
  (findings.py·PLAN.md 2/2, 라이브 잔존 0). (B) 어휘 비대칭(분식 4종 구체 vs 비분식 전체 '기타' 1종, 목적
  '이상변화 큐'와 불일치) — 실재하나 **행동영향 미측정** → 실 E2E로 크기 잰 뒤 결정(이번 비범위, 증거 없이
  큰 재편 금지). 다른 분식성 라벨(earnings_quality 등)은 표준 감사범주라 유지.
  - **⏭ 다음(사용자 결정)**: B(중립·목적정렬 축 재편) 여부는 실 LLM 2+사 E2E 후 / 실 E2E 자체(주석195조·SCE
    카드화 확인, 비용발생).
- **✅ 근본 뒤집기 — 포함-기본값(제외는 정당 2종만) + SCE 2D 편입 완료** (2026-07-01). 사용자 통찰:
  "차원을 하나씩 추가하는 게 또 두더지잡기 아니냐 → 아예 처음부터 제외를 안 시키고 정당한 것만 제외하면
  되잖아." 기본값 뒤집음: **분석 모집단 = 전 fact, 정당제외 = 완전중복 OR 비fact 2종뿐**(그 외 "모양/낯섦"
  핑계 제외 금지).
  - **주석 규칙 교정**: 직전 주석차원이 차원흡수(삼성 2003·대주 106 = 부문/지역 breakdown=net-new)를 통째
    잘못 제외했음을 발견(적재된 흡수는 전부 유차원 — load가 무차원흡수·메타는 이미 제외). `surfaced_note_facts`
    가 적재본 전량 반환으로 교정. note 원장 surfaced==population.
  - **SCE 2D 편입**: `build_sce_ledger`·`_compact_sce_cells`·`load_sce_equity_components` 배선. 본문 ledger의
    SCE 제외사유를 "SCE 2D가 상위 포함(superseded, 정당)"로. payload `sce_cells`·`coverage_ledger["sce"]`,
    change_material에 투입(자본변동=change 관점), grounding `sce:{change}`·`sce:{component}` 색인.
  - **검증**: probe(`_NOTE_LEDGER_PROBE.txt`) 삼성 note 4312/4312·sce 126/126·대주 132/132·61/61 전량 surface·
    reconciled·미설명0. 비용 라이브(target2025) 삼성 ~1,098원(전량4215note+150sce)·대주 ~84원. 신규 테스트 5
    (coverage sce1·note규칙2·grounding sce1·materials sce1), touched 35 passed. 백테스트 무관.
  - **분기**: DB 미수집 → **이 프로젝트 비범위 한계로 확정**(DATA_SCOPE §2). 제외규칙 아닌 데이터 부재.
  - **⏭ 다음(사용자 결정)**: 별개 과제 issue_type 분식프레임 수렴(③ 교란) / 실 LLM 2+사 E2E(주석195조·SCE가
    실제 카드로 뜨는지, 비용발생). 메모리 `[[include-by-default-inversion]]`.
- **✅ 근본구조 차원확장 #1 — 주석(note) 차원을 원장·분석·검증에 끌어옴 완료** (2026-06-30).
  사각 #3(주석 우발 미카드화) 해결. 결정: **A(주석 전량 투입)** — 임계·카테고리 컷은 또 다른
  두더지잡기(사용자 지적)라 금지. dedup도 실측결과 안전절감 0(특수관계자 906건 전부 연결별도×
  거래상대×기간으로 distinct, 완전중복 0)이라 제외.
  - **reader**: `load_notes_classified(corp, years)`(data.py, note_facts_classified 읽기. 그간 write-only
    dead-end이던 테이블). 삼성 4312행·대주 132행.
  - **주석 원장**: `build_note_ledger`(coverage.py) — population=전 fact, 흡수(본문중복 stem일치)·메타만
    사실기반 제외, detail+기타주석 surfaced 전량. payload `coverage_ledger["notes"]`. 삼성 4312=surfaced2309
    +흡수2003+미설명0·대주 132=26+106+0(`_NOTE_LEDGER_PROBE.txt`).
  - **material**: note 관점에 surfaced fact 전량 compact 투입(`note_material` note_facts 인자·`_compact_note_facts`).
    특수관계자195조·지급보증·소송이 이제 들어옴(기존 10계정 HTML 파이프 공백 메움).
  - **grounding**: `build_account_index`에 note 색인(`note:{label}`·`note:{category}` namespaced, 본문 비충돌).
    금액형 value 유효숫자·서술형 빈 풀. verify가 perspective==note면 note 키 조회 → note-only 우발 환각탈락 차단.
  - **비용**: dimensions XBRL 축 문자열 무손실 축약(`_slim_dimensions`, member 토큰 보존·boilerplate 제거)으로
    34% 절감 → 삼성 note 증분 **610~762원**, 대주 3~4원. 대부분 회사 무시 수준, 초대형사만 유의(줄일 수 없는 실정보).
  - **검증**: pytest 신규 8(coverage2·grounding5·materials2·integrated slim1 일부)·타깃 66 passed. 백테스트 무관
    (주석은 run_backtest 경로 아님). 메모리 `[[note-dimension-full-surface]]`.
  - **⏭ 다음 차원(같은 원장에 추가)**: SCE 2D 셀·분기·세그먼트. + 별개: issue_type 분식프레임 수렴(③ 교란).
- **✅ 근본구조 씨앗 — 커버리지 원장 + 신규/소멸 신호 완료** (2026-06-30). 사용자 지적("두더지잡기 그만,
  근본 해결")에 따라 사각 #2(신규발생)를 개별 패치가 아니라 **구조적 불변식**으로 전환. 근본원인 =
  분석 명단을 "기본 슬라이스(올해·연결·본문)에서 골라 담기(positive selection)" → 슬라이스 밖은 조용히
  드롭. 원칙(§3 전수추출·§10 population-first)이 차원마다 사후 적용돼 새 차원마다 또 터짐.
  - **A 명단=합집합**: `_account_level_series` 키 선정을 "target_year 잔액>0"→"윈도우 내 어느 해든 잔액>0".
    소멸(작년만)·신규(올해만) 동시 포함.
  - **B 신규/소멸 신호**: metrics_panel entry에 `occurrence_state`(present/appeared/resumed/disappeared)
    +columnar. delta_score 불변(별도 칸). `occurrence_state()` in metrics_panel.py.
  - **C 대조 원장(핵심)**: `src/report/coverage.py` `build_coverage_ledger` — 본문 셀 모집단(normalized_financials
    전 행)=분석셀+제외사유셀+미설명셀 항등식. payload `coverage_ledger` 키 + render "미분석 N건" 경고.
    **★원장이 실작동 입증**: 1차에 대주 미설명 24건(NaN placeholder 거짓드롭) 자동 포착 → `_real_amount`
    필터 수정. 삼성 N=847(분석803+제외44SCE+미설명0)·대주 N=892(862+30+0). 산출물 `_LEDGER_PROBE.txt`.
  - **D 자가테스트**: OFS전용·appeared·disappeared·SCE 합성셀 심어 명단포함·occurrence·미설명0 단언.
  - **회귀**: 1차 full서 2건(columnar stale 샘플·build_account_profile 모집단 격리 불완전, fix A가 suspended
    Phase1 profiler 분포 흔듦) 발견·수정(target_year 잔액 제한 격리). 백테스트 5/6·삼성 FP 14 불변.
    pytest **382 passed**(376+신규6). 메모리 `[[coverage-ledger-root-structure]]`.
  - **⏭ 다음 차원(같은 원장에 추가)**: 주석 파이프(현재 10계정·CFS·target만 → 원장 "제외:주석파이프" 기록만)
    를 분석 명단에 끌어오기 / SCE 2D 셀 / 분기·세그먼트. + 별개: issue_type 분식프레임 수렴(③ 교란).
- **✅ 멀티에이전트 사각 #1 — 별도재무제표(OFS) 전면 개방 완료** (2026-06-30, 설계 `HANDOFF_ROOT_REDESIGN.md`).
  근본진단(3사각=한 뿌리: 도구가 "연결 본문·전년대비변화" 한 축만 봄) 중 **B안(데이터층 전면개방)·단계적**
  채택. grill로 핸드오프 A안(관점별 차원분할) 기각: §3.2(계정은 데이터로 흐른다) 위반 + 1:1매핑이 사각
  재생산("OFS이면서 level/change형 이상"은 다시 무주공산) + 핸드오프의 "연결과 차이 큰 OFS만" 선택기준이
  자기동기 예시 F(OFS 내부 YoY급증, 횡단차이 아님)조차 못 잡음. **B = OFS를 공통 패널에 전부 싣고 6관점
  전부가 봄.**
  - **구현**: `_account_level_series`·`_top_unmapped_material_accounts`(company_report) → CFS+OFS 둘 다 게시,
    series_key에 fs_div 접두(`CFS:차입금`/`OFS:차입금`)로 동명계정 이질병합 차단. 분모 fs_div격리:
    `statement_totals` 키 (fs_div,sj_div,year)·`compute_self_axes`/metrics_panel 룩업·`_asset_by_fs_div`(OFS
    계정은 OFS 자산총계로 정규화). 패널 entry에 fs_div 노출(+columnar). `build_account_profile`은 CFS-only
    필터로 격리(Phase1 suspended 재설계 baseline 보존). `_primary_fs_div` 제거(죽음).
  - **검증**: 삼성 OFS 89계정 패널 진입, F(별도 유동성장기차입금) amounts에 2024 spike 22.26조·변화축 살아남
    (`_OFS_STAGE_SAMSUNG_PROBE.txt`). 백테스트 **회귀 0**(recall 5/6·삼성 FP 14·분식강도순위 유지 — 백테스트는
    scan_universal/cfs_ofs_gap만 써 변경 무관). 신규 테스트 3(metrics_panel·integrated·grounding 교차환각).
    pytest 무회귀(변경 전 375 passed).
  - **⏭ 다음(단계적)**: 사각 #2 신규발생(delta_score prior=None→0 = 변화축 사망, "신규발생 flag" 별도 타입),
    사각 #3 주석 grounding(note_facts 색인). §3 교란변수(issue_type 9종 전부 분식프레임→관점 수렴)는 별개 손봄.
- **🎯 목적 재정의(사용자, 2026-06-21): 이 도구는 "분식 탐지"가 아니라 "이상 변화·감사인이 볼
  검토 큐"를 정한다.** 백테스트 분식 recall은 회귀가드일 뿐 목적 잣대가 아님. → capex 급증(+177%)
  같은 비-분식 이상변화도 큐에 있어야 마땅. **현재 구조적 괴리 발견**: `IssueType` enum 9종이 전부
  분식 리스크 유형(earnings_quality·liquidity_risk·going_concern·receivables_quality 등)이라, capex·
  관계기업 같은 "단순 이상변화"를 담을 유형이 없음 → 관점 LLM이 분식 프레임으로만 큐를 내고 비-분식
  이상변화 누락. **eval#2 큐 정당성 판정**(대주, `_E2E_EVAL_00112457_2024.json`): account_cards 16 중
  정당 이상변화 13(당기순이익·단기차입·법인세·매출채권·운전자본 등) + **SCE 거짓양성 3**(자본총계·
  기초자본·배당변동, change 관점의 자본변동표 오해, 순위 12·15·16). capex/관계기업 0표(큐밖). 사용자
  조건①(정당한 것만 capex보다 위)은 정당 13은 충족하나 **거짓양성 3건이 capex보다 큐 우위=부분위반**
  (SCE는 다른 컨텍스트서 수정 예정). **⏭ 다음(사용자 결정)**: 삼성 측정 진행 vs issue_type/관점
  재프레임(이상변화 큐 목적 정합). metrics_panel(사용자 추가)은 §3 정합·정상 작동(카드 10→16).
- **⏸ 다축 재설계 일시중단·이관 — 핸드오프: `docs/agent/HANDOFF_SIGNAL_REDESIGN.md`** (2026-06-21).
  사용자 판단: **스코프 과대**(경미 누락 2개[capex 2.6%·관계기업 0.8%, 분식 아님] 위해 검증된 신호엔진
  recall 5/6 통째 재설계). fitting 점검서 갈수록 새 갭(mix·OR구멍·분식 미포착) 누적 → 일시중단.
  S1~S3 구현·테스트·발견은 핸드오프 문서에 전량 인계(새 컨텍스트가 이어감). **재개 시 §9 규모 재평가
  먼저**(대안: 병행추가 vs capex만 최소수정 vs 전체재설계). 코드 자산은 `profiler.py`·`test_signal_profiler.py`
  유지(347 passed). → **원래 목표(전과정 파이프라인 측정 #2 삼성·#3 금융사)로 복귀.**
- **🔨 Phase1 신호엔진 근본 재설계 진행 — 설계: `docs/agent/PHASE1_SIGNAL_REDESIGN.md`** (2026-06-21).
  E2E 평가#1서 capex 급증·관계기업 추세감소를 신호엔진이 강조 못 해 6관점 전부 놓침 → 근본=
  "룰 열거 패러다임"(사람이 변화율 룰+임계 리터럴 열거, 안 한 이상은 영원히 사각). **다축 이상
  프로파일러로 전환**: 전 계정에 self(자기 시계열)+peer(동종 분포) 기준 5축(수준·변화금액·추세·
  변동성·구성비) 원점수 전수 계산 → 분포 꼬리를 후보. floor 이진컷·valid_yoy_base 폐기. A(Δ금액)=
  ②축·B(추세)=③축으로 흡수. grill 확정: 기준선 self+peer / D1 OR+가중합 / D2 하이브리드(universal만
  대체, 관계사슬·비율·정정 유지) / D3 분포 분위(개수상한 없음).
  - **회귀 baseline 고정**: `data/backtest/_REDESIGN_BASELINE.txt` — recall 5/6(세토피아만 미발굴)·
    삼성 FP 14·핵심분식 강도순위. 재설계 후 악화 0 필수.
  - **✅ S1 완료(self 4축 계산기)**: `src/signals/profiler.py`(delta/trend/volatility/mix_score +
    compute_self_axes). trend=단조성×|당기-최초|/자산(비율 아닌 금액, 기저폭발 없음). TDD,
    `tests/test_signal_profiler.py` 11 — capex delta>자본금, 관계기업 trend(단조1.0)>자본금 단언.
    전체 **338 passed·1 xfailed**(회귀 0).
  - **✅ S2 완료(정규화+통합강도)**: profiler.py `normalize_axes`(mid-rank 분위 [0,1])·`compute_strength`
    (OR플래그 어느 축이든 분위≥tail 0.8 + 가중합 strength 정렬 + tail_axes). 신규 6테스트(합성분포:
    capex류 delta flag·관계기업류 trend flag·정상 변화축 0 flag). 전체 **344 passed·1 xfailed**(회귀 0).
    **구현 중 발견(문서 §11b)**: mix 보완효과(관계기업 감소분 흡수 계정이 mix 2위로 co-flag) — 실데이터
    희석되나 mix calibration은 백로그. peer 수준축(①)은 S3 benchmark 연동서.
  - **✅ S3 완료(build_account_profile + 실데이터 실증)**: `build_account_profile(report)`(subtotal 제외·
    자산총계 자동추출→self 프로파일). probe `_e2e_profile_probe.py`. 신규 3테스트(실데이터 fixture).
    전체 **347 passed·1 xfailed**(회귀 0). ★**실데이터 발견(대주산업 leaf 105·flagged 37)**:
    **유형자산취득(capex) flagged=True**(순위15·delta+vol축) — 설계대로 잡힘 ✅. **관계기업투자 flagged=False**
    (순위39·trend_q 0.72 상위28%이나 tail 0.8 미달) — 단조감소 감지하나 **금액 작아(자산0.8%) trend score가
    깎임**. 사용자 "완만추세도 중요" 지적의 정확한 지점 — self축(금액기반)만으론 작은 단조추세 미달.
    → S4 peer 수준축 or 단조성 가중 보강 필요(문서 §11b 연장).
  - **⏭ 다음**: S4 — ①peer 수준축(benchmark 연동, 관계기업 회복 시도) + ②review_queue 통합·universal 흡수
    (관계사슬 유지) → S5 materials 프로파일표 → S6 백테스트 회귀(recall 5/6 유지+capex/관계기업 회복).
- **✅ 전과정 파이프라인 실측 #1 완료 — 리포트: `data/backtest/_E2E_MEASURE_00112457_2024.md`** (2026-06-20).
  하니스 `data/backtest/_e2e_measure.py`(corp·year 인자화·3개사 재사용). 운영 경로 그대로
  수집→정규화→온보딩(gate+S7+alias+G6)→Phase1→Phase2 실행, 단계별 시간·LLM 토큰·비용 실측.
  비용 캡처=`pydantic_ai.Agent.run` 래핑(운영 무수정). **회사 #1 대주산업(00112457/2024, 소형비금융)**:
  - **총 158초 · ₩1,365 · LLM 10호출**(S7 1+alias 1+G6 1+Phase2 6관점+반박 1). 입력 313,178·출력 20,608토큰.
    단가가정 $2.5/$10·₩1,380(gpt-5.4 실단가 미확정).
  - 단계 시간: collect 18s·normalize 9s·gate 5s·S7 10s·alias 4s·G6 13s·phase1 5s·**phase2 93s**(병목).
    비용 비중: **phase2 ₩976(72%)** > S7 ₩329 > G6 ₩47 > alias ₩13.
  - 산출물: 게이트 통과·S7 청크 10·queue 18·account_series 525행·Phase2 카드 계정13+회사6·반박 19.
  - **자가발견·수정**: 1차 run_sync 이중카운트(동기경로 S7/alias/G6 토큰 ×2, ₩1,699 과대) 발견 →
    run만 패치(run_sync가 내부 run 호출)로 수정·재실행. 캡처 10==실제 10·S7 90,698=자체보고값 일치로 확정.
  - **⏭ 다음(사용자 예정)**: 회사 #2 삼성전자(00126380)·#3 금융사(예 대신증권) 동일 하니스 측정
    (`uv run python data/backtest/_e2e_measure.py <corp> <year>`). 금융사는 S7 본문·관점 토큰 급증 예상.
- **✅ docs/user 최신화 — 전처리·Phase1·Phase2 반영** (2026-06-20). 구현(특히 Phase2 새 파이프라인)과
  사람용 문서의 stale 제거. 편집: `MULTI_AGENT.md`(6관점 모델 전부 GPT-5.4로·반박 에이전트 부활
  섹션 재작성·다이어그램 최종 산출물=의심건 카드 목록), `FEATURES.md`(5개 역할→6관점+별도 반박·
  산출물 카드), `UI.md`(6관점·반박·카드 필드 표수N/4·반박판정·온보딩 필수 화면; 구 UX 문서 통합), `LIMITATIONS.md`
  (§6 Phase2 실호출 E2E 미검증 한계 추가), `ONBOARDING_LLM_PLAN.md`(확정 운영정책=온보딩 필수화·별칭
  사람 수동), `LLM_MODEL_COMPARE.md`(Phase2 6관점·반박도 gpt-5.4). grep 검증: Gemini(관점)·"5개
  에이전트"·"반박 관점은 왜 없나" 0건, mojibake U+FFFD 0건. BACKTEST/VERIFICATION 류는 Phase1 검증
  기록이라 비범위(Phase2 실 E2E 미실행이라 거짓 "검증완료" 표기 회피). **주의: Phase2는 구현·단위
  테스트 완료지만 실 LLM 2+사 E2E는 미실행**(문서에 그대로 명시).
  - **후속 보강(실험 결과 반영)**: `P1_AUDIT_HARNESS.md`(§6 E2E 충실도=원문 1,736행 소실 0·불일치 0
    신규, 실행방법 §7로 이동), `VERIFICATION.md`("검증이 실제로 고친 것" 표=BS −52조→+0.08조·member-sign
    334→0·USD 게이트차단·hollow-PASS 차단), `DATA_SCOPE.md §6`(정정공시 S9 가시화·정합성 E2E를 검증완료로
    이동, provenance·손익CF 검산만 잔존). mojibake 0.
- **🎯 Phase2 단단설계 확정 — 문서: `docs/agent/PHASE2_DESIGN.md`** (2026-06-20, grill with docs).
  Phase1(거의 완료, UI 제외) 후 Phase2(L3/L4 멀티에이전트 교차검증)를 기초 MVP → 단단설계로.
  grill 17개 결정 합의. 핵심: 산출물=**의심건 카드 목록**(계정 섹션+회사레벨 섹션), 교차검증=
  **코드 결정론 클러스터**(하드코딩 키워드 crosscheck 폐기), 근거=**EvidenceRef 코드검증**(환각 탈락),
  반박=**전용 반박 에이전트 1회 일괄**(제거 금지·강등 플래그만, §9), 점수·확신도·표수=코드 산정,
  개수상한 없음(결함① 교훈). 기존 코드 처분: crosscheck 폐기/perspectives 교체+병렬/synthesis→반박
  전환/AccountFinding 재사용. 구현=결정론 골격 먼저 TDD(S1~S7, PHASE2_DESIGN §7).
  - **✅ S1 완료(2026-06-20, 스키마)**: `src/schemas/suspicion.py`(SuspicionItem·scope account/company·
    grounding validator: account면 account_id·cited_value 필수, 빈 description 거부·locator build/parse
    round-trip·cluster_key 분기·INTERNAL_PERSPECTIVES 4) + `findings.py` AccountFinding 카드 메타
    (vote_count·internal_total=4·reference_badges·rebuttal_verdict·cluster_key, 전부 optional). TDD
    RED→GREEN, `tests/test_suspicion_schema.py` 10 + 전체 **289 passed·1 xfailed**(회귀 0).
  - **✅ S2 완료(2026-06-20, 근거검증)**: `src/report/grounding.py`(build_account_index·
    verify_account/company_suspicion·verify_suspicions·GroundedSuspicion). 환각 탈락=유효숫자
    동일성 대조(원·백만·억 스케일 무관, float 직접비교 회피) — 계정 미존재·금액 불일치=grounded
    False, 추세/비율 비금액 인용=계정존재 grounding(value_verified False), 외부 URL 없으면 탈락,
    탈락도 reason 동반 전부 반환(silent drop 0). TDD, `tests/test_grounding.py` 8 + 전체
    **297 passed·1 xfailed**(회귀 0).
  - **✅ S3 완료(2026-06-20, 카드조립)**: `src/report/card_builder.py`(cluster_suspicions·build_cards).
    grounded만 계정 cluster_key로 묶고(회사레벨=issue_type 버킷 별도), vote_count=내부 4관점 distinct
    (외부·동종은 reference_badges만, 미가산), materiality=절대금액 0..1 정규화·anomaly=신호참조 존재·
    confidence=value_verified+표수+매핑강도 결정론, risk_level=클러스터 최대. 카드=AccountFinding 재사용.
    버그 1건(key 미정의 가능) self-발견·수정. TDD, `tests/test_card_builder.py` 11 + 전체
    **308 passed·1 xfailed**(회귀 0).
  - **✅ S4 완료(2026-06-20, 정렬·렌더) — 결정론 골격 4단계 종료**: `src/report/card_report.py`
    (order_account_cards·order_company_cards·build_card_report·render_card_markdown). 정렬=표수 내림→
    동점 시 금액 내림, normal_dominant는 하단 강등(제거 X), 회사레벨 별도 섹션, 0건은 검토범위(계정·관점
    수) 명시(빈 화면 금지). TDD, `tests/test_card_report.py` 7 + 전체 **315 passed·1 xfailed**(회귀 0).
    ★**S1~S4로 LLM 없이 "검증 의심건→카드 markdown"까지 결정론으로 완결**.
  - **🎯 S5 설계 확정(2026-06-20, grill) — PHASE2_DESIGN §9**: 관점 출력=`PerspectiveOutput{status,
    suspicions:list[SuspicionItem]}`(봉투 1개), SuspicionItem에 선택칸 3개 추가(related_accounts·
    prior_value·prior_year), perspective 라벨 코드 재주입, 프롬프트=공통 system(코드)+관점별 focus
    (`config/playbooks/perspective_prompts.yaml`), 검사=양식 PydanticAI/환각 S2 단일. 관점별 스키마(3안)는
    비용 대비 손해라 기각.
  - **✅ S5 완료(2026-06-20, 관점 구조화·병렬) — additive 무회귀**: 신규 경로 추가, 구 PerspectiveAssessment·
    crosscheck·multi_agent 무수정(제거는 S7). `SuspicionItem`+선택칸3·`PerspectiveOutput`(suspicion.py),
    `config/playbooks/perspective_prompts.yaml`(공통+6관점 focus), `perspective_runner.py`(playbook 로딩·
    system prompt 합성·PydanticAI 출력강제·perspective 코드재주입·키없음/에러 deferred·material 수집),
    `card_pipeline.py`(6관점 asyncio.gather→verify S2→build_cards S3→report+render S4). 환각검사=S2 단일.
    TDD, 신규 9(runner6+pipeline4, schema 보완분 포함) + 전체 **324 passed·1 xfailed**(회귀 0, 기존
    test_integrated_report 전부 유지로 additive 입증).
  - **✅ S6 완료(2026-06-20, 반박 에이전트)**: `src/report/rebuttal.py`(build_rebuttal_agent·
    build_rebuttal_input·run_rebuttal·apply_rebuttal) + `RebuttalEntry`/`RebuttalOutput`(suspicion.py) +
    playbook `rebuttal` 섹션 + card_pipeline 반박 배선(build_cards→반박→정렬). 균형 반박(과도 적대 금지),
    입력=카드+그 카드 의심근거, cluster_key 매칭(회사레벨 cluster_key=company:{issue} 보완), 위험도 숫자
    불변·verdict 플래그만, 카드 제거 0, 반박 없는 카드는 "반박 미수행" 명시, 키없음/에러 빈 출력(카드 생존).
    TDD, 신규 10 + 전체 **334 passed·1 xfailed**(회귀 0).
  - **✅ S7 완료(2026-06-20, 구경로 청소) — Phase2 신규 파이프라인 S1~S7 종료**: `crosscheck.py`(§3 위반
    키워드 매칭)·`synthesis.py`·`multi_agent.py` 삭제 + test_integrated_report 의존 테스트 8개 정리.
    src 구경로 참조 0(grep). 전체 **326 passed·1 xfailed**(334−삭제8, 신규 실패 0). card_pipeline이 유일 경로.
  - **🎯 Phase2 새 파이프라인 완성(S1~S7)**: SuspicionItem·EvidenceRef 검증→근거검증(환각 탈락)→
    계정 클러스터·N/4·점수·확신도→6관점 병렬(playbook)→반박(균형·미수행 명시)→정렬·카드 렌더.
    설계 단일출처 `PHASE2_DESIGN.md`. 누적 신규 테스트 ~67, 회귀 0.
  - **🔍 code-reviewer 리뷰 후속(2026-06-20) — §9 검증 후 선별 반영**: 무비판 수용 안 함.
    - **수정 완료**: **P2-1** grounding index에 sj_div 한정 키 추가(`{sj_div}:{key}`)+verify 우선조회 →
      동명이계(IS/CF 같은 계정명·다른 금액) 타 표 금액 환각 통과 차단. 회귀테스트 추가(9 passed).
      **P1-2** apply_rebuttal in-place mutation docstring 명시.
    - **기각/보류(사유)**: **P1-1**(grounding 유효숫자) — 리뷰어 `_sig_match` 자릿수차≤4 패치는 **기각**
      (의도적 억/조 스케일 관용을 깨 거짓탈락↑ = §9상 더 나쁨). 단 **라운드 숫자 붕괴**(예 30,000,000,000
      →유효숫자"3"<3자리→금액검사 우회, 환각도 통과도 안 됨)는 진짜 갭. 올바른 수정=단위(억/조/백만) 인식
      값 파싱이나 스케일 모호성(메모리 gpt 백만 오독) 때문에 precision/recall 트레이드오프 → 별도 설계 백로그.
    - **✅ 해결(①② 별도 비율 표면화)**: 파생층 fs_div 불완전개방(비율 CFS고정) = **해결**. `_ratio_time_series`가
      fs_div별 build_ratio_report 후 fs_div 태그(queue·summary는 CFS 유지 무회귀). 삼성 112행(CFS56+OFS56)·
      대주 96행, build_fs_div_coverage gaps==[](gap 찾은 원장이 닫힘 실증). 주석은 측정상 gap 아니라 미변경.
      전체 404. `build_fs_div_coverage`는 영구 가드로 향후 fs_div-고정 누락 자동 포착.
    - **✅ 해결(SCE 자기주식 신규발생 사각#2)**: occurrence_state가 계정층에만 있고 SCE엔 없어 자기주식 신규
      취득이 raw로만 흐르던 것 = **해결**. `metrics_panel.sce_occurrence_states`(change_canonical 단위=D18
      정체성, leaf 불안정 회피)로 신규/소멸 판정, sce_cells에 occurrence_state 부착 + 소멸 synthetic 표면화.
      삼성 자기주식취득 appeared 실측 확인. trend 관점이 신규 자본거래 우선 검토(sce_role 프롬프트). 전체 402.
      **미완(D18 백로그)**: 주석 XBRL 숫자표 occurrence는 정체성 불안정으로 온톨로지 전까지 제외.
    - **✅ 해결(주석 grounding 사각#3)**: 담보·특수관계 등 서술형 공시가 note_sections·report_review_chunks
      (HTML)에 사는데 grounding 인덱스는 XBRL fact만 커버 → 진짜 공시를 "환각"으로 죽이던 허위탈락 = **해결**.
      `build_account_index(note_disclosures=...)` + `_verify_note_suspicion`(공시 텍스트 금액 실재시 grounded,
      허위금액은 탈락). card_pipeline이 materials[note] 서술형 공시를 정규화 전달. 대주 실측: 담보 54,345·
      특수관계 233,546 둘 다 탈락→grounded 부활, 허위 99,999 탈락 유지. 전체 397 passed.
    - **✅ 해결(external 실검색 배선)**: external 검색 파이프라인(create_external_assessment)이 카드
      파이프라인에 미연결(死코드)이라 구조적 0건이던 것 = **해결**. `run_external_suspicions` 어댑터 신설
      (Gemini 검색어생성→구글 grounding 검색→출처 URL 단 company SuspicionItem). card_pipeline `_run_one`이
      external만 실검색 경로로 분기. 2케이스 E2E로 死코드 0 vs 실검색 0 구분: 삼성 grounded 3건(영업이익
      398%↑ 원인)·대주 0건(소기업 뉴스 없음, 정상). GOOGLE_API_KEY 필요. 전체 400 passed.
    - **✅ 해결(change→trend 재편)**: change·numeric 단위중복(63%)을 역할분리로 해결. change 식별자를
      trend(추세)로 개명, numeric=당해 급변(yoy) 전담·trend=다년 단조방향(↑↑/↓↓·완만 드리프트) 전담.
      소급재작성은 추세와 무관(신뢰성 신호)이라 관점 경로 삭제(엔진은 dormant 보존). 대주 실LLM E2E:
      numeric∩trend 중복 **63%→20%**, trend 고유 8계정 신규(관계기업투자 등 다년드리프트 흡수, overfit 아님).
      파급: suspicion·perspectives·perspective_runner·grounding·materials·findings·event_routing.yaml·
      perspective_prompts.yaml. 전체 398 passed(소급-관점 테스트 4종 삭제 반영).
    - **✅ 해결(flow 관계 근본수리)**: SuspicionItem.related_accounts 카드 미전파 = **해결**. scope에
      "relationship" 3번째 단위 신설(계정 쌍·교차재무제표) → build_cards가 relationship_cards 별도 산출,
      cluster_key `rel:`+정렬다리(A↔B==B↔A·교차FS 동일규칙). 대주 실LLM E2E: flow 6/6 전부
      scope=relationship, 연결↔별도 현금 관계 부활(진단 시 소실). change의 prior_value/prior_year
      부활은 후속(사용자: 결과 확인 후 진행). 산출물 `data/backtest/_E2E_FLOW_REL_00112457.json`.
    - **백로그(P3 등)**: P1-2 model_copy 불변 리팩터 / 이중 timeout(perspective_runner·rebuttal wait_for) /
      note_material KeyError 방어 / 회사레벨 카드 materiality=0 반박입력 표기 / deferred 관점 리턴 노출 /
      industry scope=account 가이드 / **change prior_value·prior_year 死필드 부활(死필드 부활 2탄)**.
  - **⏭ 다음(사용자 결정) — Phase2 잔여 백로그**:
    1. **UI 배선**(dashboard에서 build_suspicion_cards 호출·카드 렌더, Phase1·Phase2 통틀어 UI 미완).
    2. **실 LLM 2+사 E2E**(비용 발생, run_llm=True 실측 — 관점·반박 실호출 품질·토큰 확인).
    3. **assessment 클러스터 완전 제거**([~] 보류분): perspectives.py·external/industry assessment 함수·
       external_agentic — dead이나 결정론·external/industry 테스트와 얽힘. external_material/industry_material만 유지.
    4. OpenAIModel→OpenAIChatModel 마이그(전 파일 공통 DeprecationWarning).
    + Phase1 잔여: 전체 corpus --force 재정규화(~30% stale)·온보딩 일괄실행 수동검증.
- **✅ 온보딩 alias 제안 개선 — 계획·결과: `docs/agent/ONBOARDING_LLM_PLAN.md`** (2026-06-17). 검증서 발견한
  alias 약점(적중~75%·confidence가 오답 못거름) 개선. **코드 반영**(`src/report/alias_suggest.py`): ②배치화
  (계정당 N회→회사당 1회, 호출 72→4·반환형식 불변) + ③일반원칙 힌트(SYSTEM_PROMPT에 "불확실하면 기타보류"+10유형
  예시). pytest 10 passed 무회귀. **수렴 사다리 라운드1**(무표준코드 ph≥10 7사): 신규 오답 4유형(특수상품
  과일반화·폐기/처분·계속중단영업·자본거래방향) 발견 미수렴이나 저conf. **일반원칙 힌트로 확정** + 새 2사
  (00143651·00261443) 테스트서 **고conf(>0.85) 오답 소멸·애매는 저conf**로 흡수 확인. 실험 누적 ~₩800(운영전수
  금지). ①high는 gpt-5.4 Chat API가 pydantic+reasoning 동시 미지원으로 보류(Responses 전환 필요). **남은: ④UI
  (confidence+reason 노출)·회사당 배치 호출 정식 적용은 코드에 반영됨**.
- **✅ Phase1 E2E 충실도 재검증 완료 — 결과: `data/backtest/_p1e2e_VERDICT.md`** (2026-06-17). 4사 층화
  (규모×금융업×양식세대 직교: 대신증권 26조·00125521 1.6조·대주산업 1114억·00108649 936억)를 **온보딩부터**
  재실행(renormalize --force→신호→material→정성 재수집). DART raw 원문 전수항목(oracle)을 normalized와 1:1 추적
  (추적표 행수==oracle 항목수 강제 → 통독 사각 차단). **저번 실패(통독 대충) 구조적 차단**: 플래그 행마다 원문·DB 인용.
  - **재무 충실도 PASS**: 4사 소실 0·금액불일치 0(원문 1,736행). 초기 자동플래그 13~16건은 **전부 거짓양성**
    (SCE 2D 별도테이블·CIS→IS 통합·배당 -abs 부호 = 추적표 도구 사각, §10 도구경계≠감사경계). 도구 보강 후 0 수렴.
  - **결함① (진짜·정량) — ✅ 수정 완료(2026-06-19, A안=개수상한 제거)**: 유의성 큰 강등계정이 LLM material에 누락(2종오류).
    근본원인=`_top_unmapped_material_accounts` head(5)·`_account_level_series` limit(40) **개수상한** + `unmapped_extension_account`만 게시(id_label_conflict 제외).
    **수정**: PLAN §3(모든 정보 추출→에이전트가 가져감)에 따라 개수상한 둘 다 제거(금액>0 전부 게시) + unmapped 조건을
    `canonical==OTHER_CANONICAL` 포함으로 확대(id_label_conflict 강등 회수). perspectives rules에 유의성 우선 가드 1줄.
    비용 실측 +₩110~150/회사(상한 제거). 검증: 대신 순이자손익(-1,961억) 회수=True, unmapped 5→24건·금융구 58건, pytest 266 passed.
    코드리뷰 P1(drop_duplicates) 반려(account_id 공유로 진짜계정 삭제=회귀 실증). series_key 뭉침 분리는 별도 백로그.
  - **결함② (운영 갭·정성) — ✅ 수정 완료(2026-06-19, 온보딩 LLM 한버튼 필수화)**: 서술형 감사관심(소송·특수관계·우발)은
    사업보고서 본문에 있고 S7 청크선별 실행해야 material 전달. 기존엔 LLM 3종(S7·alias·G6)이 전부 '선택'이라 미실행이 기본.
    **수정**: `run_full_onboarding`(gate→S7→alias→G6 순차 graceful) + `can_enter_analysis`(게이트통과+S7·G6 완료해야 진입,
    LLM실패는 경고+사람확인 강행) + UI 한버튼('온보딩 일괄 실행'). S7 키워드 fallback 제거(materials·review_chunks) +
    note_material 미선별 경고(silent 0 금지). alias는 사람이 등록(자동등록 금지 유지). 비용 실측 회사당 ~₩200~660(S7 본문통독 80%+).
    pytest 269 passed. 코드리뷰 P1(빈dump G6호출)·P2(absent/error 구분) 수정. S7 본문 축소는 별도 백로그.
  - **검증 스크립트**(재현): `_p1e2e_profile.py`·`_p1e2e_select.py`·`_p1e2e_collect.py`·`_p1e2e_trace.py`·`_p1e2e_s7.py`.
  - **🔍 입체 사각 탐색 결과(2026-06-19, 4영역 병렬 Explore) — 미수정, 우선순위 목록**:
    서브에이전트 발견 무비판 수용 안 함(§9). 교차검증(여러 에이전트 독립발견)+§9·§10 부합한 것만 채택.
    · **[높음] ①수집→게이트 silent 실패 사슬 — ✅ 핵심 수정(2026-06-19)**: (c)게이트 hollow-PASS **재현·차단 완료**.
      재현: 대신 DB BS 75행 삭제 → 수정 전 gate_passed=True(BS 통째 결손도 통과). 수정: `_g1_verdict` 순수함수 —
      BS 항등식 검산 0건이면 passed=False(검산불가≠통과, §9 바닥). 재현 후 gate_passed=False, 정상 DB는 True 유지(회귀0).
      test_onboarding_gate 5개(게이트 첫 단위테스트). pytest 276 passed.
      **하위갭 추가 수정(2026-06-19)**: SCE-dead(전행 unmatched·SCE표준화=FAIL) hollow-PASS도 재현·차단 —
      `_g1_verdict`에 sce_std 파라미터(=='FAIL'이면 passed=False). 재현 gate_passed True→False, 정상 유지. pytest 277 passed.
      부분수집 OFS결손은 재현결과 무영향([~]: primary fs로 정상분석·별도사는 BS바닥이 차단)이라 미수정.
      **남은 하위갭(미수정·백로그)**: finstate_all 예외 명시기록(graceful은 silent 악화라 보류, 게이트 바닥이 하류 차단),
      G2~G5 개별 단위테스트(G1만 추가됨).
    · **②통화 — ✅ 진짜결함 확정·수정(2026-06-19, A안 게이트 차단)**: 측정 결과 단위혼재(천원) 아니라 **외화통화**가 진짜.
      전 corpus grep USD 5,792행(39 회사연도, 전 표 USD). normalized가 USD 금액을 원 환산 없이 저장 → ~1300배 축소,
      항등식 안 깨져 게이트도 못 잡던 silent. **수정**: run_currency_check + _currency_ok로 비KRW 재무를 게이트 차단(gate_passed=False),
      _print_report 명시. 환율환산(B)은 정확도 위험이라 미채택. user 한계문서 docs/user/LIMITATIONS.md 작성. pytest 279 passed.
    · **③CF 부호 — ✅ 거짓양성 판정(2026-06-19, 측정 후 수정 안 함)**: 300 DB 측정 — 취득 양수95%·처분 양수100%로
      부호 뒤섞임 아니라 **일관 절대값**(DART가 투자활동 항목 부호없이 신고, 방향은 계정명). 투자활동현금흐름 소계 100% 직접존재(합산불필요)+
      부호의존 코드 0건+CF 결정론 점수제외 → 무영향. 가설(뒤섞여 합산오류) 빗나감.
    · **④절대임계 — ✅ 거짓양성 판정(2026-06-19, 측정 후 수정 안 함)**: 400 회사연도 자산 최소 330억·자산<100억 0건.
      floor=max(자산1%,1억)에서 모든 회사 자산1%(≥3.3억)>1억 → 자산1%가 지배, 1억 절대바닥 미작동. §3 리터럴이나 상장corpus 규모상 실害0.
      초소형사 유입 시 과민 가능성은 백로그(현 분석대상 아님).
    · **입체탐색 종결(2026-06-19)**: ①통화=진짜·게이트차단 수정 / ③CF부호=거짓양성 / ④절대임계=거짓양성.
      게이트 hollow-PASS(BS·SCE)·통화 차단이 핵심 수정. "재현/측정 먼저"가 진짜(통화)와 거짓(CF·절대임계)을 정확히 갈랐다.
    · **[제외] 설계의도/기능확장**: flow 흐름지표만·numeric queue[:10](series는 결함①으로 전량전달), 법인세·자기주식 미구현신호(확장영역), 결함①②중복분.
  - **S7 본문 축소 — 검토 후 현행유지 결정(2026-06-19)**: 측정 결과 PART선별 13%·재무제표본표 제거 3%로 효과 미미.
    진짜 덩어리는 III(재무에 관한 사항)가 입력의 80%+이고, III의 94%가 주석의 대량 정형표(증권사 금융상품 종목평가표 등,
    서술 문장은 6%뿐) — 금융사 집중(대신 III 26만tok vs 대주 5만). 대량표 압축/키워드청킹은 검토관심 누락 위험이라
    누락0 우선해 현행 통째 유지(회사당 ₩200~660 수용). 재검토 시 타깃=대량 반복표, PART/본표 아님.
  - **⏭ 다음(사용자 결정)**: ~~결함①~~(✅) / ~~결함② 온보딩 필수화~~(✅) / ~~S7 축소~~(검토후 현행유지) /
    전체 corpus --force 재정규화(~30% stale) / 다른 샘플 확대. **온보딩 일괄실행 실제 화면 수동검증 미수행**.
- **✅ E2E 충실도 감사 완료 — 결과: `data/backtest/_E2E_AUDIT_RESULTS.md`** (70차). 6사 층화(삼성·KB·카카오·
  두산·LG·진양)를 최종 PHASE1에 태우고 DART 원본 통독 ↔ material 대조. **갭 4개**:
  - **G1 [수정완료]** `company_report.py` target_year=2025 리터럴 고정(§3 위반) → 최신연도≠2025 회사 전 신호 빈값
    (6사 중 3사 큐=0 재현). 데이터 구동(`_available_norm_years`/`_present_years`)으로 수정 + 회귀테스트.
    **무회귀 243 passed·분식 target 불변**. 큐 복구(카카오46·KB18·진양2).
  - **G2 [수정완료]** 원문 청크=0 → 키워드 baseline fallback 배선(note_material). 삼성8·두산11·LG7·진양6 도달.
  - **G3 [수정완료]** 정정 이력 → change_material restatement_history 주입. 두산 11건 도달.
  - **G4 [수정완료]** event terms → routed_timeline terms(발행총액·전환가·자금용도) + cap sentinel. 카카오 도달.
  - **숫자/의미 정합(71차) [완료]**: 6사 핵심계정 raw==norm **정확 일치·소실 0**(account_id 대조). 큐 실신호.
  - **G6 [수정완료]**(73차): 주석 발췌가 39% 헤더 집던 갭 → note_material 금액블록 우선+파일 fallback(방식B
    격리). 미surface 갭 **59→1**, 실질발췌 25→83, 빈노트 67 무날조. account_finding·테스트 무변경.
  - **SCE 노이즈 [수정완료]**(74차): unmapped material에서 sj_div='SCE' 제외(AGENDA_DD_SCE2D 결정을 해당 경로에 적용). KB SCE 57→0, 진짜계정 보존.
  - **금융 미매핑 [진단정정+1단계 착수]**: "COA 제조업중심"은 틀림 — 실체는 무표준코드(온보딩 quirk 영역)+SCE노이즈+보험계정 소수. 무표준코드 라벨은 전역별칭 위험(이중계상)→
    **온보딩 LLM 별칭 제안기**(75차 `src/report/alias_suggest.py`): 후보검색=코드·분류선택=LLM·적용=사람확인. 환각 앵커링·자동적용 금지.
    **UI 배선 완료**(76차): render_quirk_form에 render_alias_suggestions 프리필 — 제안 표시→사람 확인 클릭 시에만 등록(_register_suggestion), 기타 제안 disabled.
  - **금융 미매핑 근본수정 [완료]**(77·78차): "보험 9건"은 부정확 — 실측 원인=id→canonical 1:1이라 다중표 개념(OCI)이 등록 statement 밖서 강등(`_FINMAP_ROOTCAUSE.md`). **cross_statement_ids 다중표 매핑** 구현(config·mapper·pipeline 가산적 구제). KB OCI 4종 기타→정확 CIS canonical, 기존매핑·SCE·백테스트 5/6 불변. 격리 diff로 무회귀 증명.
  - **남은 백로그**: A2 잔여(보험순금융손익 cross 등록)·B(재보험계약자산 신규 canonical 1)·A1(CF 당기순이익 statement처리)·**전체 corpus persist --force(stale 실재 확인됨 — 6사 재정규화서 SCE 매핑 변동 관측)**.
- **⏭ (참고) 감사 계획 원본: `data/backtest/_HANDOFF_E2E_AUDIT.md`**.
  ★PHASE1 S0~S11 종료(`PHASE1_EXIT_GATE.md`). 아래는 그간 진행이력.

- **🔧 S7 구현 진행 중 — 설계: `data/backtest/_HANDOFF_S7.md`** (5단계). 진행:
  - **Step1 [x] 수집기**(contract 53차): `DartCollector.document(rcept_no)`(전체 사업보고서 XML, ValueError→""흡수) +
    `src/collect/report_doc.py`(collect_report_doc 단건 / collect_report_docs ThreadPool 동시 batch, 저장
    `raw/report_doc/business_report.xml`). 신규 테스트 6 + pytest **214 passed**. mojibake 0.
  - **Step2 [x] PART 추출기**(contract 55차): `src/notes/report_parts.py` — `extract_parts(xml)`가 TITLE 로마숫자
    헤더로 PART 슬라이스(목차 TD 무시·표→행 텍스트·BeautifulSoup), `select_part(parts,patterns)`가 논리섹션을
    시대 다중패턴으로 선택(`LOGICAL_PARTS` 7종). **실문서 재현**: 삼성2023=12파트(대주주→X·감사→V)·
    삼성2015=11파트(XII없음·X=이해관계자·감사→IV), 두 시대 모두 적중. 신규 테스트 7 + pytest **221 passed**. mojibake 0.
  - **Step3 [x] baseline 씨앗**(contract 56차): 외부 LLM 아닌 **내가(Opus) 직접** 층화 샘플 통독. `_s7_baseline_sample.py`로
    301 회사연도(신112/구189) 원문 수집(`_s7_sample/`), 2건 전문 Read + 전수 Grep. ★**고빈도어=회계정책 보일러플레이트**
    (우발부채96%·담보100% 변별력 없음), **저빈도 이벤트어가 변별**(과징금14%·자본잠식4%·리픽싱3%). 산출:
    `config/playbooks/report_review_keywords.yaml` — 2단 모델(anchors/event_signals/null_markers) 13 공시유형, 빈도% 근거주석.
    검증: 고위험 바이오사 12유형 발화 vs 평범 제조사 6일상유형(변별 작동). pytest **221 passed**, mojibake 0.
  - **Step4 [x] 본체(B안) + GPT vs Opus 비교**(contract 57차): `src/report/review_chunks.py`(ReviewChunk 스키마·
    build_chunk_agent gpt-5.4·select_review_chunks usage캡처·persist content_chunks) + onboarding.py 배선(버튼). 신규 테스트 5.
    **GPT vs 나(Opus) 10사 비교**(`_S7_ONBOARDING_COMPARE.md`): 활성 공시유형 크게 일치, GPT 환각 0(grounding 103/103),
    강점=전환사채 리픽싱·콜옵션 감독지침·공정위 제재·관리종목·계속기업 강조 다 포착, 약점=재작성 과발화 1~2건·SPAC 합병 미표면화 1사.
    **비용**: 평균 in 12,863·out 1,181 토큰·9.7초, 회사당 약 ₩40~110(단가가정·식명시), 전체 5,129사 ₩20만~58만. 내용필터로 입력 ~1/9 압축.
    판정: B안 채택 가능, baseline은 fallback. pytest **226 passed**, mojibake 0.
  - **Step5 [x] Phase2 투입 — S7 전체 완료**(contract 58차): `review_chunks.load_content_chunks` + `materials.note_material`이
    `report_review_chunks`(company_quirks content_chunks)를 note 관점 material로 실음 → `_note_material`→`perspectives` 경로.
    선별 없으면 빈 리스트 graceful. 비교 user 문서화(`LLM_MODEL_COMPARE.md` 온보딩 청크선별 섹션). 백테스트 구조상 무영향
    (run_backtest는 결정론 신호만, materials 미호출 grep 확정). pytest **228 passed**, mojibake 0.
  - **✅ S7 완료(Step1~5)**: 원문수집(report_doc)→PART추출(report_parts)→baseline씨앗(report_review_keywords.yaml)→
    온보딩 청크선별(review_chunks, GPT≈Opus·환각0·회사당 ₩40~110)→Phase2 note material 투입. **보정 권고(미적용)**:
    ①재작성_정정 정상소급 가드(프롬프트) ②합병/SPAC 앵커 보강.
  - **S8 [~] 비범위 마감**(contract 59차, 실측결정): 별첨 감사보고서를 50 회사연도로 측정(`_S8_KAM_COVERAGE.md`·
    `_S8_ATTACHMENT_PROBE.md`). ★**2019+ 공시는 본문 PART V가 KAM 담음**(별첨에만 KAM=0), 별첨 유일출처는 FY2018
    과도기 대형 분식사 2건(두산·셀트리온, KAM 도입 첫해)뿐·probe로 이미 추출. 운영엔 PART V로 충분 → S8 제품화 불필요.
    수집경로(`document_all`) 확인됨, 백테스트 필요시 일회성 추출. `DATA_SCOPE.md`에 한계 1줄 기록.
  - **잣대 교정(60~62차)**: S8/S9/S10을 "분식 변별"로 재던 게 틀림 → 목표는 "DART 유용정보 끄집어내기". S9/S10 미흡수분 측정
    (`_S9_S10_ABSORPTION.md`): S9(정정이력)≈S7 미흡수·S10(event 스트림) 미흡수. S9 규모(`_S9_SCALE_COST.md`): 재무정정 ~6,600건·과거연도 28%.
  - **S9-B [x] 구현**(contract 63차): `DartCollector.filings`(final=False) + `src/collect/correction.py`(parse_corrections A·
    extract_correction_header B·collect_corrections 저장 corrections.json). 효용=**데이터 출처(원본/정정본)·무엇이 바뀜**(분식 아님).
    실문서 검증: 셀트리온 5 과거연도 "재무제표 재작성"·두산 첨부정정 vs 재작성 분류. 신규 테스트 6, pytest **234 passed**, mojibake 0.
  - **S9 배선 [x] — S9 완료**(contract 64차): 수집(collect_company_years→include_corrections→corp단위 corrections.json+summary
    restated_years)→읽기(`restated_years`/`load_corrections`)→화면(`onboarding.render_restatement_badge`: 재작성 연도면 ⚠"정정본·비교주의"
    배지, 아니면 출처 caption). **end-to-end 실데이터**: 셀트리온 재작성 {2016~2020}·소형사 {}. pytest **236 passed**, mojibake 0.
    효용=데이터 출처(원본/정정본) 가시화(분식 아님).
  - **S10 [x] 구현 — S10 완료**(contract 66차): event 36 + report 28 전수수집(`src/collect/events.py`·opendart event/report 어댑터·
    spike include_events). **2경계**: ①별도 참조저장(raw/events.json·reports.json, 재무DB 미연결=오염차단) ②compact 라우팅 투입(토큰차단).
    가치선별=코드(`event_routing.yaml` 타입→관점, 전 회사 동일)+관점 LLM. materials numeric/flow/change에 report_event_timeline 주입.
    실데이터: 바이오(영업정지→numeric·CB/유증→flow)·두산(합병/분할→change). 신규 테스트 6, pytest **242 passed**, mojibake 0.
  - **분석 근거**: `_S10_ANALYSIS.md`(report 중복·event 신규)·`_S9_S10_ABSORPTION.md`. event=시점+조건 신규차원, report=구조화(일부 신규).
  - **S11 [x] 종료게이트 — Phase1 종료**(contract 67·68차): `docs/agent/PHASE1_EXIT_GATE.md`. ★**잣대 교정(68차)**:
    분식 아니라 **일반 회사 재료 완전성**이 게이트. 정상 10/10이 review_queue 13~60·ratio·unmapped·flow/change 산출 →
    Phase2 투입 가능. Phase1산출→관점 라우팅표(전 회사 동일). **정직한 갭**: 주석=0(미수집)·event/correction 미수집·
    persist ~30% stale → 운영 전 수집 동반 필요. 분식 백테스트(recall 5/6·FP0)는 **회귀가드로 강등**(게이트 정의 아님).
    문서정리: COVERAGE S7~S11 [x], README 등록, _S10_ANALYSIS 개수정정(28/36).
  - **✅✅ PHASE1 마무리**: S0~S11 종료. 수집(S7~S10)·정규화·신호·종료게이트 완료. S6분기·S8별첨은 의도적 비범위.
  - **⏭ 다음(사용자 예정)**: **10사 E2E 테스트** — 실제 Phase1 수집→정규화→신호→Phase2(6관점 LLM) 넘기기까지
    잘 도는지. + 잔여 **전체 corpus persist --force**(~30% stale: _align제거·alias·신규 정규화 미반영).

- **✅ 2026-06-15 세션 (S3·S4·S5·S6 마감 + 신규 신호 + 적대감사 수정)** — contract 41~49차:
  - **S3 [x]**: 5종 신호 확장(df4e1c8) 완료기준 측정 — 분식16사 깔때기 sj_div별 CIS10·CF50·SCE9(0→양수). `COVERAGE_REMEDIATION` [x].
  - **S5 [x]**: 결정론 절대임계 폐기(§3 업종무시=버그). 수준판단은 Phase2 perspectives가 이미 수행(ratio_time_series→material_board, "수준 이상" 지시, industry 피어). 추가코드 0.
  - **S6 [~]**: 분기/반기 **의도적 비범위(연간전용)** — 누계환산·비감사 정합성노이즈·복잡도. `DATA_SCOPE.md §2`에 한계 문서화.
  - **S4 [x] 종료**: IFRS16(유동/비유동리스부채 단기·장기·괄호 변주)·관계기업투자(어순/공백) alias 보강(mapper 8/8 재현). 01406618=원공시 XBRL 오태깅→기록보류. member-sign 닫힘.
  - **신규: SCE 가로항등 anomaly 신호**(46차, `sce.py:sce_horizontal_identity`) — 총계=지배+비지배 모순(원공시 내부 부호모순)을 dump §F에 리스크 후보로 노출. 00141477·00260879 raw확증. materiality tol(100만/0.5%).
  - **적대 자가감사(48차) + 수정(49차)**: ★발견 — `_align_member_signs_to_bare`가 차감 너머 **비차감 원공시모순을 'grand 진실' 추측으로 뒤집고 소계 방치**(overreach). **제거함**(차감은 _apply_sign 담당). 이제 비차감 모순은 충실 보존 + 가로항등/검산이 노출. label_priority·alias보강·00545716 quirk는 감사 CLEAN. (선재 alias 충돌 7건 별도 기록.)
  - **member-sign 검증(41차)**: audit 334→0·non-audit 진짜결함 0·00141477=원공시모순(우리버그 아님, raw확증).
  - **⏭ 다음**: S7~S10(원문주석·KAM·정정공시·report/event — S6처럼 비용효익 판단) 또는 **S11 종료게이트**. **보류**: 전체 corpus persist는 Phase1 마감 시 `renormalize_all --force` 1회(현재 ~30%는 _align제거·alias보강 미반영 stale, 코드는 정확).

- **✅ member-sign 수정 검증 완료** (2026-06-15, `_P1_MEMBERSIGN_VERIFY_PROMPT.md`). audit 313 도메인에서 **member합≈-grand 시그니처 334→0**(전수 스캔·locked-skipped=0), pytest 203/1xfail, 백테스트 recall 5/6, 00131054/2023 이익잉여금 -5.51e9 — **4기준 전부 충족**. STATUS: DONE_WITH_CONCERNS.
  - **보류1(사용자 지시 — 기록만)**: 전체 corpus persist 미완. `b490i6d9g`가 [1050]/~4777 company-year에서 중단(완료줄 없음). audit 313만 fresh, 나머지 ~3,700 stale member-sign. `is_fresh()`가 부호 아닌 테이블 존재만 보므로 `--force` 없는 재개로는 안 고쳐짐 → 전체 `renormalize_all --force` 재실행 필요(미적용 보류).
  - **보류2 → 재판정: P1결함 아님(원공시 모순)**. `00141477/2023 연결대상범위의 변동`은 raw 대조 결과 **원공시 자체 부호 모순**(grand 연결재무제표=+2,126,881,891 vs 지배−12,867,283,357+비지배+10,740,401,465=−2,126,881,892). 정규화는 raw 4행을 100% 충실 재현(부호 안 건드림). `_align_member_signs_to_bare`가 안 발동한 게 **옳음** — 발동시켜 member를 뒤집으면 원공시 모순을 조작 정렬하는 셈. ⇒ `_amount_equal` 허용오차 완화는 오답. 도구가 가로항등(grand=지배+비지배) 모순을 anomaly로 노출할지는 별개 관찰(`sce_balance`는 세로검산만). non-audit new-schema 1046 전수 중 **진짜 정규화 결함 0**. 구스키마 107건은 `--force` persist로 재생성하면 해소(코드결함 아님). **메모리 `member-sign-residual-tolerance` 참조.**
- **⏭ 컴팩트 후 이것부터: 핸드오프 `data/backtest/_HANDOFF_S4_CLOSE.md`** — 닫힌 것/할 것/검증 baseline/다음 진입점 정리. 다음 진입점: S5(절대수준 신호) 또는 위 보류1·2 재개.

- **✅ Phase1 S4 수정 대량 완주** (2026-06-14). 발견 P1 높음결함 **11/13 FIXED**(pytest 203·백테스트 5/6 무회귀). 원장 `_P1_DEFECT_LEDGER.md` 수정후 표.
  - **수정 완료**: 영업이익=매출(quirk)·자본금 소계점유(Fix A+label_priority+분해탐지, 27+사)·금융업 BS(canonical 신설, -52조→+0.08조)·
    발행사채/만기보유/투자부동산(label_priority 일반규칙, 110+ 회사연도 부수교정)·dump÷1e6 착시제거·보험 canonical swap.
  - **신규 메커니즘**: config `label_priority_ids`(모호 id는 라벨 채택, 충돌행만 작동)·`_enforce_capital_decomposition`(자본금≈보통주+주발초 분해, 자본잠식/우선주 무영향)·company_quirks 실가동.
  - **의도적 보류 2**: 01406618(idiosyncratic 단일사, 올바른 매핑 모호)·00298687(member-sign 334건 systematic 트랙 `_P1_MEMBER_SIGN_FIX_PROMPT.md`).
  - **자가 적대 감사(40-F) 완료**: label_priority에 **교차표 누수 버그 발견·수정**(CF id가 SCE canonical로 새던 것 → statement 가드, mapper.py). Fix A flip 112표본 0건·피팅 전수 1사·역검증 무회귀·decomposition 무결.
  - **클린 클로즈(40-G)**: **클린 백테스트 실측 recall 5/6**(전 수정 무회귀 확정)·pytest 203·2케이스 재현(00545716·00428729). corpus persist 진행중(저장 duckdb refresh, async). S4는 `COVERAGE_REMEDIATION.md`에 **[~]부분**으로 정직 기록.
  - **⏭ 다음 진입점**: S4 잔여(member-sign 334건 트랙 `_P1_MEMBER_SIGN_FIX_PROMPT.md`·01406618·IFRS16 alias·관계기업 16사) 또는 **S5(절대수준 이상신호: DIO·부채비율·이자보상배율)**. 그 뒤 S6~S10(수집 확장)·S11(종료게이트). Phase1 종료는 아직 멂.

- **(이전) Phase1 S4 착수**: 그룹3 완료 시점 기록.
  - **✅ 그룹3 00545716 영업이익=매출 수정·검증 완료**: ripple 단일사 확정 → company_quirks.yaml override 2개(영업수익→매출+영업이익 복원, 2021·2022).
    매출 2.42조 생성·영업이익 0.245조 복원·live→FIXED·pytest 71·백테스트 무관. **quirk 메커니즘 첫 실전 가동(이전엔 빈 파일이라 미수정).**
  - **그룹1 자본금 — 변종1 완료, 변종2 잔존**:
    - 변종1(납입자본-라벨 27+사) **완료·검증**: ①Fix A(dedup 비충돌우선, pipeline.py) ②매퍼 `label_priority_ids:[ifrs-full_IssuedCapital]`(config+CanonicalAccount+mapper) → 납입자본→납입자본 canonical. 충돌 116행만 작용, 정상 8899행 무영향. pytest 71·**백테스트 분식 recall 5/6 무회귀**.
    - 변종2(자본금-라벨 소계위장 8사) **잔존**(task#2): label까지 자본금 위장이라 값 탐지만 가능. ★자본잠식사는 자본금>자본총계 정상이라 단순 가드 금지 → 정밀 분해탐지('자본금≈보통주자본금+주식발행초과금') 별도 라운드.
    - duckdb 재persist는 전체 그룹 후 일괄.
  - **남은 수정**: 그룹2 금융업BS(task#3)·그룹4 id_label_conflict 4종(task#4)·그룹5 SCE부호(task#5)·사소(task#6 dump÷1e6·task#7 표시명묶음).
  - duckdb 재persist는 그룹 전체 후 corpus 재정규화 1회로 일괄.
- **다각도 분석(이전)**: 공식 S11 종료게이트 기준 S4~S11 미완(8/12), 원장 `_P1_DEFECT_LEDGER.md` 36행·높음 11 live·근본원인 4종.
  - **S4 baseline 확정**: 원장 `data/backtest/_P1_DEFECT_LEDGER.md`(36행), live검사 `_p1_ledger_livecheck.py`(높음 13중 **LIVE=11**),
    BS 미매핑율 38.3%(감사 48%서 하락). 그룹1 자본금leaf우선·그룹2 금융업BS·그룹3 영업이익=매출·그룹4 id_label_conflict(quirk).
  - **수정 대상 live 결함**: 00545716 영업이익10배=매출 / 00428729·01573284 자본금>자본총계 / 00176914 BS항등식-52조 /
    00148504 발행사채→주식발행 / 00264945 만기보유←FVPL / 01089378 투자부동산유령 / 01406618 CF가짜exact.

- **✅ 내 홀리스틱 LLM vs gpt-5.4 비교 완료** (2026-06-14) — 산출 `data/backtest/_LLM_COMPARE_RESULTS.md`,
  gpt findings `_llm_compare/<corp>_gpt.md`(10), 스크립트 `_run_gpt_compare.py`. 고위험 10개사(known분식6+P2후보4)에
  gpt-5.4(run_llm_holistic) 같은 dump+9렌즈 실행 후 내 공장(chunk_N.md)과 대조.
  - **결론: gpt-5.4 UI 온보딩 채택 권장.** 분식신호 포착 대등이상 — 연결범위(00118345 비지배귀속이상)·재고과대(00409681 재고3배)
    2건은 B가 A보다 직접 포착(A 놓침, duckdb 검증), 매출재작성(00159616) 1건 A우위, 2 tie.
  - **B 약점=거짓 P1결함**: dump 원/백만 혼재 표시를 스케일 결함으로 반복 오독(검증4건 전부 정상 매핑). **보정 권장: dump 렌더러
    sj_div 무관 일괄 ÷1e6 통일** → 거짓 스케일경보 원천 제거. (또는 9렌즈 §G에 원-단위 표시 주의 1줄.)
  - **다음 후보**(선택): 위 dump 렌더러 ÷1e6 보정으로 gpt-5.4 거짓 P1 제거 → 온보딩 LLM 품질 확정.

- **유형A 근본해결 구현 완료 — 회귀 통과** (2026-06-14, 위 비교의 선행 완료물).
  - **구현 완료물**(3 단계로 유형A 의미 오매핑 처리):
    1. **표 호환성 심판** `src/normalize/pipeline.py:_arbitrate_conflicts` — 충돌 시 sj_div 맞는 canonical 채택(cross-statement 자동교정).
    2. **company_quirks** `config/company_quirks.yaml`+`config.py:load_company_quirks`+`pipeline.py:_apply_company_quirks` —
       within-category 진짜오매핑(mechanical 분리 불가 측정확정)을 회사별 데이터로 교정. corp_code=데이터키(하드코딩 아님).
    3. **동의어 canonical dedup** — config 중복(FVPL↔당기손익공정가치 등) 15쌍 통합(canonical 2028→2013). 충돌 719→704 소멸.
  - **온보딩 QA 게이트** `src/normalize/onboarding_gate.py:run_gate(corp,year)` — 신규회사 정규화 후 분석 전 G1~G6(기계검사·충돌·
    산술검산·F1·LLM홀리스틱 dump) 부품화 검문. `_quirk_promote_scan.py`(3회+ 반복 quirk 전사 승격). **UI**: `dashboard/onboarding.py`
    (입력→게이트→이탈 표시→quirk 등록→재검사→Phase1/2 진입). **G6 LLM 통독=gpt-5.4 추론모델**
    (OpenAIModel+reasoning_effort, Phase2 perspectives.py 정합 — Gemini Flash 아님). 실호출 성공 확인.
  - **회귀 전부 통과**(직접 재현): 백테스트 recall 5/6·IS/CF 11=11 악화0·F1 dangling 0·pytest 203 passed·corpus 재정규화 error0·세분화 보존·CF 무회귀.
  - **남은 운영 후속**(별개): 동의어 dedup 벌크(635 synonym 큐는 게이트 주도 점진)·within 진짜오매핑(9 mistag)은 quirk/게이트로 흡수·LLM홀리스틱 실호출은 API키 환경에서.
  - 설계: `dev/active/synonym-dedup-onboarding-gate/`. 측정 근거(범주·lexical·영문id 3종 실패→case불가피)=`_idlabel_precision_probe.py`. 폐기 설계 `id-label-conflict-category-arbiter`(범주 arbiter는 cross만 잡아 채택 안 함).
  - **전수 홀리스틱 재검(선행 완료)**: 34/34 묶음 `_HOLISTIC_SYNTHESIS.md`. 글로벌 F1(PASS)·IS/CF=`_GLOBAL_CHECKS_RESULTS.md`. 유형B/C/D/E·member부호 별개 트랙.
  - **글로벌 검사 2종 완료(영구 회귀 스크립트)** — `_GLOBAL_CHECKS_RESULTS.md`:
    - **F1 신호 dangling: PASS** (`_f1_signal_dangling.py`). 신호엔진 참조 56 canonical 전부 살아있음.
    - **IS/CF 산술검산: 302/313 통과** (`_is_cf_arithmetic.py`). 11 잔차=계속/중단영업 소계 미매핑 P1후보
      (config에 `계속영업손익`·`중단영업손익` alias 보강 시 0 수렴). 부호규약 회사별 상이를 magnitude 흡수.
  - **wave 1~2 주요 P1 패턴**: ①영문코드↔한글 의미 오매핑(사채발행→주식발행 1.4조·유동차입금→비유동)
    ②미매핑 대형계정 기타로(금융업자산 52조·유형자산 1.3조) ③금융기관 주석 0건. 상세 `_HOLISTIC_SYNTHESIS.md`.
  - **이유**: 라운드1~12가 기계 flag만 역추적하고 감사관 통독을 사실상 안 한 사각(사용자 지적)을 메움.
    member부호 수정·라운드13은 별개 트랙. 방법론 전환 기록 `docs/agent/P1_AUDIT_HARNESS.md §5`.

- **라운드12 구조 규칙 수정 완료 (2026-06-13, `_P1_ROUND12_FIX_PROMPT.md` 실행)**:
  SCE 소계/스톡-as-leaf 재발을 라벨 신규 등록 없이 구조 규칙으로 처리했다. 부모소계 retag는
  일반 집계 라벨 패턴과 detail parent 신호를 보되, bare subset 합 또는 기존 벡터 매칭 후보를
  모두 제외한 trial frame이 strict `기초+Σleaf=기말` 검산을 통과할 때만 subtotal로 확정한다.
  스톡 retag는 begin/restated_begin의 현재 공시 component 벡터와 후보 현재 벡터가 일치하면
  `restated_begin`으로 격리해 전기 값 NaN/부분 공시 사각을 줄였다. A/B 충돌은 처리 순서상
  스톡 벡터 일치가 우선한다.
  - **검증**: R12 targeted RED 4 failed·2 passed → GREEN. `r12 or structural or r11 or r10`
    10 passed, ruff 대상 파일 통과. 최종 102사 합집합(round1~12+known) force 재정규화
    `처리 399 | renorm=327 skip=0 empty=72 error=0 | 행 95,675`. round12 핵심
    00382199/2023 `자기주식 거래 합계`와 00526951/2020 `회계정책변경에 따른 증가(감소)` SCE검산
    OK 전환, 소실 0·전기소실 0. known+round1~11은 기존 허용 잔여만 유지. 전체 pytest
    199 passed·1 xfailed, 백테스트 recall 5/6 유지.
  - **직접 증거**: 00382199/2023 `자기주식 거래 합계` rows are `change_role='subtotal'`,
    `sce_balance` diff=0. 00526951/2020 CFS `회계정책변경에 따른 증가(감소)` 현재 공시 rows are
    `change_role='restated_begin'`, `sce_balance` diff=0. 00101752 5개년 잔여는
    `자본 증가(감소) 합계`가 이미 subtotal로 제외된 뒤에도 남는 소액 잔차라 R12 구조 A 미적용
    잔여로 보지 않는다.
  - **과수축 감사**: known+round1~12의 387 회사연도 재계산에서 초기 leaf였으나 구조 규칙 후
    subtotal/restated_begin으로 격리된 행은 327개(`subtotal` 154, `restated_begin` 173).
    상위 라벨은 `소계` 57, `회계정책변경에 따른 증가(감소)` 33, `수정 후 금액` 28,
    `자기주식 거래 합계` 16 등이다. 과수축 가드는 후보 제외 후 strict 검산이 깨지는 합성 케이스를
    leaf로 유지하는 테스트로 고정했다.
  - **남은 잔여**: round12에는 01147487/2025 `FAIL(-3,083)`(자기주식취득 부호 별도 축),
    00351579/2020~2021, 00148832/2023, 00101752 5개년, 00130772/2023~2024 등 11건이 남는다.
    이 중 00351579/00148832는 원공시모순 동반, 00101752는 subtotal 제외 후 소액 잔차, 01147487은
    프롬프트 부록의 별도 분류 대상이다.
  - **다음**: 라운드13은 구조 규칙 적용 후 20사 재검(seed=13)으로 신규 라벨 변주 0 여부를 확인한다.
- **과거 수정 과수축 독립 감사 (2026-06-13, 사용자 "뭉갠 것 아니냐" 의심)**: 우리 검산(grand-total)으로
  과거 OK를 확인하면 자기참조라, 독립 오라클(`_sce_overcollapse_audit.py`)로 전수 재검. **오라클을
  3회 만들며 2회 스스로 false-positive 잡아냄(§9 자기도구 의심)**: ①합계컬럼(지배기업소유주지분)을
  leaf로 오집계 ②"grand vs member 부호 다름"을 결함으로 오인(정상). 정밀(변동행 member합 vs grand)에서
  **결정적 발견**: 313 회사연도 중 **334건이 member합≈-grand**(연차배당·신종자본증권 등 차감변동) =
  **-abs 부호 정규화가 grand('-') 셀만 뒤집고 member 구성요소 셀은 raw 부호로 방치**. **판정: 뭉개기·
  마스킹 무혐의**(grand 검산·recall 5/6 유효), **얕은 수정 유죄**(라운드1~12 내내 검사하는 축만 고치고
  안 보는 member 셀 방치 — 공통 사각, Phase2가 member 읽으면 배당 +로 보임). 증거: 00131054/2023
  현금배당금 grand=-5,510·이익잉여금=+5,510. **다음:
  [data/backtest/_P1_MEMBER_SIGN_FIX_PROMPT.md](../../data/backtest/_P1_MEMBER_SIGN_FIX_PROMPT.md) 실행
  (부호 전 셀 일관 적용, 334→0, member합==grand 불변식 영구 편입) → 그 후 라운드12 구조규칙 수정 재개.**
- **라운드12(20사 재검) 감사: 수렴 미달 + 전략 전환 결정 (2026-06-13)**: 라운드11 수정 실재
  확인·무회귀(타깃 3사 OK). 라운드12(seed=12, 20사 77 회사연도, **691조 초대형 금융 포함**)
  재검 — 기계 floor가 64개 깨끗·13개 flag, 2분할 감사 + 게이트 PASS 77×6. **신규 결함 재발
  (사다리 20사 단계 미통과)**: ①00526951/2020 `회계정책변경에 따른 증가(감소)` 스톡 행이
  당기 벡터만 begin과 일치(전기 NaN)라 라운드4 벡터동일성 사각 → leaf 이중계상 75,412(직접
  재현) ②00382199/2023 `자기주식 거래 합계`(-486,028)가 자식(취득-485,947+소각-81)과 함께 leaf
  이중계상(직접 재현 — **B조가 "원공시 0건"으로 오분류한 것을 설계자 §9 재현이 잡음**). **핵심
  통찰: 결함 TYPE은 소계/스톡-as-leaf 2종으로 수렴했으나 한글 라벨이 회사마다 무한 변주(소계·
  합계·자기주식 거래 합계·회계정책변경…) → 라벨 등록은 두더지잡기.** **전략 전환: 라벨 등록
  중단, 구조 규칙(bare=형제합→subtotal / bare 벡터=begin벡터(공시축만)→restated)으로 일반화.**
  **다음: [data/backtest/_P1_ROUND12_FIX_PROMPT.md](../../data/backtest/_P1_ROUND12_FIX_PROMPT.md)
  실행(구조 규칙 A/B) → 20사 재검(seed=13)에서 라벨 변주가 또 나와도 신규 0이면 그게 진짜 수렴
  신호 → 50사 → 100사.** 00101752 5/6년 소액 FAIL은 구조 규칙 적용 후 원공시 잔존 여부 재확인 대상.
  직접 증거 조건을 실제 검증 기록과 맞췄다. `00153861/2020`은 derived 유령 leaf 제거 후 SCE 검산
  OK이며, 직접 `sce_balance` diff가 `-1` 같은 원 단위 잔차로 남아도 tolerance 이내이면 성공으로
  본다. 라운드11 구현·검증 결과 자체는 변경하지 않았다.
- **라운드11 수정 완료 (2026-06-13, `_P1_ROUND11_FIX_PROMPT.md` 실행)**: R11-a/R11-b/R11-c
  수정·검증 완료. `_retag_parent_subtotal_vectors`는 `(change_label, account_id)` 통합 그룹 대신
  `source_order` 인접 블록 단위로 부모소계 매칭을 수행하고, 직전 subtotal boundary 이후 여러
  자식 변동행 전체합과 일치하는 `소계`도 subtotal로 재태깅한다. `_add_derived_bare_totals`는
  `detail_path`가 prefix-nested 관계인 부모/자식 member가 함께 있을 때 derived 합계 계산에서
  child detail을 제외해 부모+자식 이중계상을 막는다. `총포괄손익 소계` alias도 등록해 id-label
  모순 케이스가 `총포괄손익` subtotal로 들어간다.
  - **검증**: targeted RED 3 failed → GREEN 3 passed. 최종 81사 합집합(known+round1~11)
    force 재정규화 `처리 318 | renorm=255 skip=0 empty=63 error=0 | 행 76,807`. round11은
    00631518/2020~2022, 00545716/2021~2022, 00153861/2020~2021 SCE검산 OK. 잔존은
    prompt 허용 범위인 00631518/2025 `FAIL(-31)`, 00120216/2025 `FAIL(-1)`, 00153861/2022
    `FAIL(3,555)`. known+round1~10 무회귀, 백테스트 recall 5/6 유지, 전체 pytest
    193 passed·1 xfailed, ruff 대상 파일 통과.
  - **직접 DB 증거**: 00631518/2021 `change_label='소계'` rows are all `change_role='subtotal'`
    and SCE diff=0. 00153861/2020 is SCE OK after derived nested child exclusion; direct
    `sce_balance` diff is `-1` within tolerance, so prompt의 `diff=0` 기대와는 원 단위 잔차 차이가
    있다.
  - **다음**: 수렴 카운터 리셋 후 라운드12는 20사 재검(seed=12, 신규 0 확인)으로 진행.
- **라운드11(20사) 감사: 수렴 깨짐 — 신규 결함 2종 (2026-06-13)**: 라운드10 수정 게이트 통과.
  **수렴 사다리 20사 단계**(seed=11, 20사 74 회사연도, 178조·105조 포함) — 기계 floor가 64개
  회사연도를 깨끗 판정, **10개만 flag**(통독량=flag수 설계 입증) → 감사 2분할(A/B조) + 게이트
  PASS 74×6. **신규 결함 2종 발견(추이 …→0→0→2) — 라운드9·10 연속 0은 표본 부족이었음이 입증
  (사용자 §9 의심이 옳았다)**: **R11-a** 동명 '소계' 다중블록이 `(change_label, account_id)`
  그룹화로 통합돼 leaf 잔존(00631518 105조 3개년 4.17조/3.62조 — 직접 재현, 세토 동명+blank id
  친척) · **R11-b** `_add_derived_bare_totals`가 부모member+중첩자식member 동시 합산해 유령 leaf
  (00153861 2020/2021 — 자본 내 대체 net 0이 깨짐, 직접 재현 diff=0) · R11-c id-label 모순
  (00545716 유상증자 id에 '총포괄손익 소계' label — R11-a 마커로 동시 해결). **수렴 카운터
  리셋.** **다음:
  [data/backtest/_P1_ROUND11_FIX_PROMPT.md](../../data/backtest/_P1_ROUND11_FIX_PROMPT.md) 실행
  → 갱신 사다리: 20사 재검(seed=12, 0 확인)→50사→100사, 각 단계 0이어야 진행, 100사까지 0이면
  수렴 선언.**
- **라운드10 수정 완료 (2026-06-13, `_P1_ROUND10_FIX_PROMPT.md` 실행)**: T1/T2 완료, T3는
  선택 항목으로 축소. `총포괄이익 소계`를 `총포괄손익` alias로 등록하고
  `parent_subtotal_label_markers`에 `소계`를 추가했다. SCE 부모소계 재태깅은 기존 수치 벡터
  정합 가드를 유지하되 자식 후보에 기존 subtotal도 허용해 `총포괄손익 = 당기순이익 + 기타포괄손익`
  구조를 처리한다. F-1 원공시모순 카운터는 차감 canonical의 bare/component 부호 비대칭을
  절대값 비교로 흡수하고, unmatched 소계 컬럼은 sibling 부분합과 일치할 때 제외한다.
  - **검증**: targeted RED 4 failed → GREEN 4 passed. 최종 61사 합집합(known+round1~10)
    force 재정규화 `처리 244 | renorm=199 skip=0 empty=45 error=0 | 행 59,242`.
    round10에서 00356361/2020~2022 SCE검산 OK로 전환, 00264547/2025·00537221/2025·
    00249502/2020·00571298/2023·00401731/2021~2022의 원공시모순은 진단값으로 잔존.
    known 및 round1~6 PASS, round7~9는 기존 허용 잔여만 유지. 백테스트 recall 5/6 유지.
    전체 pytest 190 passed·1 xfailed, ruff 대상 파일 통과.
  - **직접 DB 증거**: 00356361/2021 `총포괄이익 소계` rows are
    `change_canonical='총포괄손익'`, `change_role='subtotal'` for bare and component cells.
  - **축소**: T3 bare 기초자본 vs 전기 기말 교차검사는 §6 성공 기준에 없는 선택 항목이라
    새 출력 필드·게이트를 만들지 않고 보류했다.
  - **다음**: 라운드11은 20사(seed=11)로 수렴 사다리 다음 단계 진행.
- **라운드10(10사 배증) 감사 + 수렴 기준 상향 (2026-06-13)**: 라운드9 수정 게이트 통과. 샘플러
  n>5 라운드로빈 버그 수정 후 **10사 42 회사연도**(101조·68.6조 대형, seed=10) — 감사 2분할
  (A/B조) + 게이트 PASS 42×6. **파이프라인 신규 결함 0(라운드9·10 연속, 추이
  5→5→2→1→2→3→2→1→0→0)**, 소실·전기소실·부호반전 전수 0. 잔존: 소계 변형 '총포괄이익 소계'
  (00356361 3개년, 직접 재현 — '소계' 접미 마커감) + 하니스 F-1 오탐 2메커니즘(오탐 39건) +
  **진짜 원공시 모순 5건**(기초 셀에 기말값 오태깅 2.4조 등 — 정직 노출, Phase2 확인질문).
  **⚠ 수렴 선언 철회(사용자 §9 지시)**: 라운드9·10 연속 0은 "수렴 가능성"일 뿐. **수렴 사다리
  = 10사(완료)→20사→50사→100사, 전 단계 통과해야만 수렴**. **다음:
  [data/backtest/_P1_ROUND10_FIX_PROMPT.md](../../data/backtest/_P1_ROUND10_FIX_PROMPT.md) 실행
  → 라운드11=20사(seed=11)·라운드12=50사·라운드13=100사 순. 각 라운드는 직전 수정 적용 후
  새 표본. 100사까지 신규 0이면 그때 수렴 선언 + 잔여 전수 스캔 전환.** 50·100사 라운드는
  기계 floor가 전수 판정하고 LLM은 flag(검산 FAIL·소실>0·원공시모순·사유미상) 회사연도만
  정밀 통독(p1-auditor 다분할) — 통독량은 회사 수가 아니라 flag 수에 비례.
  SCE 변동행 매칭에서만 `당기` 접두를 제거해 `당기총포괄손익`을 `총포괄손익` subtotal로 분류하고,
  본문 `map_row`의 `당기~` 매핑은 그대로 유지했다. CFS/OFS 같은 label이 서로 다른 account_id로
  공시된 경우 mapping은 바꾸지 않고 양쪽 `mapping_status='id_label_conflict'`만 표시한다.
  하니스는 SCE raw bare 합계행과 구성요소 컬럼합 불일치를 `원공시모순=N`으로 표기한다.
  - **검증**: targeted RED 3 failed → GREEN 3 passed. 52사 합집합(known+round1~9) force
    재정규화 완료(`처리 206 | renorm=165 skip=0 empty=41 error=0 | 행 49,767`). 본문
    `label like '당기%'` canonical 분포는 재정규화 전후 동일(`diff={}`). round9는
    00927558/2021~2023 SCE검산 OK, 00927558/2024는 원공시모순 2와 함께 `FAIL(1,375)` 잔존,
    00428729/2020~2021은 원공시모순 1과 함께 원천 결함 FAIL 잔존. known 및 round1~6 PASS,
    round7·round8은 기존 허용 잔여만 유지. 전체 pytest 186 passed·1 xfailed, 백테스트 recall
    5/6 유지.
  - **직접 DB 증거**: 00927558/2021 `당기총포괄손익` rows are
    `change_canonical='총포괄손익'`, `change_role='subtotal'`.
  - **다음**: 라운드10은 10사 배증(seed=10, 배증 규칙 발동). 라운드10도 신규 0이면 수렴 선언과
    잔여 기계 floor 전수 스캔 전환을 검토한다.
- **라운드7 수정 완료 (2026-06-12, `_P1_ROUND7_FIX_PROMPT.md` 실행)**: N2-d·N2-e 수정·검증.
  차감 `-abs`는 `component_std='-'` bare 셀과 도출 bare 합계에만 적용하고, 구성요소 셀은 원부호를
  보존한다. 도출 bare 합계도 구성요소 부호가 양·음 혼재하면 `-abs`를 적용하지 않아 자본 내 대체
  거래의 순액 방향을 보존한다. `sce_deduction_changes`에는 `비지배지분에 대한 배당금`을 config
  데이터로 등록했다.
  - **검증**: N2-d/N2-e TDD RED 3 failed → N2-d 후 1 failed·2 passed → GREEN 3 passed.
    round7은 00469799/2025 SCE검산이 -68,878에서 **-2,841**로 축소, 00147295/2023 OK,
    00147295/2024 **FAIL(-1)**은 백만원 granularity 잔존으로 허용. known 및 round1~6은 기존
    미제공 표기 외 모두 기계검사 PASS, 소실 0·전기소실 0. 전체 pytest 178 passed·1 xfailed,
    백테스트 recall 5/6 유지.
  - **직접 DB 증거**: 00469799/2025 `무상감자` `자본잉여금` component amount
    `+33,018,628,500`, 00147295/2023 `비지배지분에 대한 배당금` bare amount
    `-1,293,000,000`.
  - **남은 데이터 특성**: 00469799/2025 잔여 -2,841은 원공시 NCI 열 미정합, 00147295/2024
    -1은 공시 단위 granularity로 판단. 다음은 라운드8 5사 유지(신규 2종 — 배증 보류 지속).
- **수집 부재 manifest + 하니스 미제공 표기 구현 완료 (2026-06-12,
  `_P1_COLLECT_GAP_FIX_PROMPT.md` 실행)**: `collection_summary.json`에
  `absence: {fs, xbrl_zip}`를 추가하고, 하니스가 DB/주석 부재를 `FAIL`과 `미제공(...)`으로
  구분하도록 변경. `fs`는 `ok|no_report|dart_no_data`, `xbrl_zip`은
  `ok|no_report|dart_no_xbrl`로 기록한다. 수집 spike는 XBRL zip 실패 경로에서도 summary를
  남기며, 기존 summary 스키마는 필드 추가만 수행.
  - **하니스 동작**: `_p1_review_all.py`는 DB 없음이 summary상 `no_report`/`dart_no_data`이면
    `미제공(...)`으로 표기하고 사유미상만 `FAIL(DB없음·사유미상)`으로 남긴다. 주석 테이블 부재도
    summary상 `no_report`/`dart_no_xbrl`이면 `OK(주석미제공(...))` 및 `주석행=미제공(...)`으로
    표기한다. `_p1_company_review.py`도 동일 기준으로 단일 dump의 조기 종료/§0 완결성을 맞춘다.
  - **백필**: `data/backtest/_backfill_absence.py`를 추가해 기존 `data/companies` 5,126 회사연도에
    absence를 기록. 현재 디스크 기준 출력은 `fs_absence=353(no_report=166,dart_no_data=187)`,
    `xbrl_absence=512(no_report=239,dart_no_xbrl=273)`로, 프롬프트 기준선 `본문 347·zip 163`과
    불일치한다. 이는 전수 notes 수집 로그 전체 실패(512)를 반영한 결과로 보이며, 기준선 정의가
    다르므로 완료 상태는 `DONE_WITH_CONCERNS`로 취급.
  - **검증**: RED 4 failed+1 passed → GREEN 5 passed. round1~6 및 known 배치 모두
    `기계검사 바닥 전수 PASS`, 사유미상 FAIL 0. 기존 갭은 `미제공(dart_no_data)`,
    `미제공(no_report)`, `OK(주석미제공(dart_no_xbrl))`로 전환. 전체 pytest
    175 passed·1 xfailed, ruff check/format 대상 파일 통과.
- **라운드6 수정 리뷰게이트 통과 + 수집 레이어 점검 완료 (2026-06-12)**: 라운드6 수정(N1-f·
  N1-g·N4-c) 게이트 통과 — round6 검산 OK·전기소실 컬럼 작동·전환사채 prior 6,395,852,761
  보존·stock_balance 재지정·하드코딩 0. **수집 점검 결론: 수집 버그 0건** — 전수 측정(본문
  부재 347건: 2020:121→2024:11 점감 / zip(주석) 부재 163건) 후 DART API 직접 대조로 3분류
  확정: ①미제출(사업보고서 없음 — 신규상장 전, 01584183 유형) ②본문 미제공(보고서 있으나
  finstate_all status 013 — 금융업 구 양식 2020~22, 00117267·00158909 실증) ③zip 미제공
  (finstate_xml 013/014 — 00127158/2023 재수집 시도로 실증, no_zip). 즉 갭 전체가 DART측
  부재 = 재수집 불가/불필요. 남은 관측 공백(부재 사유 미기록 → 미제공 vs 수집누락 구분 불가)은
  [data/backtest/_P1_COLLECT_GAP_FIX_PROMPT.md](../../data/backtest/_P1_COLLECT_GAP_FIX_PROMPT.md)
  발행(absence manifest + 하니스 '미제공' 구분 표기 + backfill). **다음: 수집 프롬프트 실행
  (선택) → 라운드7 5사(seed=7) 계속.**
- **라운드6 수정 완료 (2026-06-12, `_P1_ROUND6_FIX_PROMPT.md` 실행)**: N1-f·N1-g·N4-c와
  하니스 전기 대조 수정 완료. TDD RED(3 failed·1 passed) → GREEN(4 passed), 전체 pytest
  171 passed·1 xfailed, ruff check/format 대상 파일 통과. 36사 합집합(known+round1~6), 143
  회사연도 force 재정규화 완료(renorm=117·empty=26·error=0).
  - **N1-f restated delta/stock 분리**: `수정 후 금액`·`조정후금액` 등 잔액형은
    `stock_balance`로 전체 label group 재지정하고 leaf 합산에서 제외. `재작성효과`처럼 begin
    벡터와 다른 restated delta label은 잔액 대체가 아니라 movement에 더한다.
  - **N1-g bare total 부재 보정**: 구성요소 열만 있고 `component_std='-'` bare 합계행이 없는
    SCE 변동은 component sum으로 `component_role=derived_total`, `detail_path=[derived:component_sum]`
    bare row를 생성해 검산이 볼 수 있게 했다.
  - **N4-c 전기/전전기 비교치 소실 방지**: statement/canonical dedup 키와 값 차이 판정에
    `prior_amount`·`prior2_amount`를 포함하고, pandas `groupby().first()`의 NaN skip 부작용을
    피하도록 물리 첫 행 기준으로 대표값을 잡았다. 당기 NaN이라도 전기/전전기가 다른 동명 blank 행은
    생존하고, 완전 동일 중복은 계속 dedup된다.
  - **하니스 §D 보강**: raw `frmtrm_amount`를 normalized 본문+SCE `prior_amount`와 직접 대조해
    `전기소실`을 집계하고 `_p1_review_all.py` 표/파서에도 노출.
  - **검증**: known 19 PASS. round1~6은 기존 원천 DB 없음·주석 테이블 없음 갭 외 모든 runnable
    회사연도 소실 0·전기소실 0·SCE검산 OK. Round6 핵심 직접 SQL:
    00127158/2023 `전환사채 prior_amount=6,395,852,761` 생존, 00127158/2020 `수정 후 금액`
    `change_role=('stock_balance')`. 백테스트 recall 5/6 유지(세토피아 변동미미).
  - **남은 갭(기존/원천 문제)**: round1 00117267/2020~2022, round2 00688996/2020~2022·
    01675421/2020~2022, round3 00126256/2020~2022·00124106/2020~2022, round4
    00131850/2020~2022, round5 00158909/2020~2022는 DB 없음. round2 00121686/2025,
    round5 00238782/2021, round6 00127158/2023은 `note_facts_classified` 없음. 라운드7은
    5사 유지 권고.
- **라운드5 수정 리뷰게이트 통과 + 라운드6 감사 완료 (2026-06-12)**: 라운드5 수정(N1-d·N1-e)
  게이트 통과 — round5 검산 OK·stock_balance 재지정 DB 확인·src 라벨 하드코딩 0(config만).
  **라운드6**(seed=6: 금융 83조·별도전용·blank고비중 6년·다년대형·단년소형, 23 회사연도) —
  p1-auditor 게이트 PASS[round6], 핵심 주장 직접 재현. **신규 3종**(추이 5→5→2→1→2→3, 당기
  값 소실 0): **N1-f** 조정후개시 '수정 후 금액' leaf 혼입 + restated 델타형(+2,572)을 잔액
  매칭이 대체 처리해 어긋남(00127158/2020, 이중 결함) · **N1-g** 합계열 미공시 변동행(구성요소
  열에만 -514M)을 bare 기반 검산이 못 봄(00127158/2023) · **N4-c** 당기 NaN blank-id 동명행
  dedup으로 **전기/전전기 비교치 소실**(전환사채 전기 6,395,852,761 등 3건 — §D가 당기만
  대조해 하니스도 사각). 부수: 00127158/2023 수집 누락(zip 자체 부재, 재수집 필요)·01584183
  비금융 원천 부재(갭 패턴이 금융업이 아니라 "해당 연도 XBRL 미공시"일 가능성)·원공시 태깅
  오류 9행(N5 자료 누적). **다음:
  [data/backtest/_P1_ROUND6_FIX_PROMPT.md](../../data/backtest/_P1_ROUND6_FIX_PROMPT.md) 실행
  (N1-f·N1-g·N4-c + 하니스 §D 전기 대조 추가) → 라운드7 5사 유지**(신규 3종 — 배증 보류.
  수집 갭 과제(금융 7사+비금융 1사+수집누락 1건)는 라운드 루프와 분리해 별도 회차 권고).
- **라운드5 수정 완료 (2026-06-11, `_P1_ROUND5_FIX_PROMPT.md` 실행)**: N1-d·N1-e 수정·검증. TDD(실패→GREEN).
  - **N1-e restated marker 보강**: `restated_begin_markers`를 정규화 키로 비교하는 기존 경로에
    `반영후자본` marker를 config 데이터로 추가해 `회계정책변경 효과반영후자본` 공백 변형을
    `restated_begin`으로 분류.
  - **N1-d stock_balance role**: SCE 추출 결과에 `source_order`를 보존하고, bare 합계열
    `component_std='-'` 중 config marker(`소계`, `잔액`) 라벨이 누적 스톡 잔액 또는
    `기말자본총계 - 공시 subtotal` 브릿지와 일치하면 신규 `stock_balance`로 재지정. leaf 합산과
    R3 잔여보정 양쪽에서 제외한다. src/에는 회사·연도·금액·라벨 조건 하드코딩 없음.
  - **재정규화**: round5·round1~4·known positive runnable 합집합 31사, 120 회사연도 `--force`
    재정규화 완료(renorm=97·empty=23·error=0).
  - **검증**: targeted RED 2 failed·2 passed(기존 stock 테스트 포함) → GREEN 4 passed /
    round5 00158909/2023~2025·00164362/2020 SCE검산 OK·소실 0(기존 수집갭 3건+주석갭 1건 외 OK) /
    known 기계검사 바닥 전수 PASS / round1~4 기존 수집·주석 갭 외 OK / 백테스트 recall 5/6 유지 /
    pytest 167 passed·1 xfailed / 00158909/2023 `소계` bare 직접 SQL 결과 `stock_balance`.
  - **다음**: 라운드6 5사 유지. 라운드6·7 연속 신규 0이면 10사 배증, 수렴 시 잔여 기계 floor 전수 전환.
- **라운드4 수정 리뷰게이트 통과 + 라운드5 감사 완료 (2026-06-11)**: 라운드4 수정(N1-c) 게이트
  통과 — round4 검산 OK·오류수정 행 restated_begin 재지정 확인·진짜 재작성(00413046) 무회귀·
  src/ 라벨 하드코딩 0. **라운드5**(seed=5: 금융 83.6조·별도전용·blank고비중·**은행 557조**·
  단년소형, 19 회사연도) — p1-auditor 게이트 PASS[round5], 핵심 수치 직접 재현. **신규 2종·값
  소실 0**(신규 추이 5→5→2→1→2, 전부 SCE 스톡 혼입 계열로 협소화): **N1-d** 잔액형 `소계`
  행(기초+소유주거래 반영 잔액)이 미등록 leaf로 Σleaf 혼입 — 은행 3개년 검산 FAIL 28~32조,
  begin과 벡터가 달라 N1-c로 못 잡음, subtotal 등록 시 R3 잔여보정이 역흡수하므로 stock 계열
  신규 role 필요. **N1-e** restated 마커 매칭이 공백 정규화 미적용 — 같은 표의 공백 변형 2행 중
  1행만 잡힘(직접 재현: '효과 반영후자본' restated_begin vs '효과반영후자본' leaf 24,889).
  부수: 수집 갭 금융 7사째·00238782/2021 주석만 부재(부분 갭 변형)·혼합형 BS(금융업자산
  분리표시) 관찰.
- **라운드4 수정 완료 (2026-06-11, `_P1_ROUND4_FIX_PROMPT.md` 실행)**: N1-c 수정·검증. TDD(실패→GREEN).
  - **N1-c 스톡 재태깅 변동의 벡터 동일성 판별**: SCE 추출 후처리에서 같은 `fs_div` 내
    `begin`/기존 `restated_begin` 그룹의 전체 component 벡터(`component_std`→`amount`·`prior_amount`)와
    완전 동일한 변동행 그룹을 `restated_begin`으로 재지정. 라벨·corp·연도·금액 하드코딩 없음.
    행은 보존하고 검산 leaf 합산에서만 제외한다. 부분 일치·벡터 불일치 correction concept은 leaf 유지.
  - **재정규화**: round4·round1~3·known positive runnable 합집합 26사, 101 회사연도 `--force`
    재정규화 완료(renorm=81·empty=20·error=0).
  - **검증**: targeted RED 1 failed·1 passed → GREEN 2 passed, N1/D5/R3-b 주변 6 passed.
    round4 00136776/2025 SCE검산 OK·소실 0(기존 수집갭 3건 외 OK) / known 기계검사 바닥 전수 PASS /
    round1 기존 수집갭 3건 외 OK / round2 기존 수집갭 6건+주석갭 1건 외 OK / round3 기존 수집갭
    6건 외 OK / 백테스트 recall 5/6 유지 / pytest 164 passed·1 xfailed.
  - **다음**: 라운드5 5사 유지. 라운드5 신규 0이면 라운드6부터 10사 배증 검토.
- **라운드3 수정 리뷰게이트 통과 + 라운드4 감사 완료 (2026-06-11)**: 라운드3 수정(R3-b·M1)을
  work-prompt-authoring 리뷰게이트로 검증 — round3 검산 OK(00557933)·M1 분리(지분법이익잉여금변동
  +32 별도)·테스트 약화 0(assert 변경은 N5 플래그 의도 반영)·하드코딩 0·4경로 무회귀. **라운드4**
  (seed=4: 금융 6.5조·별도전용·blank고비중·다년대형·blank39% 소형, 16 회사연도) — p1-auditor
  게이트 PASS[round4], **신규 1종·값 소실 0**(수렴 추세: 신규 유형 5→5→2→1): **N1-c** 스톡
  재태깅 변동(`오류수정에 따른 증가(감소)` concept에 수정후 기초 스톡 — component 벡터가 begin과
  당기·전기 전 셀 동일, 00136776/2025 검산 FAIL 29,636, 직접 재현 확인). 라벨 등록 불가(타사에선
  진짜 델타) → 벡터 동일성 구조 판별 필요. 그 외 병합 다발은 전수 동질(parent-child 재태깅,
  값 왜곡 0)·수집 갭 금융 6사째(00131850). **다음:
  [data/backtest/_P1_ROUND4_FIX_PROMPT.md](../../data/backtest/_P1_ROUND4_FIX_PROMPT.md) 실행
  (N1-c 단건, work-prompt-authoring 규약) → 라운드5 5사 유지, 라운드5 신규 0이면 라운드6부터
  10사 배증.**
- **라운드3 수정 완료 (2026-06-11, `_P1_ROUND3_FIX_PROMPT.md` 실행)**: R3-b·M1 수정·검증. TDD(실패→GREEN).
  - **R3-b 부분자식 소계 잔여 보정**: `sce_change_roles.subtotal_children`에 `기타포괄손익` 구성 leaf
    멤버십을 선언하고, `sce_balance`가 `소계 bare 값 - 공시된 구성 leaf 합` 잔여만 leaf 합산에 보정.
    자식 0개면 기존 R3 소계 채택과 동치, 자식 전부 공시면 잔여 0으로 D5 무회귀.
  - **M1 alias 오염 분리**: `지분법이익잉여금`을 `지분법기타포괄손익재분류가능` alias에서 제거하고
    전용 SCE leaf `지분법이익잉여금변동` alias로 이동. 동류 오염 스캔 결과 조치 대상 0건
    (별도 SCE leaf `기타포괄손익지분증권처분이익잉여금대체`는 이미 분리된 전용 canonical).
  - **재정규화**: round3·round1·round2·known positive runnable 합집합 21사, 85 회사연도 `--force`
    재정규화 완료(renorm=68·empty=17·error=0).
  - **검증**: targeted RED 2 failed → GREEN 2 passed / round3 00557933/2023 SCE검산 OK·소실 0
    (기존 수집갭 6건 외 OK) / known 기계검사 바닥 전수 PASS / round1 기존 수집갭 3건 외 OK /
    round2 기존 수집갭 6건+주석갭 1건 외 OK / 백테스트 recall 5/6 유지 / pytest 162 passed·1 xfailed.
  - **다음**: 라운드4 5사 유지. 라운드4·5 연속 신규 0이면 10사 배증 + 수렴 시 잔여 기계 floor 전수 스캔 전환.
- **라운드2 수정 검증 + 라운드3 감사 완료 (2026-06-11)**: 라운드2 수정(R1~R5) 직접 재현 검증
  통과(round2 검산 전건 OK·R2 처분 +720백만 양수 보존·R5 §I 병합 노출·round1/known 무회귀·
  pytest 160). **라운드3**(seed=3: 금융 314조·별도전용·blank고비중·금융 83조·단년소형, 16
  회사연도) — p1-auditor 게이트 PASS[round3], 핵심 주장 직접 재현. **파이프라인 값 소실 0**
  (밀도 뚜렷한 하락 — 신규가 "값 손실"→"정밀도"로 이동). 발견: R3-b 부분자식 소계 잔여 누락
  (검산 -5, 00557933) · M1 alias 오염(지분법이익잉여금이 OCI canonical에, 00791209) · N5 본문
  CF 실증(00614593, 2단계 결정 자료 누적) · **하니스 H1(§D 절사vs반올림 — 소실 8건 전부 거짓
  경보)·H2(§I 강등/SCE 생존을 ✗소실 오표기) 발견 즉시 수정·검증 완료**(소실 0 확인, 진짜 병합
  소실은 유지 노출). 수집 갭 5사째(금융업 2020~22 일관) — 별도 수집 점검 과제로 분리. **다음:
  [data/backtest/_P1_ROUND3_FIX_PROMPT.md](../../data/backtest/_P1_ROUND3_FIX_PROMPT.md) 실행
  (R3-b·M1 — 경미 2건) → 라운드4 5사 유지**(신규 2건이라 배증 보류 — 라운드4·5 연속 신규 0이면
  10사 배증 + 수렴 시 잔여 ~1,600사 기계 floor 전수 스캔 전환).
- **라운드2 수정 완료 (2026-06-11, `_P1_ROUND2_FIX_PROMPT.md` 실행)**: R1~R5 수정·검증. TDD(실패→GREEN).
  - **R1 소계 라벨 변형**: `총포괄이익`→총포괄손익 alias, `소유주와의 거래`(합계/등)→subtotal
    (canonical + `subtotal_label_markers`, config). 00117577 6개년 leaf 이중계상 전부 해소.
  - **R2 통합 canonical 부호 분기**: `자기주식변동`(취득·처분 양방향) 무조건 -abs 불가 → label 분기
    (`sce_combined_deductions`: 취득/소각/감자→-abs, 처분/발행/재발행→+abs). `_apply_sign` 도입.
    00688996/2023 검산 OK + **자기주식 처분(00102432/2025) +값 보존 확인**(역버그 방지, ripple).
  - **R4 total 라벨 변형**: `기말자본`→자본총계 alias. 00121686/2025 total 식별→검산 OK.
  - **R3 계층 보정(D5 역방향)**: `sce_balance`에서 leaf-only가 어긋나고 소계까지 더하면 맞으면 그
    소계를 leaf로 채택(자식 있는 D5는 leaf-only가 이미 맞아 무회귀). 00169215/2025 검산 OK.
  - **R5 하니스 §I 보강**: dedup 이전 raw 매퍼 매핑으로 병합 소실 label 노출(`✗소실`+기계요약 카운트).
    01675421/2023 보통주자본금→자본금 collapse 가시화.
  - **검증**: round2 검산 전건 OK(수집갭 6년·주석갭 1건 부수 기록 제외) / round1·known 무회귀
    (D5·N1~N3 재발 0) / 백테스트 recall 5/6 / pytest 160 passed / 게이트 PASS[round1]·[round2].
  - **다음**: 라운드3(5사 유지). 새 코드 룰은 R2 분기·R3 계층보정 2건뿐 — 2연속 신규 0이면 10사 배증.
- **라운드1 수정 검증 + 라운드2 감사 완료 (2026-06-11)**: 라운드1 수정(N1~N5) 직접 재현 검증
  통과 — round1 배치 소실 0·검산 전건 OK(수집갭 3연도 제외), **known-19 사상 첫 기계검사 전수
  PASS**(셀트2018·세토2018 잔여 D5까지 해소), N4 생존(25,953,661,360 '기타' 보존)·N5 플래그
  50건+측정 리포트(159,863건)·pytest 155. 이어 **라운드2**(seed=2, `_round_targets_round2.json`:
  금융 715조·별도전용·blank금융·다년대형·단년소형, 16 회사연도) — 샘플러에 기감사 회사 제외+
  라운드별 파일 분리 추가. p1-auditor 통독·게이트 PASS[round2], 핵심 주장 3건 직접 재현.
  **신규 R1~R5**: R1 소계 라벨 변형(총포괄이익·소유주와의 거래)이 role 밖→leaf 이중계상
  (00117577 6개년 전부) · R2 통합 canonical 자기주식변동 차감 미등록+양방향 label 분기 필요
  (00688996 1.14조) · R3 leaf 부재 소계의 변동 누락=D5 역방향(00169215) · R4 기말자본 total
  변형 미등록=검산 불가(00121686) · R5 하니스 §I dedup 후 집계라 동액 병합 사각(01675421).
  수집 갭 반복(금융지주/신규상장 3사째, A6) + 00121686 주석 raw 부재. **다음:
  [data/backtest/_P1_ROUND2_FIX_PROMPT.md](../../data/backtest/_P1_ROUND2_FIX_PROMPT.md) 실행 →
  라운드3도 5사 유지**(신규 5종이되 대부분 config 변형 갈래 — 코드 룰 신규는 R2 분기·R3
  계층보정 2건으로 좁아지는 중. 2연속 신규 0이면 배증).
- **라운드1 수정 완료 (2026-06-11, `_P1_ROUND1_FIX_PROMPT.md` 실행)**: N1~N5 수정·검증. TDD(실패→GREEN).
  - **N4 EXACT 소실**: `_dedupe_canonical_rows` 강등 보존 가드를 distinct account_id EXACT 중복까지 확장
    (`_EXACT_GRADE`). 서로 다른 표준 id가 같은 canonical로 수렴해도 distinct line item이라 비대표를 드롭
    대신 '기타'로 보존. 00120526 2024 CFS 25,953,661,360 + 2025 CFS 144,246M·OFS 100,000M 생존(소실 0).
  - **N2/N3 차감 결정화**: `sce_deduction_changes`에 신종자본증권 상환/배당/이자·배당금지급 등록(-abs).
    raw 부호 의존 비결정 제거(config 데이터 등록, 하드코딩 아님).
  - **N1/D5 검산 leaf-only**: SCE 변동행 `change_role`(begin/total/subtotal/restated_begin/leaf) config
    표준화(`sce_change_roles`) + sce_equity_components에 컬럼 추가. `sce_balance` helper(materiality 허용오차
    1e-7+1000원)로 §F·`_sce_balance_check.py` 일치. 소계(총포괄손익·기타포괄손익)·조정후개시(기초자본(조정후)·
    기초보고금액·재작성 브릿지) 제외, leaf만 합산. 8건 FAIL + 세토2018 + 00159616/2017·01091382/2018 +
    00413046/2018(기초보고금액+재작성 reconciliation) 전부 해소.
  - **N5(확정 범위)**: 본문 `map_row`에 id≠label 정확 alias면 `id_label_conflict` 플래그(매핑은 id-first
    유지=무회귀, score·dedup서 EXACT 동급 취급). 전수 측정 `_audit_id_label_conflict.py` → `ID_LABEL_CONFLICT
    _AUDIT.md`(4773 회사연도 159,863건·3패턴: ①폐지715 ②계열65,422 ③이질93,726). 매핑 규칙 변경은 2단계 별도 회차.
  - **검증**: 라운드1 5사 소실 0·SCE검산 전건 OK(수집갭 00117267 2020~22 제외) / known 19 기계배치 전수 PASS
    (소실 0·SCE OK) / 백테스트 recall 5/6 유지 / pytest 155 passed·1 xfailed / 매트릭스 게이트 PASS[round1] 22×6.
  - **다음**: 라운드2(표본 5사 유지). N5 측정결과 검토 후 2단계(폐지개념 id→label 우선 등) 결정.
- **라운드1 감사 완료 → 수정 프롬프트 발행 (2026-06-10)**: 반복 루프(층화 N사 재정규화→하니스→
  수정→재검증) 1회차. `_round_sampler.py`(계정구조 5층: 금융형·별도전용·blank고비중·다년대형·
  단년소형, seed=1 재현) + 러너/게이트 라운드 인자화(`_p1_review_all.py <targets.json>`, 산출물
  접미사 격리). 5사 22 회사연도 감사 결과 **신규 결함 5종**(N1 조정후기초자본 변동합산 ~3조 ·
  N2 신종자본증권 상환/배당/이자 차감 미등록=raw 부호 의존 비결정 · N3 배당 canonical 변형
  `배당금지급` 미등록 · **N4 EXACT-EXACT canonical 충돌 시 비대표 드롭=진짜 소실 3건**(00120526
  차입금상환 259.5억 등) · N5 id-label 모순 무검증) + D5 소계 이중계상 3사 재현(중첩 소계 포함)
  + 수집 갭 실증(00117267 2020~22 raw 헤더만, A6). fresh-context 에이전트 통독·매트릭스 게이트
  PASS[round1] 22×6, 핵심 주장 3건 직접 재현 검증. known-19 무회귀. **다음:
  [data/backtest/_P1_ROUND1_FIX_PROMPT.md](../../data/backtest/_P1_ROUND1_FIX_PROMPT.md) 실행 →
  라운드2도 5사 유지**(표본 5사에서 신규 5종 = 밀도 높음, 배증 보류). N5는 사용자 확정:
  이번 회차는 플래그+전수 모순 측정 리포트까지만(매핑 변경 금지), 매핑 규칙 변경은 측정
  결과를 보고 별도 결정.
- **P1 소실·오매핑 수정 완료 (2026-06-10, `_P1_LOSS_FIX_PROMPT.md` 실행)**: 4개 타깃 수정·검증.
  - **T1 (SCE account_detail 한글 복원)**: `_xbrl_to_finstate_csv.py`에 `_member_ko`(XBRL member→한글
    라벨, 라벨없으면 코드 보존)·`resolve_sce_dimensions`(CSA축→fs+마커, 구성요소축→leaf) 추가. 마커행은
    CSA 한글("연결재무제표 [member]"), 구성요소는 한글 leaf("이익잉여금 [member]")로 DART 정정본 형식
    복원. `_regen_original_csv.py`(백업·주석·DB 미변경, finstate CSV만)로 19사 재생성 → SCE detail
    100% 한글. `SceComponentMap.classify` 마커 component_std='-'로 정렬(§F 검산축). 결과: component_role
    leaf/marker/subtotal 등장(unmatched 전소 해소), 행수=정정본 backup 일치.
  - **T2 (CFS dedup 소실)**: 원인=CFS는 placeholder/회사 udf id라 generic 라벨(파생상품부채)이 같은
    canonical(유동파생상품부채)로 묶여 canonical dedup 충돌, OFS는 distinct 표준 id라 분리 생존.
    `pipeline.py` 수정 ①statement dedup: placeholder는 금액으로 분별 ②canonical dedup: 비대표 ALIAS
    행이 대표와 금액 상이면 드롭 대신 '기타 중요 계정'으로 강등(이중계상 방지·소실 방지). 세토피아
    2019 파생상품부채 944·리스부채 297 생존 확인.
  - **T3 (id-label 모순, 사용자 결정=SCE 한정)**: 일반 label-우선은 본문 464행 회귀(법인세비용→조정 등)
    측정 후 사용자가 SCE 한정 선택. `mapper.map_change_row`(SCE 변동행 전용, 모순 시 label 우선 +
    `ID_LABEL_CONFLICT`)·`sce.py` change_status 컬럼 추가. 본문 `map_row`는 id-first 무변경(무회귀).
    주식선택권(dart_StockDividends 슬롯) → 배당금의 지급(SCE)에서 제외, change_canonical=주식선택권.
  - **T4 (하니스)**: §D abs 비교+부호반전 카운트, §F 검산 재작성(빈집합 명시 FAIL), funnel CIS→IS 주석은
    외부에서 이미 구현돼 있어 검증·정렬만. classify 마커 component_std='-' 정렬로 §F 작동화.
  - **검증**: `_p1_review_all` 전수 19 — 소실 0/19(거짓소실 7→0, 세토피아도 T2로 0), SCE표준화 OK 19/19,
    SCE검산 17/19 OK. 검산 FAIL 2(셀트2018 미분류변동 2.4조·세토2018 자본증감합계 소계 이중계상)는
    T4b가 hollow 없이 정직 노출→LLM verdict 라우팅(T1/T2/T3 회귀 아님). pytest 150 통과(1 xfail).
    백테스트 positive recall 5/6 유지(두산·아스트·디아이·모델·셀트 discovered, 세토피아 변동미미),
    삼성 clean·KAI negative 미발굴 — baseline 동일 무회귀. 세토피아는 T2로 데이터(944·297) 복원됐으나
    신호 결과 불변(BW 손익영향 제한적). 변경 파일: `_xbrl_to_finstate_csv.py`·`_regen_original_csv.py`(신규)·
    `pipeline.py`·`mapper.py`·`sce.py`·`config.py`·tests(`test_xbrl_converter.py` 신규·`test_normalize.py`).
- **하니스 원문대조 보강 (2026-06-10)**: 리뷰 하니스가 "P1 산출물을 보여주기"만 하고 DART 원문과
  대조하지 않던 구멍 3개 수정. ①`_p1_company_review.py` §D를 매퍼 미경유 원문 전수 대조로 교체
  (기존은 같은 매퍼로 raw를 재매핑해 비교하는 순환 — 매퍼 버그 미탐): raw→norm 행수 funnel +
  raw 금액 미출현(소실 후보) 목록. ②§I 병합 가시화 신설(1 canonical ← 2+ raw label 전시, LLM이
  이질 판정). ③OFS 전용 회사 §A 빈 dump 수정(CFS→OFS fallback)·전 섹션 truncation 표기·주석
  적재율(raw TSV 분모)·prior 결측률·§B 0값 truthiness 수정. ④`_p1_review_all.py` 자식 크래시
  rc/stderr 보존 + [기계요약] 파싱(소실·병합 컬럼). **전수 재실행 결과: 19/19 중 9건 소실 후보**
  (예: 00159616 SCE 주식선택권 3,292·종속기업 유상감자 572 — raw에 있는데 정규화 어디에도 없음,
  대부분 SCE), 병합 0건(전 DB 스캔 0 + 합성테스트로 검출기 발화 증명 = 진성 0). 한계: 미출현
  검사는 동일금액 우연일치 미탐(필요조건 floor).
- **LLM 심층 탐색 완료 → 수정 프롬프트 발행 (2026-06-10)**: 소실 9건 해부 결과 ①7개 회사연도분
  = -abs 차감 부호 정규화에 의한 **거짓 소실**(데이터 정상, 하니스 §D가 부호까지 일치 요구한 탓)
  ②세토피아 01091382/2019 2건 = **진짜 소실**(CFS blank account_id 동명행 dedup — 파생상품부채
  945·리스부채 298 증발, OFS는 정상 분리. BW 분식 핵심 계정). 추가 발견: ③**SCE 구성요소 표준화
  전사 사망** — 원본 교체 컨버터가 account_detail에 XBRL member 코드 기록, 분류기는 한글 alias라
  19건 전부 role=unmatched·marker 0행 → 하니스 §F 검산이 "기초 0+Σ0=0" hollow ④주식선택권
  (dart_StockDividends)→"배당금의 지급(SCE)" id-label 모순 오매핑 ⑤CIS funnel 격차는 IS 재분류로
  정상(손실 0). **다음: [data/backtest/_P1_LOSS_FIX_PROMPT.md](../../data/backtest/_P1_LOSS_FIX_PROMPT.md)
  실행** (T1 컨버터 한글 라벨 복원 → T2 CFS dedup → T3 모순 매핑 → T4 하니스 보강, 검증 프로토콜 포함).
- **하니스 최종본 — LLM 변동성 보완 구조 (2026-06-10)**: T4 선반영 + 변동성 장치 3종. ①기계화:
  §D 절대값 비교(거짓 소실 제거)+부호반전 별도 카운트, §0b SCE 표준화 전멸 FAIL, §F 검산을 bare
  합계행 기준으로 부활(빈 입력=명시 "검산 불가 FAIL", hollow 차단), funnel CIS 재분류 주석.
  ②판정 매트릭스: 배치가 회사연도×6차원 템플릿(`_review_dumps/_VERDICT_MATRIX.md`) 생성,
  `_p1_verdict_gate.py`가 전수 존재·전 칸 체크·근거 인용을 기계로 셈(FAIL/PASS 양방향 검증됨).
  ③전용 에이전트 `.claude/agents/p1-auditor.md`(고정 절차+기만 패턴 7종 내장, fresh-context 실행).
  전수 재실행: 소실 18건→0(거짓 경보 소멸)·세토피아/2019 진짜 소실 2 유지·SCE표준화 FAIL 18/19
  노출·**부활한 검산이 신규 이상 3건 검출**(00413046/2018 차이 2.4조 등 — T1 수정 후 재평가).
  하니스 정리: [docs/agent/P1_AUDIT_HARNESS.md](P1_AUDIT_HARNESS.md).
- **진행 중 (2026-06-10): 분식사 정정본→원본(정정 전) 교체 완료.** 백테스트가 정정본(세탁
  데이터) 위에서 도는 문제 해결. DART는 정정공시 시 원본 미삭제(영구보존)·정정본 별도 rcept
  추가, finstate_all API는 최신(정정본)만 반환. 원본은 `list(final=False)`→원본 rcept→
  finstate_xml로 수집. **XBRL→finstate_all CSV 컨버터**(`data/backtest/_xbrl_to_finstate_csv.py`)
  작성, round-trip 검증(정정 변환=디스크 정정 97.8~98.7% 일치, 핵심계정 전부). 분식 19 회사연도
  본문+주석 원본 교체(`_migrate_to_original.py --apply`), 정정본은 `data/_backup_corrected/` 백업.
  순이익 전수 스캔값 일치(셀트2016 무형자산 848,323=분식값 확인). **원본=진짜 분식본 검증: 본문·
  주석 값+내용+DART 출처 3중 확인**(셀트=개발비 자산화·두산=공사손실 은폐가 주석에 박힘).
  세토피아2019만 원본 빈템플릿 skip. **원본 재정규화 완료**(6사 31 회사연도, 순이익 18/18 원본값 일치·
  항등식 18/18 통과). 하니스(_p1_company_review) 검사: 셀트2016 무형자산 848,323(개발비 자산화)·두산2017
  미청구공사 1,969,816(진행률 과대) 등 분식 단서가 원본 정규화 데이터에 드러남. **정답지 정리**: known_cases.json에서
  참고용(runnable=false, pre-2015) 분식 7사 삭제→positive 6사(실행가능 전부)만 유지.
- **하니스 보강 + 전수 재검사 (2026-06-10)**: "하니스 검사를 2개사만 보고 통과" 사고 후 근본수정. 원인=하니스가
  주석 미읽기·필수테이블 MISSING 미FAIL·전수 미강제(LLM 양심 100% 의존) + 훅은 체크박스만 셈 + 내 "대표" 다운스코프.
  수정: ①`_p1_company_review.py` §0 데이터완결성(normalized·sce·note_facts_classified MISSING/빈 FAIL) + 주석
  섹션 H(차원축 분포) + docstring "전수 원칙" ②`_p1_review_all.py` 전수 배치(정답지 positive·runnable 19 전수
  강제, 기계검사 PASS/FAIL + dump→_review_dumps/) ③PROTOCOL "전수 기본" 명문 ④원본 주석 재적재(load_notes_classified
  6사·30회사연도·8,236행). 결과: **19/19 전수 기계검사 PASS + 분식단서 전수 드러남**(두산 미청구공사·아스트 재고·
  셀트 무형자산·디아이 자본/지분법·모델 매출·세토피아 금융자산). 기계검사가 거짓양성 3건(별도/CIS) flag→확인→개선.
- **원본 데이터 백테스트 재실행 (2026-06-10)**: 정정본→원본 교체 후 첫 백테스트. 안전성 확인(_ensure_raw=raw있으면
  skip 원본보존·spike=현파이프라인). 결과: **분식 5/6 발굴**(두산·아스트·디아이·모델·셀트 discovered=True,
  세토피아 미발굴=BW 손익영향제한적) + **대조군 정상**(삼성clean·KAI negative 미발굴). recall 5/6=정정본 baseline
  동일(신호가 구조·괴리 기반이라 정정본에도 흔적). 발굴 근거가 실제 분식계정 정확히 가리킴(두산 미청구공사·
  공사손실충당·종속기업투자 / 셀트 무형자산(개발비)·재고). **baseline 정량비교 교란 발견(§9)**: git HEAD(정정본)
  vs 현재(원본) fired 두산125→343·삼성113→215인데, **삼성(미교체 clean)도 +102 = 파이프라인 개선(canonical
  116→2,028) 효과 교란**. 단순 git비교로 "원본이 더 잡음" 단정 불가. 순수 원본효과는 백업 정정본(_backup_corrected)을
  현 파이프라인으로 돌려 통제비교해야. **다음: (선택) 통제비교 또는 세토피아 미발굴 심층분석.**
- 단계: 설계 확정 → 프로젝트 뼈대 구축 → L0 수집 → L1 정규화 → L2 신호엔진 →
  **S1 전기/전전기 금액 보존 + S2 소급재작성 신호 + S3 재무제표 5종 신호 완료**
- **진행 중 (2026-06-07): Phase1 분류 품질 전수 감사 완료 → 분류 확장 설계 토의 대기.**
  미분류 51.1%·신규분류후보 2080종·SCE 2D·오매핑 등 미토의 결정은
  [PHASE1_CLASSIFY_AGENDA.md](PHASE1_CLASSIFY_AGENDA.md)에 항목화. 하나씩 토의해 확정 예정.
- **Phase1 정합성 감사 2차 완료 (2026-06-09)**: 라벨 8사 B~F 이월항목 읽기전용 측정
  ([../../data/backtest/_P1_INTEGRITY_AUDIT2.md](../../data/backtest/_P1_INTEGRITY_AUDIT2.md),
  스크립트 `_p1_integrity_audit2.py`·산출 `_p1_audit2.json`). 결론: 자산=부채+자본·유동/비유동
  =총계·당기순이익 4표(IS·CIS·CF·SCE) **35 회사연도 전부 일치**, 가짜exact 0·scale이상치
  0·회사간 비교불가 0으로 본문 수치는 Phase2 적합. **결함 4종**: ①SCE roll-forward 단순검산
  불성립(배당변동 양수 부호 + 미분류 변동 '기타 중요 계정' 적재), ②주석 concept↔본문 canonical
  account_id 직접매칭 0건, ③raw 행 추적 컬럼(rcept_no/ord) 부재, ④법인세비용 부호 회사·연도
  비일관(원천 특성·NI=세전±법인세로 판별). 손익항등식 ok21/중단영업5(두산,정상)/법인세부호5.
  무음 empty 2건(모델솔루션 상장전, 정당). 분식 vs 정상 정합성 차이 없음(정합성≠판별기 재확인).
- 최근 작업 (2026-06-03): BS 34개, IS 17개, CF 18개 canonical을 raw account_id 기반으로
  등록하고 L1 정규화를 재실행했다. `src/signals/universal.py`를 추가해 BS·IS·CF 모든
  account_id에 YoY, z-score, 구성비 급변, CFS/OFS 괴리 신호를 적용했다. relationship chain에는
  영업이익→순이익, 차입금→재무활동CF→투자활동CF/CAPEX, 순이익→영업CF→운전자본변동,
  연결 구조·비지배지분 사슬을 추가했다. L4 6관점 live에서 사업결합순현금유출,
  장기차입금차입, 운전자본변동, 기타수익 z-score, 장기금융상품 취득, 기타자본항목 CFS/OFS
  괴리가 queue 상위로 올라왔고, 교차 결과는 사업결합순현금유출 conflict로 나왔다.

## 완료

- 설계 단일 출처 [PLAN.md](PLAN.md) — 아키텍처 L0~L6, 원칙 5개, MVP 1~3
- 결정 D1~D4 ([DECISION.md](DECISION.md))
- 스킬 2종(`disclosure-review`/`disclosure-testing`) + skill-rules.json
- CLAUDE.md, pyproject.toml, config/playbooks, src/ 스캐폴딩, `src/schemas/findings.py`
- Codex/비-Claude 진입점 [../../AGENTS.md](../../AGENTS.md) + [CODEX.md](CODEX.md)
- L0 수집 모듈 [../../src/collect](../../src/collect)
- L0 raw 데이터 `data/companies/00126380/{2022,2023,2024,2025}/raw/`
- Raw 데이터 계약 [DATA_CONTRACT.md](DATA_CONTRACT.md)
- L1 정규화 모듈 [../../src/normalize](../../src/normalize)
- L1 canonical config [../../config/canonical_accounts.yaml](../../config/canonical_accounts.yaml)
- L1 정규화 결과 `data/companies/00126380/{2022,2023,2024,2025}/analysis.duckdb`
- L1 측정 보고서 [NORMALIZE_REPORT.md](NORMALIZE_REPORT.md)
- 결정 D5 ([DECISION.md](DECISION.md))
- L2 tool DSL [../../src/analysis_tools](../../src/analysis_tools)
- L2 MVP1 관계 사슬 계산 [../../src/signals](../../src/signals)
- L2 계산 보고서 [SIGNAL_REPORT.md](SIGNAL_REPORT.md)
- L2 threshold 빨간불 추출 [../../src/signals/red_flags.py](../../src/signals/red_flags.py)
- 수치 분석가 1명 [../../src/agents/numeric_analyst.py](../../src/agents/numeric_analyst.py)
- D82242 주석 인덱서 [../../src/notes/indexer.py](../../src/notes/indexer.py)
- 매출채권 주석 분석가 [../../src/agents/note_analyst.py](../../src/agents/note_analyst.py)
- 매출채권 주석 매핑 [../../config/playbooks/note_mappings.yaml](../../config/playbooks/note_mappings.yaml)
- 외부 맥락 스키마 [../../src/schemas/context.py](../../src/schemas/context.py)
- Google Search grounding ContextBrief [../../src/agents/context_brief.py](../../src/agents/context_brief.py)
- 범용 계정 Finding 파이프라인 [../../src/agents/account_finding.py](../../src/agents/account_finding.py)
- 재고 Finding 실행점 [../../src/agents/first_inventory_finding.py](../../src/agents/first_inventory_finding.py)
- 첫 Finding 실행 기록 [FINDING_REPORT.md](FINDING_REPORT.md)
- Gemini 일시 오류 재시도 테스트 [../../tests/test_red_flags_and_agent.py](../../tests/test_red_flags_and_agent.py)
- 주석 파싱/주석 분석가 mock 테스트 [../../tests/test_notes_and_note_agent.py](../../tests/test_notes_and_note_agent.py)
- 외부 맥락 출처/비오염 테스트 [../../tests/test_context_brief.py](../../tests/test_context_brief.py)
- 재고 계정 파이프라인 mock 테스트 [../../tests/test_account_finding_pipeline.py](../../tests/test_account_finding_pipeline.py)
- 결정 D6 ([DECISION.md](DECISION.md))
- 결정 D8 ([DECISION.md](DECISION.md))
- 감사기준·K-IFRS 근거 평가 [AUDIT_BASIS.md](AUDIT_BASIS.md)
- 관계 사슬별 audit_basis 매핑 [../../config/playbooks/relationship_chains.yaml](../../config/playbooks/relationship_chains.yaml)
- 실무 재무지표 플레이북 [../../config/playbooks/financial_ratios.yaml](../../config/playbooks/financial_ratios.yaml)
- 2단계 기준 선정 방법론 [../user/METHODOLOGY.md](../user/METHODOLOGY.md)
- 기본 합계 계정 7개 추가 [../../config/canonical_accounts.yaml](../../config/canonical_accounts.yaml)
- 실무 재무지표 계산기 [../../src/signals/ratios.py](../../src/signals/ratios.py)
- 삼성 3개년 실무 재무지표 보고서 [RATIO_REPORT.md](RATIO_REPORT.md)
- L4 통합 리포트 조립기 [../../src/report](../../src/report)
- 삼성 L4 통합 리포트 [INTEGRATED_REPORT.md](INTEGRATED_REPORT.md)
- 통합 리포트 결정론/LLM mock 테스트 [../../tests/test_integrated_report.py](../../tests/test_integrated_report.py)
- 결정 D9 ([DECISION.md](DECISION.md))
- 결정 D10 ([DECISION.md](DECISION.md))
- 결정 D11 ([DECISION.md](DECISION.md))
- 결정 D13 ([DECISION.md](DECISION.md))
- 결정 D14 ([DECISION.md](DECISION.md))
- 결정 D15 ([DECISION.md](DECISION.md))
- L4 6관점 live 통합 리포트 [INTEGRATED_REPORT.md](INTEGRATED_REPORT.md)
- 동종업계 피어 config [../../config/industry_peers.yaml](../../config/industry_peers.yaml)
- 피어 지표 baseline [../../src/peers](../../src/peers)
- 남은 주석 카테고리 매핑 [../../config/playbooks/note_mappings.yaml](../../config/playbooks/note_mappings.yaml)
- 장기차입금·사채·충당부채 canonical 보강 [../../config/canonical_accounts.yaml](../../config/canonical_accounts.yaml)
- BS·IS·CF 주요 canonical 확장 [../../config/canonical_accounts.yaml](../../config/canonical_accounts.yaml)
- IS·CF 흐름 관계 사슬 보강 [../../config/playbooks/relationship_chains.yaml](../../config/playbooks/relationship_chains.yaml)
- 전 계정 보편 스캔 [../../src/signals/universal.py](../../src/signals/universal.py)
- 2025 포함 raw contract [DATA_CONTRACT.md](DATA_CONTRACT.md)

## 백테스트 (검증 — 진행 중, 2026-06-03)

> "토이 같다"는 인식의 근본 원인 = 검증 증거 부재(건강한 회사 1곳만 분석). 실제 분식 사건에
> 도구를 돌려 탐지율을 정량 측정한다.

- **익명 사례집 → 검색 특정은 폐기.** 금감원 감리지적사례(HWP146+PDF84, Codex 파싱 542사례)는
  일부러 익명화·금액 마스킹돼 있어, 가장 구별력 높은 단서조차 웹검색으로 회사 특정 불가.
  업종+연도만으론 후보가 너무 많아 오특정(정답지 오염) 위험. 파싱 산출(분식유형 분포)은 참고로만.
- **방향 전환 = 실명 공개 확정사건으로 정답지 구성**(옵션1 유명사건 + 옵션2 증선위 의결 실명).
  `data/backtest/known_cases.json`(내 검증) → `src/backtest/build_labels.py` → `data/backtest/labels.csv`.
- **실행 가능 8건 확정**(OpenDART 2015~ 가용·상장): positive 6(두산에너빌리티·아스트·디아이동일·
  모델솔루션·셀트리온·세토피아) + clean 1(삼성전자) + negative 1(KAI, 법원 무죄·과징금취소).
  럭슬은 출처 1개뿐이라 제외. reference 7건(대우조선·대우건설·효성·경남기업·STX·모뉴엘·중국고섬)은
  pre-2015/비상장이라 실행불가, 패턴 참고용.
- 정답지·검증방법·각 사건 한계는 사람용 문서 [../user/BACKTEST.md](../user/BACKTEST.md)에 문서화.
  각 사건 한계: 중과실(두산·셀트리온), 연결특화(디아이동일), 상장시점(모델솔루션), 손익영향 제한(세토피아).
- **Stage1 백테스트가 핵심 엔진 버그를 발견**: 전수 스캔 `universal_min_abs_amount: 1조원`(절대값)이
  삼성 같은 거대사에만 맞아, 중소형 분식사(아스트 0.58조·세토피아 0.06조)는 전 계정이 규모 미달로
  스캔 0건이 된다. "계정매핑실패"는 오해 라벨이고 실제론 매핑 정상·규모 필터 탈락. 수정 방향:
  규모 임계를 자산총계 대비 비율(%)로 상대화(`universal_min_pct_of_assets`) + 절대 하한 1억.
  miss_reason도 정직하게(계정부재/규모미달/변동미미/상위10밖) 재정의.

## 백테스트 Stage1 결과 + 해부 (2026-06-03)

- Stage1 결정론 백테스트 실행·재채점 완료. recall: 분식계정 신호 발화 5/6(세토피아만 단일연도),
  상위10 엄격 hit 2/6(두산 미청구공사 z=-16·모델솔루션 당기순이익). 정상 삼성은 채점대상 79개 →
  결정론 단독은 발굴기지 판별기가 아님을 실증(멀티에이전트 층 정당화).
- 사건별 해부 → [../user/BACKTEST_ANALYSIS.md](../user/BACKTEST_ANALYSIS.md). "잡을 수 있었는데
  못 잡음(도구 약점)" 3가지 식별:
  1. 노이즈 매몰(단일 계정 신호 과다 → 분식계정 중위권 매몰, 아스트 재고 68위).
  2. account_id 변경 시 시계열 단절(연결 편입으로 디아이동일 수익 +4088% 점프가 신호 누락).
  3. CFS-only 처리로 OFS-only 연도 누락(세토피아 2017·2018 별도 존재하는데 "데이터부족" 오판).
- 결정론 본질적 한계(→LLM/주석/동종업계): 점진적 분식(셀트리온 개발비 매년 +3~14% 자본화),
  관계로만 드러나는 분식(아스트 재고↑ vs 매출원가 flat), 움직임 포착 후 분식 여부 판단.

## 백테스트 Stage1 수정 ②·③ (2026-06-04)

- `src/signals/universal.py`: 전수 보편 스캔 시계열 키를 `account_id|label`에서
  canonical 우선, 미매핑 정규화 label 기준으로 변경했다. account_id는 evidence locator로
  보존한다. mapped canonical 중복은 연도별 합산하고, 미매핑 label 중복은 금액이 큰 대표 행을
  사용해 유동/비유동 등 우연한 label 중복 이중계상을 피한다.
- `src/signals/universal.py`: CFS 연속 시계열이 불완전하면 OFS 기준을 선택하고, 한 신호
  계산 안에서 CFS/OFS를 섞지 않는다. `src/normalize/pipeline.py`와
  `src/backtest/run_backtest.py`도 CFS/OFS 둘 중 하나만 있어도 해당 연도를 정규화·평가하도록
  바꿨다.
- 검증 결과: 세토피아는 available `[2017, 2018, 2019]`로 데이터부족이 해소되고
  `금융부채`가 상위10밖(14위)으로 재분류됐다. 디아이동일은 `수익` 상위10밖(35위)으로
  신호는 유지되나 hit는 아니다. 삼성전자는 clean 유지, 모델솔루션은 hit 유지. 두산에너빌리티는
  `미청구공사` z-score가 생성됐지만 상위10 기준 12위라 hit에서 miss로 남았다. 채점 로직과
  신호 임계값은 변경하지 않았다.

## 백테스트 P7 관계엔진 연도 수정 (2026-06-04)

- `src/signals/mvp1.py`: `build_mvp1_signal_report`가 `relationship_chains.yaml`의
  `l2_mvp1.years` 대신 frame 실제 연도 또는 호출자가 넘긴 years를 분석 윈도우로 사용한다.
  `src/signals/spike.py`와 L4 회사 리포트 호출부도 years를 명시 전달한다. YAML의 `years`는
  분석 윈도우 제어용이 아님을 deprecated 주석으로 표시했다.
- 재실행 결과: 삼성전자 2022~2025는 기존 config 윈도우와 같아 raw fired 125와 top10 구성이
  불변이다. 아스트는 `cogs-vs-inventory` 관계 신호가 2017, 2018, 2019, 2020, 2022년에
  발화했다. 가장 강한 2022 신호는 99.97pp, 정규화강도 6.6647, 전체 채점대상 61위다.
- strict positive recall은 1/6으로 유지됐다. 모델솔루션 hit 유지, 삼성 clean 유지.
  관계 신호 복구로 KAI negative control은 개발비가 10위에서 19위로 밀려 hit가 False가 됐다.
  채점 로직·임계값·상위10 기준은 변경하지 않았다.

## L4 삼성 하드코딩 일반화 (2026-06-04)

- `src/report/company_report.py`: 삼성 전용 `COMPANY_NAMES`/`COMPANY_DOMAINS` map을 제거하고,
  회사명·업종 메타데이터는 OpenDART `DartCollector.company(corp_code)` 프로필에서 채운다.
  API/profile이 없으면 corp_code 기반으로 degrade하되 분석 계산은 계속 인자와 데이터로만 수행한다.
- `src/peers`와 `config/industry_peers.yaml`: 피어 config를 target corp_code별 구조에서
  DART `induty_code`별 구조로 변경했다. 대상 회사의 `induty_code`가 config에 없으면
  `industry` 관점만 `피어 미구성`으로 deferred된다. 기존 264 피어는 264 업종에만 적용된다.
- `src/report/industry.py`: 삼성전자 사업 다각화 문구를 제거하고, 대상 회사 일반 caveat
  ("대상 회사의 사업구조가 피어와 달라 단순 비교에 한계")로 바꿨다. `industry` 관점은 계속
  판단 필드를 바꾸지 않는 참고 관점이다.
- 데모 러너(`first_*`, `ratios.py`)는 corp_code/year CLI 인자를 받도록 정리했다. 기본값은
  데모 편의용이며 분석 함수 본체의 대상 선택을 좌우하지 않는다.
- Stage1 백테스트는 L4 변경 영향 없이 직전 결과와 동일했다. positive recall 1/6, 삼성 clean,
  모델솔루션 hit, KAI negative hit False를 유지했다.

## Stage1 신호 아티팩트 억제 Tier 1+2 (2026-06-04)

- `src/signals/universal.py`: universal YoY/z-score/mix 스캔에서 CF 계정을 제외하고 BS·IS만
  대상으로 삼았다. CF는 기존 관계사슬과 방향 신호가 담당한다. `scan_cfs_ofs_gaps`는 변경하지
  않았다.
- YoY/mix는 전년 금액이 동적 floor 이상이고 전년·당년 부호가 같을 때만 계산하도록 기저
  가드를 추가했다. 0 근처 폭발·부호반전 YoY 아티팩트를 제거한다.
- universal z-score는 `config/playbooks/relationship_chains.yaml`의
  `universal_z_score_cap: 10`으로 캡한다. 기존 `z_score_abs: 2`, `yoy_pct_abs: 50` 등
  신호 임계값은 변경하지 않았다.
- `src/backtest/score.py`: raw fired_signals는 보존하되, strict top10과 account_scores 산정은
  같은 계정명당 최강 신호 1개로 dedupe한다. hit 규칙(분식계정이 고유 계정 top10 안에 있으면 hit)은
  유지했다.
- 재실행 결과: positive strict hit는 1/6 → 3/6으로 상승했다. 모델솔루션 당기순이익 1위 유지,
  셀트리온 재고자산 9위, 세토피아 금융부채 4위가 포착됐다. 아스트 재고자산 16위,
  디아이동일 수익 13위, 두산 미청구공사 12위로 올라왔지만 여전히 strict hit는 아니다.
  삼성 clean은 유지되고 raw fired는 125 → 110으로 줄었다. KAI negative control은 공사진행률/매출
  9위로 다시 hit=True가 됐다.

## Stage1 mvp1 Tier 1 가드 확장 (2026-06-05)

- `src/signals/mvp1.py`: universal에 적용했던 Tier 1 기저 가드를 관계엔진에도 확장했다.
  `single_account_yoy`는 raw `primary_yoy` 테이블에는 CF 계정을 보존하되, red flag 발화에서는
  `sj_div == "CF"`를 제외한다. CF 흐름은 기존 direction/growth 관계 신호가 담당한다.
- `growth_divergence`는 양쪽 계정 모두 전년 금액이 동적 floor
  `max(자산총계 x 1%, 1억)` 이상이고 전년·당년 부호가 같을 때만 growth%와 divergence를
  채운다. 한쪽이라도 0 근처 기저·부호반전이면 해당 연도 divergence는 `None`으로 둔다.
- 채점 hit 규칙·상위10 기준·기존 신호 임계값은 변경하지 않았다. P4 순위 공정성도 이번 범위에서
  건드리지 않았다.
- 재실행 결과: positive strict hit는 3/6 → 6/6으로 상승했다. 두산 미청구공사 2위,
  아스트 재고자산 6위, 디아이동일 수익 7위, 모델솔루션 당기순이익 1위, 셀트리온 재고자산
  3위, 세토피아 금융부채 4위가 포착됐다. 아스트 `cogs-vs-inventory`는 2017 -43.85pp,
  2022 99.97pp 등 material 기저라 유지됐다. 기존 908pp급 장기차입금 0근처 폭발은 사라졌고,
  material 기저에서 나온 장기차입금 관계 신호만 남았다. 삼성 clean은 유지되고 raw fired는
  110 → 87로 줄었다. KAI negative control은 hit False, miss_reason `변동미미`다.

## Stage1 홀드아웃 검증 — 엔진 동결 (2026-06-05)

- `src/backtest/build_labels.py`: 입력/출력 경로 인자를 추가해
  `known_cases_holdout.json` → `labels_holdout.csv`를 생성했다. 기본 `known_cases.json` →
  `labels.csv` 동작은 유지한다.
- `src/backtest/run_backtest.py`: `--labels` 인자를 추가했다. `labels_holdout.csv` 실행 시
  `backtest_results_holdout.jsonl`과 `BACKTEST_REPORT_holdout.md`를 생성한다. 삼성/KAI 전용
  보고 줄은 해당 회사가 있을 때만 출력한다. clean 회사처럼 fraud_year가 없으면 `run_years`로
  윈도우를 잡는다.
- 신호엔진(`src/signals/*`), `score.py`, config 임계값은 변경하지 않았다. 기존 labels 백테스트는
  positive 6/6, 삼성 clean, KAI `변동미미`로 유지됐다.
- 홀드아웃 결과: positive 3/3. 티피씨메카트로닉스 재고자산 2위, 유네코 매출채권 7위,
  본느 재고자산 6위가 top10에 들어 hit다. 정상 5곳(NAVER, KT&G, 오리온, 한미반도체,
  영원무역)은 모두 hit False다.
- 정상군 잔여 아티팩트: NAVER는 당기순이익 divergence -1854.67pp, 관계기업투자 YoY
  1574.99%, 유형자산취득 divergence -458.52pp가 상위5에 남았다. 한미반도체는 기타수익
  YoY 5239.94%가 상위5에 남았다. KT&G, 오리온, 영원무역은 상위5 기준 극단 아티팩트 후보가
  없다. 삼성 baseline raw fired 87과 비교하면 NAVER 88, 영원무역 110은 비슷하거나 더 높아
  Stage1 숫자 신호 단독은 여전히 검토 큐 생성기이지 판별기가 아니다.

## Stage1 single_account_yoy 기저 가드 완성 + 강도 캡 (2026-06-05)

- `src/signals/mvp1.py`: `single_account_yoy`의 전년 기저 판정을 대상 연도 동적 floor 기준으로
  보강했다. 예: 한미반도체 기타수익은 2022 전년 56억이 2023 자산총계 1% floor 72억에
  못 미쳐 `single_account_yoy` red flag에서 제외됐다. `primary_yoy` 테이블에는 값과
  `valid_yoy_base=False`를 보존한다.
- `config/playbooks/relationship_chains.yaml`: 원칙값 `signal_strength_cap: 10`을 추가했다.
  `src/backtest/score.py`는 `%/pp` 기반 신호(`single_account_yoy`, `universal_yoy`,
  `growth_divergence`, `universal_mix_shift`)의 normalized_strength만 10으로 캡한다.
  raw metric_value는 증거로 보존한다. z-score는 기존 raw z cap을 그대로 쓴다.
- 재실행 결과: 튜닝 세트 positive 6/6 유지, 삼성 clean 유지(raw fired 87), KAI negative
  `변동미미` 유지. 홀드아웃 positive 3/3 유지. 본느 재고자산은 6위→5위, 유네코 매출채권
  7위 유지, 티피씨 재고자산 2위 유지.
- 정상군 효과: 한미반도체 기타수익 YoY 5239.94% 신호는 top5에서 사라지고 fired 60→59로
  줄었다. NAVER의 극단 raw 값(당기순이익 divergence -1840.96pp, 관계기업투자 YoY
  1574.99%)은 raw 증거로 남지만 normalized_strength는 10으로 캡되어 123배·31배 강도로
  순위를 지배하지 않는다.

## Stage1 데이터 정리 시도 — 중단 (2026-06-05)

- 요청 범위대로 신호 임계·채점 hit 규칙은 건드리지 않고 정규화 중복행 제거, BS 소계
  `is_subtotal` config 표시, 매출 alias 보강을 적용해 재실행했다.
- 정규화 중복은 16개 실행 회사 모두 `(account_id, label, year, fs_div, sj_div)` 기준 0건으로
  수렴했다. 소계 계정(`자산총계`, `유동자산`, `부채총계`, `자본총계` 등)은 universal/
  single_account_yoy scoring fired_signals에서 0건으로 사라졌다.
- 그러나 튜닝 세트 positive가 6/6 → 2/6으로 깨졌다. 두산과 모델솔루션만 hit 유지,
  아스트 재고자산 16위, 디아이동일 수익 14위, 셀트리온 재고자산 13위, 세토피아 금융부채
  `변동미미`로 내려갔다. 홀드아웃 positive 3/3은 유지됐다.
- 원인 관찰: BS 소계 제거 자체는 정상 작동했지만, 중복행 제거 후 기존에 덜 보이던 확장계정
  YoY 신호(아스트 임차보증금/미수금/유동파생상품부채, 셀트리온 기타수취채권/기타비용 등)가
  top10을 점유했다. 세토피아는 `금융부채`가 score.py의 현재 동치 매핑상 `부채총계`에
  묶여 있어, BS 소계 제외 후 더 이상 hit에 기여하지 않는다.
- 지시대로 여기서 추가 튜닝을 중단한다. 다음 결정 필요: 소계 제외를 유지할지, score의
  `금융부채→부채총계` 동치 매핑을 데이터 매핑으로 대체할지, 확장계정 alias/소계 판별을 더
  정교화할지.

## Stage1 백테스트 지표 재정의 — 발굴 recall 중심 (2026-06-05)

- 데이터 정리(B1/B2/B4)는 유지했다. 중복행 제거, BS 소계 제외, 매출 alias 보강은 되돌리지 않았다.
- `src/backtest/score.py`: 주 지표를 strict top10 hit가 아니라 분식계정 발굴 recall로 분리했다.
  `account_scores.status`가 `포착` 또는 `상위10밖`이면 `discovered=True`다. 기존 top10 기준은
  `hit` 필드와 리포트의 `상위10 strict hit` 보조 지표로 유지한다.
- `score.py`의 소계 crutch 매핑을 제거했다. 특히 `금융부채→부채총계`, `금융자산→기타 중요 계정`,
  `자기자본→자본총계`를 제거했다. 분식계정은 실제 line item 또는 canonical alias로만 잡는다.
- 재실행 결과: 튜닝 세트는 발굴 recall 5/6, 상위10 strict 2/6이다. 두산 미청구공사와
  모델솔루션 당기순이익은 strict hit, 아스트 재고/매출원가, 디아이동일 종속기업투자·수익,
  셀트리온 재고는 발굴됐지만 top10 밖이다. 세토피아 금융자산/금융부채는 `변동미미`로,
  recall로도 잡히지 않는다.
- 홀드아웃은 발굴 recall 3/3, 상위10 strict 3/3이다. 티피씨 재고자산 2위, 유네코 매출채권 8위,
  본느 재고자산 4위가 strict hit다.
- 해석: Stage1 결정론은 분식계정이 후보로 뜨는지 보는 발굴기다. 정상 변동과 분식 후보를
  최종 판별하는 순위/맥락 판단은 다음 층(관계 우선, 주석/LLM, 외부/동종업계 교차)에서 다룬다.

## Stage1 빈 mvp1 테이블 robustness 수정 (2026-06-05)

- `compare_growth`, `account_yoy_table`, `direction_table`, `build_mvp1_signal_report`가 빈 결과에서도
  기대 컬럼을 가진 빈 DataFrame을 반환하도록 보강했다. 단일연도/관계계정 없음 케이스에서
  `growth_divergences`가 `(0,2)`의 `id,name`만 남아 `divergence_pp` KeyError를 내던 문제를 막았다.
- `red_flags.py`는 growth/yoy/direction 입력 테이블이 비어 있거나 필요 컬럼이 없으면 `[]`를
  반환한다. 크래시 대신 빈 신호로 degrade한다.
- 재현 확인: `run_signal_spike('00688996', [2023])` 후 `extract_red_flags(..., 2023)`이 `[]`를
  반환한다. 기존 백테스트 결과는 유지됐다(기본 발굴 5/6·strict 2/6, 홀드아웃 발굴 3/3·strict 3/3).

## 매출채권 조합 라벨 proxy 매핑 (2026-06-05)

- `config/canonical_accounts.yaml`: `매출채권 및 기타유동채권`, `매출채권 및 기타채권`,
  `매출채권및기타채권`을 canonical `매출채권` alias로 추가했다. 조합 수취채권 라벨이므로
  기타채권이 포함되지만 매출채권 사슬 복구용 proxy로 수용한다.
- `장기매출채권 및 기타비유동채권` 등 장기/비유동 조합은 이번 alias에 넣지 않았다.
- 검증 결과: 기존 백테스트 결과는 유지됐다(기본 발굴 5/6·strict 2/6, 홀드아웃 발굴 3/3·strict 3/3).
  빈 mvp1 테이블 재현도 계속 크래시 없이 `[]`를 반환한다.

## 매입채무 조합 라벨 proxy 매핑 (2026-06-05)

- `config/canonical_accounts.yaml`: `매입채무 및 기타유동채무`, `매입채무및기타채무`,
  `매입채무 및 기타채무`를 canonical `매입채무` alias로 추가했다. 매출채권 조합 라벨과 같은
  proxy 원칙이다.
- 투자부동산·전환사채는 case-specific/스코프 확장 위험이 있어 이번 매핑에서 제외했다.
- 검증 결과: 기존 백테스트 결과는 유지됐다(기본 발굴 5/6·strict 2/6, 홀드아웃 발굴 3/3·strict 3/3).

## 백테스트 홀리스틱 리뷰 — Codex 독립 산출 (2026-06-05)

- `data/backtest/review_packets_0_45.txt`, `review_packets_45_90.txt`, `review_packets_90_200.txt`의
  121사 공용 패킷만 사용해 [../../data/backtest/REVIEW_CODEX.md](../../data/backtest/REVIEW_CODEX.md)를
  작성했다. 외부 검색·실명 추정·코드/config 수정은 하지 않았다.
- 사용자의 추가 재검토 지시에 따라 스크리닝식/체크리스트식 리뷰를 폐기하고 심층 감사조서식 리뷰로
  다시 작성했다. 회사별로 핵심 판단, FS 읽기(BS/IS/CF·운전자본·손익-현금 괴리), 엔진 신호 검토,
  데이터·매핑 검토, 다음 검토 포인트를 분리해 121사 전부 기록했다.
- 집계: 항등식 불일치 0사, 핵심 입력 결측 93건, 핵심 미매핑 84건, 극단 신호/아티팩트 145건,
  엔진 신호 없음 12건, positive 중 분식계정 미발굴 1사(세토피아), clean 강한 신호 5개 이상 51사.
- 이 문서는 Claude 독립 리뷰와 교차검증할 Codex 측 회사별 회계 감각 리뷰 산출물이다.

## FIX 1·2·4 — 매핑 완전화·진행률 계정·sanity 가드 (2026-06-05)

- FIX 1: `normalize_label`이 alias 비교 전 후행 `(손실)/(이익)/(손익)`만 제거하도록 보강했다.
  `당기순이익(손실)`은 `당기순이익`으로 매핑되고, `수익(매출액)` 같은 총액 매출 라벨은 보존된다.
  매출 alias는 총액 라벨(`영업수익`, `수익(매출액)`, `재화의 판매로 인한 수익(매출액)`, `방송수익`)
  중심으로 보강하고, `제품매출` 같은 구성요소는 매출로 끌지 않는다.
- FIX 2: `계약자산`, `계약부채`, `공사손실충당부채` canonical과 `매출 vs 계약자산 증가율 괴리`
  관계사슬을 추가했다. 정규화는 mapped canonical에 대해 회사·연도·fs_div당 대표 1라인만 남기며,
  canonical statement(BS/IS/CF)를 우선해 SCE/CF 중복 라벨이 IS/BS 대표행을 밀어내지 않게 했다.
  새 canonical과 충돌하던 score의 `공사손실충당부채→충당부채` 우회매핑도 제거했다.
- FIX 4: `src/signals/sanity.py`를 추가해 자산총계가 인접/중앙값 대비 100배 이상 튀는 연도를 신호 계산에서
  제외한다. 소프트센(00204226) 2022년이 `suspicious_asset_years == [2022]`로 검출되고 신호 입력에서
  제외됨을 확인했다.
- 안전선 확인: 기본+홀드아웃 재정규화 후 `매출/매출채권/매입채무/자산총계/계약자산/계약부채/당기순이익`
  canonical의 회사·연도·fs_div 중복은 0건이다. 백테스트 결과는 기본 발굴 5/6·strict 2/6,
  홀드아웃 발굴 3/3·strict 3/3이다.
- FIX 3: 신호를 제거하거나 raw 값을 감쇠하지 않고, 대상 계정 당해연도 금액/자산총계 비율로
  트랙 A(규모 계정)와 트랙 B(소액 급변)를 분리 게시한다. 설정은
  `track_split_pct_of_assets: 5.0`, `track_a_quota: 6`, `track_b_quota: 6`이다.
  결과 JSON과 리포트는 기존 단일 top10 strict와 새 track quota hit를 병기한다.
  mega(126사: positive 16, clean 110) 재실행 결과는 발굴 15/16, legacy strict 14/16,
  track hit 13/16이다. 아스트 재고자산은 트랙 A 6위, 셀트리온 재고자산은 트랙 B 2위로
  정원 내 게시된다. 정상 110사의 강도 10 신호는 legacy top10 기준 111개, track A 기준 75개다.
- Stage2 LLM 강화: L4 내부 분석·판정 관점과 synthesis를 GPT-5.4로 전환했다. 외부 검색 관점은
  Gemini 3.1 Pro preview + Google Search grounding을 유지한다. `material_board`는 더 이상
  review_queue 중심이 아니라 핵심 계정 수준 시계열과 전체 지표 시계열을 포함한다. 아스트
  2015~2019 live에서 numeric/flow/change 관점이 review_queue 밖 재고자산을 DIO 432.95,
  재고회전율 0.84, 재고자산 증가 근거로 직접 제기했다.
- 피어 DB 구축: `industry` 관점 매칭을 DART `induty_code` 앞 3자리 중분류로 바꿨고,
  `known_cases_mega.json` + `known_cases_gap.json` 표본의 73개 중분류를 대상으로
  `config/industry_peers.yaml`에 72개 중분류/601개 피어를 등록했다. 표본/known case 회사와
  피어 overlap은 0건이다. 10개 미만 업종은 26개이며, `266`은 피어 후보가 없어 미등록이다.
  아스트 `31322`는 `313`으로 매칭되고, industry baseline은 DIO 432.95 vs 피어 중앙값 46.8,
  재고회전율 0.84 vs 피어 중앙값 7.8을 산출했다. L4 live에서 `industry / completed / High`를
  확인했다.

## Stage1 마무리 — floor 버그·커버리지 갭·트랙 채점 확정 (2026-06-06)

- **floor 버그 발견·수정**: universal 스캔 materiality 하한이 `_exclude_subtotal_rows`로 자산총계를
  잃어 자산×1% 상대하한이 0→1억으로 추락하던 버그. 소계 제외 *전* frame으로 floor를 계산해 자산1%
  복원(현대건설 2023 floor 2,371억=자산1%). 정상 110사 강도10 노이즈 309→109개, 아스트 재고
  16→6위·셀트리온 재고 13→3위로 단일 잣대에서도 상승. ([../user/TROUBLESHOOT.md](../user/TROUBLESHOOT.md) 2026-06-06)
- **커버리지 갭 보강**: 제조 편중 표본에 빠진 업종(건설·통신·전기/가스·게임/SW·항공·물류·리테일·교육)
  대표 17사 추가 → 138사. 건설 4사로 FIX 2(계약자산/계약부채) 실증, DL이앤씨 유동계약자산/유동계약부채
  alias 누락 보강. 새 발견 유형 0(5가지 수렴 유지). ([../user/VERIFICATION.md](../user/VERIFICATION.md) 커버리지)
- **신규분식 5사 복원**: `known_cases_mega.json`의 신규분식(웰바이오텍·에스엘·이렘·더테크놀로지·한창)
  run_years가 비어 dart_ok=False로 빠져있던 stale 수정 → mega **16사 완전체**. 신규 5사 전부 발굴.
- **트랙 채점 확정**: FIX 3 두 트랙을 채점 잣대로 채택(track strict 13/16). 단일 top10(legacy 14/16)
  병기. 트랙 13<legacy 14는 유네코 매출채권이 A 정원 6 밖(7위)으로 잘린 것 — 정원은 오버피팅 회피로
  안 만진다. 트랙 고유 가치는 점수가 아니라 소액 부정 별도 노출(세토피아 B 1위).
- **핵심 통찰**: 노이즈 309개의 진짜 원인은 트랙(FIX 3)이 아니라 floor 버그였다. floor 수정만으로
  분식계정이 단일 잣대에서도 top10 진입. 트랙은 점수론 -1, 가치는 가독성.
- 7개 논리 커밋(develop). pytest 89·ruff 통과. 항등식 0/458.
- **Stage1(결정론 백테스트 검증) 종료.** 결정론은 발굴기(15/16), 정상과의 최종 판별은 Stage2 LLM 층.

## DART 데이터 커버리지 전수 감사 (2026-06-07)

- 사용자 요청에 따라 [../../data/backtest/COVERAGE_AUDIT2.md](../../data/backtest/COVERAGE_AUDIT2.md)를
  전수 기준으로 재작성했다. 표본은 positive 16사 + 정상 다양 10사 + 삼성전자 1사, 총 27사다.
- 회사-연도 모집단 119개에 대해 CFS/OFS 양쪽 raw `finstate_all` 계정 운명 39,612행을
  L0→L1→L2 단계로 추적했다. sidecar CSV는
  `data/backtest/coverage_audit_cache/account_fate_full.csv`다.
- DART API 커버리지는 report code 4종 × fs_div 2(952 레코드), 사업보고서 report API 28종
  (3,332 레코드), event/regstate/share/list(1,296 레코드)를 상태·행수 기준으로 확인했다.
  원문 payload는 출력하지 않았다.
- 주요 정량: BS/IS floor 미달 4,146/11,610(35.7%), L2 미스캔 SCE 11,317행·CF 10,503행·
  CIS 4,321행, `frmtrm_amount` 대조 가능 19,077 pair 중 3,744 불일치(현재 L1/L2 미사용).
- 재확인 결론: `reprt_code=11011`만 수집, CF/CIS/SCE 전수 스캔 누락, KAM/감사의견·정정공시·
  원문 주석 미수집, 주석 매핑 8/70 수준, `ord`/`currency`/전기·전전기 금액 미보존이 확인됐다.
  전기·전전기 금액 미보존은 아래 S1에서 해소했다.

## S1 전기/전전기 금액 정규화 보존 (2026-06-07)

- `src/normalize/pipeline.py`: `finstate_all`의 `frmtrm_amount`, `bfefrmtrm_amount`를 각각
  `prior_amount`, `prior2_amount`로 정규화 출력에 보존한다. `parse_amount`와
  `settings.amount_round_digits` 정책은 기존 `amount`와 동일하다. 비교표시 컬럼이 없는 raw도
  결측으로 degrade한다.
- `OUTPUT_COLUMNS`와 `src.analysis_tools.data.TOOL_COLUMNS`를 확장했다. DuckDB
  `normalized_financials`는 재정규화 시 새 스키마로 생성된다. 오래된 DB는 로더가 누락 컬럼을
  결측으로 채우지만, S2 검증에는 재정규화 DB를 사용해야 한다.
- dedupe 키·대표행 선정 로직은 변경하지 않았다. `_dedupe_statement_rows`는 계속
  `(account_id, label, year, fs_div, sj_div)`, `_dedupe_canonical_rows`는 계속
  `(canonical, year, fs_div)` 기준이며, 정렬 기준도 기존 `amount` 기반이다.
- 검증: `.venv\\Scripts\\python.exe -m pytest -q` 92개 통과. 기본 labels 백테스트는 발굴 5/6,
  legacy strict 5/6, track 5/6으로 유지됐다. mega 백테스트는 발굴 15/16, legacy strict 14/16,
  track 13/16으로 유지됐다.
- 16개 positive 회사 재정규화 결과: 총 19,101행, `prior_amount` 비결측 16,999행(89.00%),
  `prior2_amount` 비결측 16,676행(87.30%).
- 아스트 재고 대조 앵커: 2020 보고서 OFS 재고 `prior_amount` 41,854,541,192원(약 419억),
  2019 보고서 OFS 재고 `amount` 110,270,586,075원(약 1,103억)을 재현했다. 이는 S2의
  N년 전기 표시 vs N-1년 당기 대조 입력이다.

## S2 소급재작성 신호 (2026-06-07)

- `src/signals/restatement.py`: 정규화 frame에서 N년 보고서 `prior_amount`와 N-1년 보고서
  `amount`를 같은 line item 기준으로 대조하는 `scan_restatement_signals`를 추가했다.
  임계값은 `relationship_chains.yaml`의 `restatement_abs_amount: 100000000`,
  `restatement_rel_pct: 1.0`이다.
- restatement용 `scan_key`는 canonical 집계가 아니라 `account_id + normalized label` 기준이다.
  `-표준계정코드 미사용-`은 normalized label 기준으로 비교한다. canonical만 쓰면 서로 다른
  CIS/CF 세목이 같은 canonical으로 섞일 수 있어 line item 기준으로 좁혔다.
- `RedFlagSignal.signal_type == "restatement"`를 생성한다. `metric_value`는
  `prior_amount[N] - amount[N-1]` 원시 괴리 금액이고, evidence에는 N년 비교표시 값과
  N-1년 원래 공시 값을 각각 넣는다.
- 최초 S2 구현에서는 L4 `build_company_report`가 restatement 신호를 review queue와
  `latest_signal_snapshot["restatements"]`에 함께 포함했다. 아래 S2 마무리에서 review queue
  합산은 제거했고, `change_material`의 `restatement_signals` 단서만 유지한다.
- 검증: 신규 테스트 포함 `.venv\\Scripts\\python.exe -m pytest -q` 95개 통과. 기본 labels
  백테스트는 발굴 5/6, legacy strict 5/6, track 5/6으로 유지됐다.
- 16개 positive 회사 전수: 전 `sj_div` 기준 15/16사 394개 신호. 기존 감사 baseline과 같은
  BS line item 기준은 12/16사이며 모델솔루션·본느·이트론·에스엘의 BS 신호는 0이다.
  본느·이트론·에스엘은 전 `sj_div` 확장 시 CIS/CF/SCE 재분류·부호표시 변화가 추가로 잡힌다.
- 분식 직격 앵커: 셀트리온 2016 CFS 무형자산 −108,537,593,133원, 아스트 2020 CFS
  자산총계 −99,677,813,878원, 이렘 2020 CFS 매입채무 −62,726,226,951원이
  restatement 신호로 발생했다.
- 정상 10사 측정: 전 `sj_div` 기준 4/10사 19개 신호, BS 기준 0개다. 정상에서도 CF/SCE
  표시·재분류 신호가 있을 수 있으므로 L4 change 관점은 `sj_div`와 evidence를 함께 봐야 한다.

## S2 보완 — 소급재작성 거짓양성 억제 (2026-06-07)

- 생산 코드 변경은 `src/signals/restatement.py`에 한정했다. 소계 계정은 restatement 신호 후보에서
  제외하되, 자산총계는 자산 대비 floor 계산에는 계속 사용한다.
- 억제 가드: `subtotal_account_names` 기반 소계 제외, `rel_pct >= 1000%` 또는
  `prior_amount`/전년 `amount` 스케일 100배 이상 단위혼입 제외, `max(1억원, 자산총계 x 1%)`
  floor, `(account, fs_div, year, diff)` 중복 제거.
- 임계값은 `load_l2_config()["signal_thresholds"]`에서 읽고, YAML에 없는 값은
  `restatement_rel_pct_max=1000`, `restatement_scale_multiple_max=100`,
  `restatement_min_pct_of_assets=universal_min_pct_of_assets` fallback을 사용한다.
- 검증: `.venv\\Scripts\\python.exe -m pytest -q` 99개 통과, `.venv\\Scripts\\python.exe -m ruff check .`
  통과. 기본 labels 백테스트는 발굴 5/6, legacy strict 5/6, track 5/6 유지.
- 정상 10사 억제 후: 전 `sj_div` 기준 2/10사 2개, BS 기준 0/10사 0개. 이전 S2 측정
  4/10사 19개 대비 감소했다.
- 16개 positive 억제 후: 전 `sj_div` 기준 15/16사 157개, BS 기준 9/16사 33개. 이전 S2
  15/16사 394개, BS 12/16사 대비 신호 수가 줄었다. BS에서 빠진 두산에너빌리티,
  디아이동일, 웰바이오텍은 자산 1% floor 미달 소액 재분류 성격이다.
- 분식 앵커 유지: 셀트리온 2016 CFS 무형자산 −108,537,593,133원, 이렘 2020 CFS
  매입채무 −62,726,226,951원 유지. 아스트 2020 CFS 자산총계 −99,677,813,878원은 소계 제외로
  빠지고, 구성요소 재고자산 −80,511,480,581원이 유지된다.

## S2 마무리 — restatement 큐 제외·change 단서 격하 (2026-06-07)

- `src/report/company_report.py`: `restatement_signals`를 `all_signals` 합산에서 제거했다.
  따라서 review queue와 결정론 점수 산정에는 restatement가 들어가지 않는다.
- `latest_signal_snapshot["restatements"]`와 `change_material()["restatement_signals"]`는 유지한다.
  restatement는 결정론 큐가 아니라 change 관점 LLM의 맥락 단서다.
- `src/report/perspectives.py`: change 관점 rules에 소급재작성 해석 가이드를 추가했다. 회계정책 변경,
  중단영업 재분류, EPS 소급재계산, 오류수정, 사업결합 잠정조정, 연결범위 변동 등 정상 사유를
  위험으로 보지 말고, 이익·자산 과대계상 후 하향 재작성 패턴만 검토 후보로 제기하도록 했다.
  restatement 단독으로 High를 주지 말고, 금융자산·차입금·현금의 광범위 재분류/연결범위 변동은
  정상 소급 후보로 낮춰 보라는 가드도 추가했다.
- 검증: `.venv\\Scripts\\python.exe -m pytest -q` 101개 통과, `.venv\\Scripts\\python.exe -m ruff check .`
  통과. 기본 labels 백테스트는 발굴 5/6, legacy strict 5/6, track 5/6 유지.
- 정상 10사 실제 company report 확인: review_queue의 restatement 0건. change material에는
  target year에 남은 restatement 단서만 들어간다.
- change material 앵커 확인: 셀트리온 2016 무형자산 −108,537,593,133원, 아스트 2020
  재고자산 −80,511,480,581원 및 OFS 재고 −68,416,044,883원, 이렘 2020 매입채무
  −62,726,226,951원이 실린다.
- LLM 표본: 셀트리온 2016 change 관점은 무형자산 하향 재작성과 이익/자산 과대계상 후 하향
  가능성을 검토 후보로 제기했다. 다우기술 2023 change 관점은 restatement 단서 6개를 받았지만
  광범위 금융자산·차입금·현금 재분류와 연결범위 변동 가능성을 들어 Medium으로 낮춰 보고,
  분식 단정 대신 재작성 사유와 금융부채 재분류 맵핑 확인을 제안했다.

## S3 재무제표 5종 전수 신호 (2026-06-07)

- `config/canonical_accounts.yaml`: CIS canonical 10개(총포괄손익, 기타포괄손익,
  FVOCI/매도가능 평가손익, 해외사업환산, 현금흐름위험회피, 확정급여재측정 등)와 SCE canonical
  7개(기초자본, 배당변동, 자본금변동, 자본잉여금변동, 이익잉여금변동, 자기주식변동,
  기타자본변동)를 추가했다. `기초자본`은 roll-forward 시작 잔액이라 `is_subtotal`로 표시해
  universal 신호에서는 제외한다.
- `src/signals/universal.py`: 보편 스캔 대상 `sj_div`를 BS·IS에서 BS·IS·CIS·CF·SCE 5종으로
  확장했다. `scan_cfs_ofs_gaps`는 기존 BS·IS·CF 범위를 유지해 SCE/CIS CFS-OFS 괴리 신호가
  새로 섞이지 않게 했다.
- 노이즈 억제는 새 임계 없이 기존 장치를 재사용했다. 기존 floor/base/sanity/subtotal 제외를
  유지하고, mapped canonical은 `canonical_accounts.yaml`의 `statement`와 실제 `sj_div`가 맞을
  때만 universal 스캔한다. 예: CIS/SCE 표에 반복 표시된 `당기순이익`은 IS canonical이므로
  중복 신호에서 제외된다. 미매핑 확장계정은 전수 스캔 대상이라 그대로 둔다.
- 검증: `.venv\\Scripts\\python.exe -m pytest -q` 102개 통과,
  `.venv\\Scripts\\python.exe -m ruff check .` 통과. 기본 labels 백테스트는 positive 발굴
  5/6 유지(세토피아 `변동미미`). KAI negative control은 CF 확장 후 `무형자산취득` 등이
  top10에 들어 strict=True가 되어, CF 세목 신호는 정상/음성 통제에서 잔여 노이즈가 있음을
  확인했다.
- 삼성전자+16개 positive 재정규화/스캔 결과: 삼성은 funnel BS 177, IS 70, CIS 44, CF 158,
  SCE 19행, universal 신호 BS 6, IS 11, CIS 11, CF 13, SCE 1개다. 16개 positive는 funnel
  BS 2,156, IS 437, CIS 871, CF 2,892, SCE 449행, universal 신호 BS 254, IS 32, CIS 102,
  CF 336, SCE 52개다. 16/16사 모두 CIS/CF/SCE 신호가 발생했다.
- 정상 다양 10사(SK하이닉스, LG화학, 한국단자공업, 아진산업, 강원에너지, 계룡건설산업,
  하림지주, 롯데쇼핑, HMM, 다우기술)는 funnel BS 1,545, IS 150, CIS 483, CF 1,990,
  SCE 270행, universal 신호 BS 101, IS 20, CIS 53, CF 202, SCE 23개다. 10/10사에서
  CIS/CF/SCE 신호가 발생했다. 원인은 정상 영업·투자·재무 현금흐름 세목과 총포괄손익의 큰
  변동이 자산 1% floor를 넘는 경우가 많기 때문이다. S3는 사각 제거 단계이며, CF/CIS/SCE
  신호는 L4 material에서 맥락 판단이 필요하다.
- 표본 내 직접 사례: 세토피아 2019 CF `전환사채의 발행` YoY 1371.55%와 SCE `자본금변동`
  mix shift -31.88pp, 유네코 2018 CIS `총포괄손익` YoY -2169.04%, 셀트리온 2017 CIS
  `지배기업귀속총포괄손익` YoY 136.01% 등이 새 5종 스캔에서 생성된다. 표본 라벨에는
  순수 OCI 은닉으로 확정된 사건이 없어 OCI 신호는 검토 후보로만 기록한다.

## S3 보완 — CF/CIS/SCE 결정론 큐·strict 제외 (2026-06-07)

- universal 5종 신호 생성은 유지하되, `RedFlagSignal`에 선택적 `sj_div`를 붙여
  결정론 큐와 백테스트 scoring에서 statement를 구분한다. `src.signals.universal`의 universal
  신호와 CFS/OFS gap은 실제 `sj_div`를 채운다.
- `src.signals.red_flags`: mvp1 관계 신호는 raw 반복표 `sj_div`가 아니라
  `canonical_accounts.yaml`의 canonical statement를 기준으로 `sj_div`를 채운다. 예를 들어
  SCE에 반복 표시된 `당기순이익`도 canonical statement는 IS이므로 기존 BS/IS 채점에서
  빠지지 않는다.
- `src.report.integrated`: review queue에 들어가는 `RedFlagSignal`은 `sj_div is None` 또는
  `sj_div in {BS, IS}`만 허용한다. `sj_div`가 있는 미매핑 중요계정도 BS/IS만 큐에 넣고,
  원본 `unmapped_material_accounts` material은 5종을 유지한다.
- `src.backtest.score`: `fired_signals`에는 CF/CIS/SCE 신호를 보존하되
  `excluded_from_scoring=True`로 표시해 strict/track 채점에서 제외한다.
- `src.report.company_report`: `latest_signal_snapshot["universal_scan"]`에는 `sj_div`를 포함하고,
  `account_level_series`는 BS·IS·CIS·CF·SCE 5종을 유지한다. 따라서 LLM 관점 material은
  5종 시계열과 단서를 계속 받는다.
- 검증: `.venv\\Scripts\\python.exe -m pytest -q` 104개 통과,
  `.venv\\Scripts\\python.exe -m ruff check .` 통과. 기본 labels 백테스트는 positive 발굴
  5/6 유지, 삼성 clean False, KAI negative control strict=False/track=False(`변동미미`)로
  복귀했다.
- 정상 다양 10사 검증: target 2023 기준 생성 단계에는 CF 108, CIS 15, SCE 10개 비-BS/IS
  신호가 있었지만 deterministic queue 필터 뒤 CF/CIS/SCE 신호 누수는 0건이다. 같은 회사들의
  material에는 `account_level_series` 기준 BS 1,498, IS 89, CIS 464, CF 1,838, SCE 282행과
  universal snapshot 기준 CF 47, CIS 15, SCE 10개가 남아 LLM 관점이 5종을 계속 볼 수 있다.

## S4 미매핑 핵심계정 canonical 보강 (2026-06-07)

- `config/canonical_accounts.yaml`: IFRS16 사용권자산·유동리스부채·비유동리스부채·리스부채,
  투자부동산, 관계기업투자 표준 ID/alias, FVPL/FVOCI/상각후원가 금융자산(유동/비유동 포함),
  순확정급여부채·확정급여부채, 유동성장기차입금을 추가했다. 리스부채는 유동/비유동 구분을
  유지하고, 일반 `리스부채`는 별도 generic canonical로 둔다.
- 관계기업투자는 기존 alias 중복/누락을 정리하고 `ifrs-full_InvestmentsInAssociates`,
  `ifrs-full_InvestmentsInSubsidiaries`를 추가했다. 이트론 raw의 `관계기업에 대한 투자자산`
  (`ifrs-full_InvestmentsInAssociates`)이 `관계기업투자`로 매핑된다.
- 검증: `.venv\\Scripts\\python.exe -m pytest -q` 106개 통과,
  `.venv\\Scripts\\python.exe -m ruff check .` 통과. 기본 labels 백테스트는 positive 발굴
  5/6 유지, 삼성 clean False, KAI negative strict=False/track=False 유지.
- 표본 27사(positive 16 + 정상 다양 10 + 삼성) raw BS 9,536행 재측정 결과:
  미매핑 3,708행, 행 기준 38.88%다. 기존 감사 baseline 48% 대비 9.12%p 하락했다.
  금액 기준 미매핑률은 3.79%다.
- 조 단위 핵심계정 canonical 탈출 확인: 사용권자산 15사 최대 5.16조, 비유동리스부채 18사
  최대 5.62조, 리스부채 5사 최대 5.40조, 투자부동산 19사 최대 2.30조, 유동성장기차입금
  16사 최대 22.26조, FVPL금융자산 8사 최대 29.31조, FVOCI금융자산 5사 최대 16.30조,
  상각후원가금융자산 4사 최대 10.71조, 관계기업투자 26사 최대 59.50조가 canonical로
  매핑된다.
- 16개 positive 회사 관계기업투자는 16/16사에서 매핑된다. 이렘은 2016 CFS 142억,
  2019 CFS 255억/OFS 421억, 2020 CFS 155억 등 `관계기업투자` canonical 행이 확인됐다.
- 과병합/이중계상 안전선: 매출, 매출채권, 매입채무, 자산총계, 계약자산, 당기순이익,
  관계기업투자, 사용권자산, 유동리스부채, 비유동리스부채, 투자부동산의
  `(company, year, fs_div, canonical)` 중복은 0건이다.

## S4 후속: 종속기업투자 canonical 분리 (2026-06-07)

- S4 검증 중 별도재무제표(OFS)에서 종속기업투자와 관계기업투자가 같은 canonical로 합쳐져,
  `_dedupe_canonical_rows`(합산 안 함, 점수·금액 1행만 keep)에서 한 계정이 통째로 버려지는
  데이터 소실을 발견했다(하림지주 OFS: 종속 2.5조 vs 관계 30억 → 관계 소실).
- `ifrs-full_InvestmentsInSubsidiaries`와 종속 단독 alias 6종을 신설 canonical `종속기업투자`로
  분리했다. 종속+관계 통합ID(`...InSubsidiariesJointVenturesAndAssociates`)·통합 alias는 분리
  불가하므로 관계기업투자(대표)에 유지하고 배치 이유를 yaml 인라인 주석으로 남겼다.
- 검증(직접 재현): 하림지주·웰바이오텍·아진산업 OFS에서 종속·관계가 각각 별도 canonical 1행
  → dedupe 소실 0. 미매핑률 38.56%→38.43%(개선). 관계+종속 합쳐 분식 16/16 누락 0. pytest
  107 통과, 백테 positive 5/6·삼성 clean·KAI strict=False 회귀 0.
- 미결(별도 결정): `relationship_chains.yaml` consolidation-structure 체인에 종속기업투자
  포함 여부는 흐름신호 설계 사항으로 보류.

## D-D 구현: SCE 2D(자본구성요소) 보존 (2026-06-08)

- 자본변동표(SCE)는 (변동행 x 자본구성요소) 2차원 표인데, 메인 `_dedupe_*`가 구성요소 열
  차원을 붕괴시켜 변동행당 1행만 남기던 것(전수 39.4만행 손실)을 **별도 2D long 테이블**로
  보존했다(옵션②). 메인 `normalized_financials`·`OUTPUT_COLUMNS`·signals·백테스트 입력 스키마는
  무변경이라 회귀 표면이 0이다.
- `src/normalize/sce.py`(신규): `account_detail` 파이프 경로에서 leaf(마지막 세그먼트)를
  추출(`[구성요소]` 신형·`[member]` 구형 두 관습 모두), 표준으로 묶되 raw도 보존하는 2필드
  방식이다. `component_raw`(원형 leaf — 어느 적립금인지 유지) + `component_std`(13표준 묶음) +
  `component_role`(leaf/subtotal/total/marker). 셀 단위 정확 중복만 제거해 구성요소 차원은
  붕괴시키지 않는다.
- config `sce_equity_components`(13표준+6복합)·`sce_fs_total_markers` 섹션을 신설했다(데이터
  외부화, 코드 하드코딩 없음). 적립금류는 명칭 성격대로 배정(준비금·법정적립금→이익잉여금,
  주식보상·재평가·환산→자본조정/OCI), 미분리 합산열은 `복합_*` role=composite로 격리한다.
  이 섹션은 메인 `AccountMapper`(canonical_accounts만 읽음)와 무관하다.
- `sce_components_company_year`(pipeline) 신규 산출 + `write_sce_components`(db,
  `sce_equity_components` 테이블) + `load_sce_equity_components`(data, SHOW TABLES 가드로 구 DB는
  빈 프레임 하위호환). `spike.py`가 정규화 시 양 테이블을 함께 영속화한다.
- 검증: pytest 128 passed·1 xfailed(baseline), ruff clean, 기본 백테스트 발굴 recall 5/6 유지
  (두산·아스트·디아이동일·모델솔루션·셀트리온 discovered, 세토피아 변동미미, 삼성 clean, KAI
  negative — 회귀 0), 편집 8파일 mojibake 0.
- 보존 수치(2케이스): 삼성 00126380 SCE 428행(leaf 291·marker 81·subtotal 51·unmatched 5),
  std 10종·변동행 18종, 변동행당 최대 8개 구성요소 보존(붕괴 전=1행). 두산 00266961(구형 member
  변형) 134행, subtotal alias "의" 변형 보강 후 unmatched 0. 삼성 잔여 unmatched 5는 희귀
  OCI/매각예정 긴 라벨(3+2행)로 `component_raw`에 완전 보존된다(정보손실 0).

## 다음 할 일 (우선순위)

1. **S5 절대 수준 이상 신호(DIO 등)**: 변동률이 작아도 절대 수준이 비정상적인 재고·운전자본·
   현금흐름 지표를 후보화한다. S4로 핵심 BS 계정 coverage가 넓어졌으므로 수준 신호 입력이
   더 안정적이다.
2. **Stage2 LLM 시연**: 결정론이 발굴한 트랙 A/B 후보를 6관점 L4가 어떻게 설명·교차검증하는지
   확인한다. 특히 세토피아처럼 소액 부정이 숫자 임계로는 변동미미인 사례는 과장하지 않고
   도구 한계로 남긴다.
3. **Stage2 LLM 시연**: 본질적 한계 사례(셀트리온 개발비, 아스트 재고-매출원가 관계)에 6관점 live
   실행해 결정론이 못 한 분별을 LLM이 하는지 확인. (대상 회사 주석 수집 필요)
4. 공시 변동 고도화: D82757 등 주석 전기/당기 텍스트 diff로 우발부채 문구 변화를 수치 변동과 교차.
5. CF 흐름 리포트 보강: 사업결합순현금유출·장기차입금차입·자기주식취득·운전자본변동 원천/사용처 표 분리.

## 열린 이슈 / 주의

- `finstate_all` 응답에는 `fs_div` 컬럼이 없다. 수집 context에서 CFS/OFS를 주입해야 한다.
- `account_id == "-표준계정코드 미사용-"` 행이 존재한다. MVP1/합계 계정에서는 `매입채무`,
  `이자비용`, `당기순이익` 일부 과거 행과 `단기차입금`(2023~2025)이 label alias 보조를
  필요로 했다.
- 전체 raw 행 기준 미매핑 행은 여전히 존재한다. 이제 L4 review queue는 target year CFS의
  금액 큰 미등록 계정을 `unmapped_material_account`로 Low risk 노출하고, 전수 보편 스캔은
  미등록 BS·IS·CIS·CF·SCE account_id도 label/account_id로 신호화한다.
- 연결 특유 이슈는 별도 에이전트가 아니라 CFS/OFS 괴리와 연결 구조 사슬로 흡수한다. 영업권은
  raw에서 단독 계정이 아니라 `ifrs-full_IntangibleAssetsAndGoodwill`에 포함되어 무형자산으로
  다룬다.
- 주석은 표와 텍스트가 섞인 HTML이다. 단순 TXT만으로는 행/열 구조가 손실된다.
- 현재 주석 인덱서는 8개 카테고리 모두 섹션 단위 텍스트로 보존한다. 행/열 정밀 복원은
  아직 하지 않았다.
- 충당부채는 2025 threshold 기준 수치 red flag가 없어 계정 Finding은 생성되지 않았다.
  대신 D82757 섹션은 L4 주석 관점에서 우발부채 공시 검토 후보로 반영된다.
- ROI는 공시 재무제표 기본 합계 계정에 투자원가가 없어 계산하지 않는다.
- 수치 분석가 prompt는 외부 사실을 쓰지 않는다. 정상 설명은 일반적 가능성으로만 작성해야 한다.
- 외부 업황·뉴스 맥락은 L4 `external` 관점으로 교차에 참여한다. 쿼리 생성과 외부 평가는
  `gemini_external_model == "gemini-3.1-pro-preview"`를 사용하고, 내부 분석·판정 관점
  `numeric/note/flow/change/industry`와 종합 문단은 `openai_model == "gpt-5.4"`를 사용한다.
  쿼리 생성은 내부 데이터 기반으로 하되,
  외부 평가는 검색 결과와 출처만 입력받는다. 출처 없는 외부 주장은 버리고 Finding 판단
  필드는 변경하지 않는다. 외부 맥락은 설명용이며 면죄부가 아니다.
- 동종업계 비교는 L4 `industry` 관점으로 교차에 참여한다. 피어는 대상 회사 DART
  `induty_code` 앞 3자리 중분류 config 피어의 재무지표 baseline만 계산하며, 주석·외부·5축
  분석을 피어에 적용하지 않는다. 해당 중분류 피어가 없으면 `industry` 관점만 deferred한다.
- L4 종합 문단은 결정론 큐, 지표 요약, 계정·지표 시계열, 관점별 평가, 교차 결과에 grounding한다.
  live 호출 실패 시 문단만 보류하고 결정론 큐는 유지한다.
- L4 관점 LLM은 독립 입력을 받는다. 수치 관점은 review_queue 참고 후보와 계정·지표 시계열,
  주석 관점은
  `note_mappings.yaml`의 8개 카테고리 note section material, 흐름 관점은
  BS-IS-CF/활동성·이익의 질 material과 계정 시계열, 변동 관점은
  전기 대비 변동 material과 수준·추세 시계열을 받는다. review_queue는 정답이 아니라 참고
  후보이며, 큐 밖 항목도 제공 material에 근거하면 검토 후보로 제기할 수 있다.
  외부 관점은 내부 데이터로 검색어만 생성하고, 평가는
  Google Search grounded ContextBrief만 받는다. 서로의 결론은 입력으로 받지 않는다.
- 감사기준·K-IFRS 근거는 검토 관점의 출처다. Finding은 부정·분식 확정 표현으로 쓰지 않는다.
- 실무 재무지표도 검토 관점이다. 출처 없는 계산식은 플레이북에 넣지 않고, 계정 부족 지표는
  `mvp1_status: account_missing`으로 표시한다. 현재 ROI만 계정 부족으로 남아 있다.
- 공개 KSA 원문별 링크는 확인하지 못한 항목이 있어 [AUDIT_BASIS.md](AUDIT_BASIS.md)에
  “KSA 원문 미검증”으로 표시했다. ISA/IFRS 제목과 요지는 공식 IAASB/IFRS 출처로 확인했다.
- L3 Gemini 모델 기본값은 `config.settings.gemini_model == "gemini-2.5-flash"`다.
  L4 내부 분석 모델은 `config.settings.openai_model == "gpt-5.4"`이고, 외부 관점 query/eval
  모델은 `config.settings.gemini_external_model == "gemini-3.1-pro-preview"`다.
  Gemini fallback은 `gemini_fallback_model` 설정이 비어 있으면 비활성이다.
- 2025 CFS는 IS·CF 계정 확장 후 Medium 관계 red flag가 여럿 있다. 대표 신호는
  사업결합순현금유출 YoY 2102.89%, 장기차입금차입 YoY 593.17%, 자기주식취득 YoY 552.00%,
  운전자본변동 YoY -513.31%, 재무활동CF vs 장기차입금 괴리 -137.49pp다.

## Phase1 분류 품질 전수 감사 (2026-06-07)

- 목적: Phase1에서 숫자를 최대한 잘 분류해 Phase2(LLM)로 넘기기 위해, 무엇이 잘못/덜 분류되는지
  전 회사(1667사)·전 연도(4773 회사연도)·CFS+OFS·5종 재무제표를 운영코드로 전수 측정.
- 3개 전수 리포트 산출(`data/backtest/`):
  - `MERGE_AUDIT.md` — 이질계정이 한 canonical 칸에 뭉개져 소실/오염(충돌 80 canonical). statement 가드 적용 전 측정.
  - `ALIAS_MISMAP_AUDIT.md` — 표준ID 있는데 이름으로 엉뚱한 칸에 매핑(30,847행/540쌍 → 오매핑 후보 52).
  - `UNMAPPED_AUDIT.md` — 미분류 잔여 51.1%·신규분류후보 2080종(CF/SCE 대량)·거시구조 인벤토리(SCE 2D 76구성요소,
    USD 5792행, 기간3개, 주석 62/4773).
- 검증: 기지 케이스 A/B/C 재현, 미분류 후보·SCE 2D raw 2케이스 교차확인. 금액 이상치(corp 00204226) caveat 명시.
- 다음: 분류 확장·구조 보존은 **수정 전 토의**. 미토의 결정 항목 → [PHASE1_CLASSIFY_AGENDA.md](PHASE1_CLASSIFY_AGENDA.md).
  하나씩 토의해 확정 시 DECISION.md로 이관.

## Phase1 분류 확장 적용 — 진행 중 (2026-06-08)

안건(PHASE1_CLASSIFY_AGENDA.md) 중 안전한 것부터 적용. **모든 변경에서 백테스트 baseline 유지(발굴 5/6·삼성 clean·KAI negative, 회귀 0).**

- **D-B 완료**: `mapper.py` ifrs_≡ifrs-full_ 접두사 통일(근본해결) + config 5등록 → 미분류 4,662행 회수.
- **D-F 완료**: `pipeline.py`/`data.py` currency 보존 + `sanity.py` `exclude_foreign_currency_years`(universal·mvp1 연결) → 두산밥캣 KRW→USD 가짜점프 차단.
- **D-C 완료**: 비유동 채권/채무 4 표준ID → 비유동매출채권/비유동매입채무 등록.
- **D-A 진행**(목표 CF+SCE+BS 고가치, chunk별): Chunk1~7 완료로 **canonical 116→214**.
- **D-A ≥50사 일괄등록 완료 (2026-06-08)**: 16고가치 군집 내 미등록 신규개념 중 **≥50사 보편 223종**을
  canonical 승격(사용자 결정=223종). 생성기 `_da_register_gen.py`(v3, **account_id stem 구동**)로
  이질병합 차단: 라벨이 유동/비유동/총계를 구분 못하므로 stem으로 정체성 구동, 병합은 stem 일치만
  (이름매칭 병합 제거 — 지분법 IS↔CF·배당금 영업↔투자 섹션-cross 방지). MERGE 2 + NEW 214.
  alias 충돌 시 드롭(account_id 우선매칭으로 분류). **canonical 214→428**. 재스캔 ≥50사 잔여 80,677행→0.
  <50사 장기꼬리(728종)는 "기타 중요 계정" 유지(설계대로·범위 외). 한글 보존(순수추가·mojibake0·LF).
  검증: pytest 128 passed·1 xfailed, 백테스트 발굴 recall 5/6 유지(fired 불변=두산363·아스트349·삼성215,
  신규 canonical은 CF/SCE라 결정론 점수 제외→신호엔진 무영향, Phase1 분류만 풍부). 회귀 0.
- **부수**: 전역 `~/.claude/CLAUDE.md` §10(전수=사용자요청시만) 수정, hooks `post_write_check.py`(ruff F401 자동삭제 차단)·`guard_bash.sh`(폴링루프 차단) 수정.
- **알려진 xfail 1건**: `test_financial_liability_label_does_not_map_to_subtotal` — 채점기 퍼지매칭이 '금융부채'→'기타유동금융부채' 매칭(백테스트 무해). **채점단계 제거 결정 후 정리**.
- **② 채점/랭킹(strict·track quota) 제거 완료 (2026-06-08)**: 근거 = L4 LLM 프롬프트가 "review_queue는 참고일 뿐 의존 말고 전체 material 검토"라 명시(채점을 권위로 소비 안 함) + CF/CIS/SCE 부분채점 불일치. 변경:
  - `universal.py`·`red_flags.py`: track quota·top-N 선택 제거 → 신호를 materiality 정렬로 **전부 반환**(선택·할당 없음). `_with_track`·`_asset_totals`·track_for_amount 삭제.
  - `tracks.py` 삭제, config `track_*`·`universal_top_n` 제거(signal_strength_cap=정규화 캡은 유지).
  - `backtest/score.py`: strict top10·track 채점 제거, **발굴 recall(discovered)만** 유지. `_account_score` 발굴/미발굴로 단순화.
  - `run_backtest.py` 리포트: 발굴 recall만 출력.
  - 신호 **계산**과 `review_queue`(단순 materiality 참고 정렬)는 유지. Phase1 출력 = 전체 신호 + 전체 시계열 → Phase2.
  - 검증: 전체 116 passed·1 xfailed·ruff clean. 백테스트 발굴 recall 확인(실행중 bdffpx44d).

## D-G 실행: 주석(notes) XBRL 수집 — O4 가용성 검증·표본수집 (2026-06-08, collect 서브시스템)
- 결론: singlnote 웹뷰어(8종·소형사 빈응답) 대신 **XBRL 원본 zip + Arelle**가 분식 소형사에서도
  비금융 주석(무형자산·차입금·관계기업·리스·충당부채·금융상품)을 추출·저장 가능. 표본 10/10 성공.
- 가용성: 현재 보유 zip 4/4,773(삼성만). 표본 분식소형사 다운로드 사업보고서 10/10·zip 10/10·추출 10/10.
- 함정 수정: 분식사 사업보고서는 정정(restatement)으로 수년 뒤 제출·상폐로 결측 → 기존
  `opendart.annual_report()`(year+1·final) 누락. 신규 `find_annual_report()`가 year+1..+4 정정대응.
- 신규 코드 `src/collect/notes_xbrl.py`(find_annual_report·extract_note_facts·save_note_facts) +
  테스트 `tests/test_notes_xbrl.py`(2 passed). 저장: `raw/notes_xbrl/note_facts.tsv`(표본 10).
- 전수 옵션·비용: API ~6k(회사단위list)~24k·1일+α·~3GB·Arelle 4~5h. O4a(분식만)/O4b(전수)/보류 = 사용자 결정(§8).
- 산출물: `data/backtest/AGENDA_DG_NOTES.md §6` + 재현 `_dg_arelle_probe.py`·`_dg_pipeline_run.py`.
- **전수 수집 완료 (2026-06-08, 사용자 결정=전수 직렬)**: 러너 `src/collect/collect_notes_all.py` +
  회사단위 보고서탐색 `notes_xbrl.find_annual_reports_for_company`(list 1회로 API 절감). 196분 직렬.
  - 처리 5,126 회사연도: **ok=4,579** · 보고서없음 239 · XBRL없음 273 · skip 35. 성공률 ~90%.
  - 수집물 `raw/notes_xbrl/note_facts.tsv` **4,614개**(zip 1.30GB + TSV 1.55GB). 빈추출 0건(facts 중앙값 1,012).
  - 실패 512건(10%)=실제 가용성 한계(비상장외감·신규상장·폐지=보고서없음 / 과거·소형 XBRL미제출).
  - 재현 `_dg_timing.py`·`_dg_collect_all.jsonl`(회사연도별 status). 버그수정 `save_xbrl_zip` 014→False.

## 주석 분류기 빌드 (2026-06-08, Option 2: 본문 canonical 재사용 + detail 토큰분류)
신 XBRL `note_facts.tsv`(concept 26k종, 대부분 메타·본문중복)를 Phase2용으로 정제. 사용자 결정 = Option 2.
- **측정(표본 400)**: concept을 3분류 — 흡수 42.3%(본문 canonical stem 일치=재무제표 본문 재게시)·
  메타 14.3%(표지·감사·연락처)·detail 43.4%(주석 고유). detail의 **81.7%**가 28 IFRS 카테고리로 수렴.
- **분류기** `src/normalize/notes_classify.py`: meta필터 → canonical stem 흡수 → note_categories 토큰
  (우선순위 순, 특수관계자>채권·이연법인세>법인세) → 기타주석. 카테고리·토큰 전부 config 외부화.
- **config** `config/playbooks/note_mappings.yaml`에 `meta_tokens`·`note_categories`(28)·`note_high_priority`
  추가(기존 `account_notes` 구 웹스크랩용 보존 — indexer.py·materials.py 참조 무손상).
- **검증**: 프로덕션 분류기 재집계가 survey 수치 정확 재현. 풍부연도(00102858/2024) 실증 = 차입금
  만기·이자율(5.59%·0.75%)·특수관계자 자금대여(50억) 등 리스크 핵심 분류. pytest 136 passed(+8 신규)·
  1 xfailed·ruff clean. 재현 `_dg_concept_survey.py`·`_dg_canonical_reuse.py`·`_dg_detail_cluster.py`·
  `_dg_classify_reconcile.py`.
- **남은 것**: 전수 분류 실행(수집 완료 후) → DuckDB 주석 테이블 적재. 본 단계는 분류기·검증까지.

## 주석 차원(세그먼트) 보존 재추출 (2026-06-08, 사용자 결정=보존)
적재범위 토의 중 발견: 현 note_facts.tsv가 XBRL `context.qnameDims`(SegmentsAxis·GeographicalAreasAxis·
ComponentsOfEquityAxis·SegmentConsolidationItemsAxis)를 버려 흡수 concept이 라벨없는 숫자뭉치가 됨.
- **실측 근거(00100939)**: "Assets" 14값이 실은 사업부문(도료·합성수지·복합성형재료)×지역(한국·중국·
  베트남) 세그먼트 자산 + 내부거래제거(-203bn) + 자본구성요소. 산수검증: 영업부문합 1,177bn − 제거
  203bn = 연결 974bn(본문 CFS 일치). 분식탐지 고가치(부문 자산이전·내부거래·지역집중) → 보존 결정.
- **변경**: `notes_xbrl.py` `NoteFact.dimensions`("축=멤버|…") + `_context_dimensions()` 추가,
  `extract_note_facts`가 qnameDims 보존. `save_note_facts`는 `__dict__`라 자동 7컬럼화.
  `notes_classify` NOTE_FACT/CLASSIFIED_COLUMNS에 dimensions 추가(구 6컬럼 tsv 하위호환).
- **재추출 러너** `src/collect/reextract_notes_dims.py`: 저장 zip 재처리(재다운로드·API 0), dimensions
  컬럼 있으면 skip(재개 안전). 검증: 00100939 재추출 fact 99.7% 차원보유·세그먼트값 정확 라벨,
  세그먼트 813.9bn(도료/한국) 등. pytest 10(notes)·ruff clean.
- **전수 재추출 완료(2026-06-09)**: reextract 3,955 + skip 659 = 4,614, empty 0·error 0, 151분(2세션).
  전수검증(`_dg_reextract_audit.py`): 7컬럼 4,614/4,614(100%)·빈추출 0·mojibake 0·차원보유 98.8%·
  세그먼트축 15%. 보존축에 BorrowingsByName(차입건별)·CategoriesOfRelatedParties·CarryingAmount분해 등.
- **재고 결정**: 차원 보존으로 흡수(본문중복)의 세그먼트·구성요소가 이제 해석가능 → DuckDB 적재범위
  결정(흡수 제외)을 재검토해야 함. 흡수의 dimensioned 행은 본문에 없는 부문·차입건별 분해라 가치 있음.

## 주석 분류 전수 적재 (2026-06-09, DuckDB note_facts_classified)
적재범위 측정·확정(_dg_absorb_value): 흡수 행의 64.5%는 무차원(본문 총계 중복), 35.5%는 유차원
(지역별매출·차입처별·부문손익·특수관계자·자산명세 = 본문에 없는 고가치). **사용자 결정 = detail +
기타주석 + 유차원 흡수 적재, 메타·무차원흡수 제외.**
- **변경**: `notes_classify` `is_dimensioned`(CFS/OFS 외 축 보유)·`select_for_load`(적재필터) 추가.
  `db/normalized` `write_note_facts_classified`(회사연도 격리 테이블, D-D 패턴). 러너
  `src/collect/load_notes_classified.py`(전수, 테이블 있으면 skip 재개). Arelle 불필요(빠름).
- **검증**: 00100939(세그먼트152행)·아스트 9연도 적재 — **무차원흡수 0건**·유차원(자본구성·자산종류·
  세그먼트) 보존 확인. pytest 139 passed(+3 신규)·1 xfailed·ruff clean.
- **전수 적재 완료(2026-06-09)**: loaded 4,605 + skip 9 = 4,614, error 0, **5,767,592행**, 7.5분.
  전수검증(`_dg_load_audit.py`): 테이블 4,614/4,614(100%)·총행 일치·**무차원흡수 누출 0**·메타 0·
  세그먼트행 보존. 전체 fact 978만 중 **~59% 보존**(detail+기타+유차원흡수), ~41% 제거(메타+무차원흡수).
- **테이블 스키마**: concept·label_ko·period·unit·value·dimensions·bucket·category·corp_code·year.
- **다음**: Phase2 LLM이 회사연도별 `note_facts_classified`(차입조건·특수관계자·부문·자산명세 등)를
  본문 신호와 함께 리뷰. 주석↔본문 연결·category 기반 조회는 Phase2 설계 단계.

## 데이터 포함/제외 명세 + Phase1 완성테스트 프레임 문서화 (2026-06-09)
- **신규** [DATA_PIPELINE_SCOPE.md](DATA_PIPELINE_SCOPE.md): DART→수집→정규화→주석→적재 전 단계
  포함/제외+이유 단일출처(11011 연간·CFS/OFS·반기분기제외·2015+한계·canonical428·dedup·통화·주석 3분류·
  적재범위 detail+기타+유차원흡수). 구 [DATA_CONTRACT.md](DATA_CONTRACT.md)는 삼성 스파이크 역사로 강등.
- **신규** [PHASE1_INTEGRITY_PLAN.md](PHASE1_INTEGRITY_PLAN.md): 완성 정합성 테스트 프레임 A~F
  (완전성·항등식·분류품질·차원·핸드오프·신뢰) + 분식5사 1급. 존재론적 3개=정정공시·금액가중·provenance.
- **신규** 사람용 [../user/DATA_SCOPE.md](../user/DATA_SCOPE.md). README 링크 갱신.
- **다음 작업**: 위 프레임으로 정합성 감사 하니스 작성→분식5사+20사 측정→LLM 판단 리포트(미착수).

## Phase1 정합성 감사 1차 — LLM 판단 (2026-06-09, `_p1_integrity_audit.py`)
감사대상 8사(백테스트 라벨) --force 재정규화(428 반영) 후 측정.
- **합격**: 회계 항등식(자산=부채+자본) 전사·전연도·CFS/OFS diff=0~±1 / 이질병합 0 / 5표·CFS/OFS·연도연속 /
  통화 일관. raw→norm 25~30% 감소는 SCE차원·소계 dedup(등식 유지가 손실 아님 방증).
- **🔴 치명 발견 — 정정공시 오염**: 분식 5사 중 **4사(두산·셀트리온·아스트·모델솔루션)의 분식연도
  데이터가 정정본**(rcept 신고일 FY+2~7, 예: 셀트리온 2016~2020 전부 2022-05-12, 두산 2017~19 전부
  2024-03-27). finstate_all이 정정신고 시 정정본 반환. → 백테스트 발굴이 원본 분식 아닌 **정정 흔적**을
  잡을 수 있음. **"실시간 원본 공시 분식탐지"는 미증명**(포지셔닝 직결). 디아이동일·세토피아만 원본(FY+1).
- **🟠 중간**: 금액가중 미분류 高(셀트리온 12~18%·세토피아 22~27%, 행분류율과 별개) → Phase2가 기타버킷
  필수 확인. 주석 컨텍스트 쏠림(삼성2023 6,191행 vs 세토피아2017 0행). 세토피아(미발굴) 데이터결손 의심.
- **하니스 버그(§9)**: 정정공시 검사가 처음 전부 공백 — finstate CSV BOM(`﻿rcept_no`) 키조회 실패 →
  utf-8-sig로 수정 후 정정공시 패턴 드러남.
- **미측정(2차 이월)**: B 유동+비유동·순이익 표간, C 소계 이중계상·비교가능성, D 부호, E provenance·크기,
  F 가짜exact·무음empty. 정정공시가 사활적이라 우선.
- **다음 결정**: 원본 공시 수집 가능성(OpenDART 원본 rcept 지정) 조사 — 도구 사활. 사용자 대기.
- **한계 메모**: 일부 회사 `analysis.duckdb`가 구 스키마(prior_amount 없음) — 본문 재정규화 별개 이슈.

## 전수 매핑 감사 + 미등록 표준 전수 등록 (2026-06-09)
- **매핑 정합성 감사**(`_mapping_correctness_audit.py`): 577 매핑을 IFRS 영문명 vs 한글 토큰 모순검사 →
  **명백한 오매핑 사실상 0**(경계 2건=차입금상환→사채상환). 매핑은 정확. 진짜 갭은 미등록(coverage).
- **금액가중 미분류 정체**: ①소계·총계 중복(착시) ②통합라벨 미등록 ③IS/CIS 세부 미등록(상품/제품/용역
  매출·대손상각비·급여 등). **정정**: 세토피아 매출총액은 분류돼 있었음(어제 "매출 못봤다"는 내 오류).
- **미등록 표준 전수 등록**(사용자 결정=전수): 표준ID 미등록 1,644종 전수. 생성기 P1_ALL=1(stem·충돌0).
  MERGE6+NEW1,588 → **canonical 428→2,016**. 표준ID 미등록 1,644→**0**.
- **검증**: pytest 140 passed·1 xfailed(notes test 갱신=본문개념 흡수전환 반영). 세토피아 재정규화 후
  상품/제품/용역매출·대손상각비·급여 전부 exact. 백테스트 진행중(완료시 5/6).
- **주석 재적재 완료**(2026-06-09, --force): 등록으로 본문개념 흡수전환 반영 → 4,614 테이블 전부 갱신,
  543만행(무차원흡수 ~33만 정상제거, 누출0). 5,767,592→5,431,626.
- **⚠ 후속**: 전수 본문 재정규화 미완(현재 8사+20테스트만 fresh, 나머지 ~5,000 stale).

## Phase1 2차 정합성 감사 — 검사(서브에이전트 결과 재검증, 2026-06-09)
2차 감사(별도 컨텍스트, `_P1_INTEGRITY_AUDIT2.md`)가 결함 4건 보고. §9로 직접 재검증:
- **결함1 SCE 배당 부호 = 진짜 버그**: 삼성2024 이익잉여금 배당 +9.81조(음수여야). 차감변동(배당·자기주식
  취득·감자)이 raw 양수로 보존돼 "기초+변동=기말" 안 맞음. 부호 정규화 필요(차감유형 config 외부화). 미수정.
- **결함2 주석↔본문 연결 0건 = 오경보**: udf_ concept은 9/5519(0.16%)뿐. 주석 concept은 bare 표준명이고
  prefix 벗기면 stem 매칭 120/612(20%) 연결됨(=흡수 분류 방식). 2차가 prefix 안벗겨 0건 오측정.
- **결함3 provenance**(원본 행 식별자 없음) = 진짜·이월. **결함4 법인세 부호 회사별** = 원본 특성(보정불가).
- **합격(2차)**: 항등식·순이익 4표 일치(35건)·비교가능성·가짜매핑0. 2차가 잡은 함정 2개(CF조정 오집·지배지분
  오인)는 자가수정함. 본문 숫자는 Phase2 핸드오프 가능 결론.
- **다음 결정**: 결함1(SCE 부호 정규화) 수정 여부 사용자 대기.

## SCE 차감변동 부호 정규화 — 결함1 수정 (2026-06-09)
- **원인**: 차감변동 raw 부호 혼재 — 배당은 +양수(크기), 자기주식취득은 -음수(이미 부호). 단순 ×-1이
  이미 맞는 자기주식을 거꾸로 뒤집어 삼성 3.62조 잔차(=2×자기주식) 발생(§9가 잡음).
- **수정**: `sce.py` `_as_deduction`=**-abs**(차감유형은 raw 부호 무관 무조건 음수). 차감유형 config
  외부화 `sce_deduction_changes`(canonical_accounts.yaml) + `SceComponentMap.deductions`.
- **검증**: 삼성2024·두산2018·셀트리온2019 **기초+Σ변동=기말 오차 0**(이전 19.6조·71억·0). 영속화 DB
  배당-10.91조·자기주식-1.81조 음수 확인. pytest 140·ruff clean. SCE는 백테스트 점수 제외라 발굴 무관.
- **후속**: 전수 본문 재정규화 시 전체 SCE에도 반영됨(현재 audit 8사+20테스트만 적용).

## 50개 표본 재정규화 + 정합성 검증 — 전수 전 버그탐지 (2026-06-09)
28개(8audit+20test) 제외 50개사 force 재정규화(152 회사연도) + 동일 검증(`_p1_sample50_audit.py`).
- **새 데이터버그 0**: 항등식(자산=부채+자본)·이질병합·가짜exact·empty 전부 **0 실패**. 핵심 정합성 견고.
- **SCE검산 48→8**: 첫 측정 48실패 중 대부분이 **검산식 오탐**(소계 자본증감합계·총포괄손익을 개별변동과
  이중계상). 보정 후 8건. 그 8건도 검산식이 회사별 SCE구조(총포괄손익을 단일income으로 신고 등)를
  일반화 못한 한계. **부호수정 회귀 아님**(audit-8 + 검산가능 케이스서 0오차 검증됨).
- **SCE미검증 89건**: SCE 변동이 표준ID 공백(`-표준계정코드 미사용-`)인 커스텀 라벨(소계 포함) →
  표준화·검산 불가(inherent). 등록으로 못 고침. 원라벨은 보존돼 Phase2가 봄.
- **결론**: 전수 재정규화 진행 안전(새 버그 없음). SCE 자동검산은 구조 다양성으로 전수 자동화 어려움(별개).

## 행별 전수 충실성 감사 — 본문 모든 과목 + 주석 (2026-06-09, `_p1_rowlevel_audit.py`)
"50표본 검증 완료"가 구조검사 5개뿐이었음을 자백 → 행별 감사로 확장(과목 하나하나 + 주석).
- **주석: clean** — 전 회사연도 누락이 정확히 메타+무차원흡수, 차원 보존, 오분류 0.
- **본문**: 분식5사·KAI **소실 0**. 삼성/00103626/00150165에 소수 소실 — 2종:
  - **benign**: 삼성 자본금 보통주/우선주 드롭하나 **총계(897억) 정확 보존**(구성은 SCE 2D에 있음).
  - **진짜 손실**: 유동/비유동 기타금융자산취득이 한 canonical "기타금융자산취득"으로 묶여 dedup이 유동
    흐름 소실. 원인=유동/비유동 lump. 전수측정 **3개**(기타금융자산취득/처분·유동성장기차입금)+지분법OCI(별축).
- **판단**: 규모 작음(소실 ~10M, 분식사0, 주석clean)이나 진짜 fidelity 갭. 수정=lump canonical을 유동/비유동
  분리(D-C식). **이전 "검증완료"는 과장**(자산총계 3과목·SCE marker만 봤지 과목별·주석 전수 아니었음).
- **다음**: lump 분리 또는 전축 lump 전수탐지 후 전수 재정규화 — 사용자 대기.

## 전 축 lump 전수 탐지 + 분리 (2026-06-09, 행별 소실 제거)
사용자 "샅샅이 봤어?" 지적 → 행별 감사가 진짜 소실 발견 → 전 축 데이터기반 lump 탐지·분리.
- **탐지**(`_p1_lump_detect.py`): 한 canonical에 여러 account_id가 다른 값 충돌+총계부재면 distinct lump.
  131 회사연도/41사 측정 → **진짜 lump 9개**(유동비유동 외 종속관계·대손/기타대손·재분류가능불가능 등 전 축).
- **판단**: 8개 진짜(관계기업투자4조 소실·대손상각비36사연도 등), 1개 benign(자본금=총계897억 보존, 탐지기 오탐).
- **분리**(`_p1_lump_split.py`+`_p1_lump_aliasfix.py`): 8 lump→20 canonical(account_id별 정밀). alias는 대표
  canonical에 복원(label-only fallback 유지). canonical 2,016→**2,028**.
- **검증**: lump 재탐지 9→1(자본금만) / 00103626 행소실 4→**0** / pytest 140 passed(테스트 5개 갱신:
  분리 새이름·account_id 정밀) / ruff·mojibake0. 백테스트 진행중.
- **자백**: 이전 "검증완료"(자산총계 3과목·SCE marker만)는 과장. 행별 전수로 진짜 소실 잡음.

## Phase1 LLM 감사 프로토콜 (2026-06-10)
사용자 핵심 요구: 딱딱한 pass/fail이 아니라 **에이전트가 LLM으로서 데이터를 직접 보고 감사관처럼 판단**.
- **문서** [PHASE1_VERIFICATION_PROTOCOL.md](PHASE1_VERIFICATION_PROTOCOL.md): 전 차원(A완전성·B항등식·
  C값정확성·D분류·E주석·F신뢰하류) 카탈로그 — 각 차원에 "LLM이 무엇을 보고 무엇을 의심하나"+구현상태(✅14/
  ◐4/⬜10)+재현. 발견 이력(lump·SCE부호·정정공시·금액가중). "검증완료 과장" 재발방지 SSOT.
- **하니스** `data/backtest/_p1_company_review.py <corp> [year]`: 한 회사연도 전 차원 데이터 dump(본문
  전과목·항등식·미분류상위·raw대조·시계열·SCE검산·이상신호) → 에이전트가 읽고 판단. 두산2018·삼성2024 시연:
  항등식차이0·raw=norm일치·SCE검산0. ruff·mojibake0.
- **미구현 1급**: C1 값정확성(전과목 raw=norm)·F1 신호 dangling(lump로 18개 개명, 신호엔진 옛이름 참조 위험).
- **다음**: 위 프로토콜로 분식사+표본을 깊게 LLM 감사. 전수 본문 재정규화는 버그 다 잡은 뒤 마지막.

## FINAL-REPORT 정합성 감사·교정 (2026-07-16)

Opus 생성 FINAL-REPORT 13장을 전수 감사(주장 456건 대조, census 13/13·경로 37/37) 후 교정.
- **결과**: 불일치 43건(치명 14·경미 29) 전량 교정 + 파생 잔존 7곳 마감. census_diff PASS 43/43,
  현재형 stale 0·mojibake 0. 근거: `_workspace/final-report-audit/` (audit-A~D·SUMMARY.md).
- **치명 근원 7개**: 발견자 6관점 stale·별칭 자동등록 반대서술·external URL 분기 도달불가 누락·
  annotate 3곳 과장·figure_sheet 미배선인데 "감사한다"·guardrails 부착 위치·한계#9 반대서술.
  전부 생성 시점(07-14)에 코드 진실이 이미 확정돼 있었음 — 낡은 docs/docstring/캡션이 코드를 이김.
- **스킬 결함 판정·패치 완료**: final-report 스킬 verify가 커버리지(N/N) 전용, 동작 주장 정합은
  스팟체크 3개뿐이던 것이 원인. `~/.claude/skills/final-report/SKILL.md`에 4건 반영 —
  진실 우선순위(코드>config·테스트>docs·docstring·UI 문구, §2) · 배선 역참조(정독 노트 필수 필드
  + 검증, §2·§5) · 주장 감사 패스(집필 비관여 에이전트가 현재형 동작 서술·다이어그램 엣지 전수
  대조, 스팟체크 대체 금지, §5) · 최신성 앵커(git log 최근 fix 커밋을 팩트시트에, §3).
  '흔한 실패'에 실측 2종(자기서술 전사·존재≠배선≠도달) 추가. 68줄 유지.
- **미결**: `dashboard/onboarding.py:430` UI 캡션이 "사람이 확인 후 등록"으로 낡음 —
  자동 등록 코드(:27 AUTO_REGISTER_MIN_CONFIDENCE=0.7)와 모순. 이번 보고서 치명 오류의 원인
  파일이기도 함(제품 수정 후보).

## 진입 포인트

- 전체 흐름 → [OVERVIEW.md](OVERVIEW.md) → 상세 [PLAN.md](PLAN.md)
- **Phase1 분류 설계 토의 → [PHASE1_CLASSIFY_AGENDA.md](PHASE1_CLASSIFY_AGENDA.md)**
- Codex 작업 지침 → [../../AGENTS.md](../../AGENTS.md) → [CODEX.md](CODEX.md)
- 할 일 → [ROADMAP.md](ROADMAP.md) · 결정·이유 → [DECISION.md](DECISION.md)
- L1 측정 → [NORMALIZE_REPORT.md](NORMALIZE_REPORT.md)
- L2 계산 → [SIGNAL_REPORT.md](SIGNAL_REPORT.md)
- 첫 Finding → [FINDING_REPORT.md](FINDING_REPORT.md)
- 문제 기록(사람용) → [../user/TROUBLESHOOT.md](../user/TROUBLESHOOT.md)
