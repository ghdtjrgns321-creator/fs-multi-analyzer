# 작업: Streamlit 신규회사 온보딩 전처리 페이지

## 1. 목표
- 신규 회사를 Phase1/2 분석에 넣기 전, UI에서 ①온보딩 게이트(전수검사+LLM 통독) 실행 ②이탈(튀는값/미존재/오매핑) 표시 ③이탈을 company_quirks.yaml에 등록 ④재검사 통과 시 Phase1/2 진입을 할 수 있는 Streamlit 페이지를 신설한다.
- 성공 기준: ①`uv run streamlit run dashboard/app.py` 또는 페이지가 import-smoke 통과(`uv run python -c "import dashboard.onboarding"` 류) ②corp/year 입력→게이트 실행→gate_report 표시 ③이탈 등록 폼이 company_quirks.yaml에 안전 append ④게이트 통과 시 Phase1/2 진입 버튼 활성 — 흐름이 동작.

## 2. 컨텍스트
- 읽을 파일(필수): `src/normalize/onboarding_gate.py`(`run_gate(corp_code, year)->gate_report` 인터페이스), `dashboard/app.py`(Streamlit 진입 패턴), `config/company_quirks.yaml`(등록 대상 스키마), `data/backtest/_HOLISTIC_AUDIT_PROMPT.md`(LLM 9렌즈), `src/normalize/config.py`(load_company_quirks), 환경변수(`.env`: OPENAI_API_KEY/GOOGLE_API_KEY — 출력·커밋 금지)
- 따라야 할 패턴: `developing-with-streamlit` 스킬 관례. 기존 app.py 스캐폴딩 형식.
- 배경: 게이트의 결정론 단계(G1~G5)는 `run_gate`가 제공. LLM 전수검사(G6)는 dump + 홀리스틱 프롬프트를 LLM에 보내 findings(P1결함/원공시/P2후보) 산출. corp_code는 데이터(하드코딩 금지).

## 3. 설계 (이대로)
신규 `dashboard/onboarding.py`(또는 dashboard/pages/ 멀티페이지):
- **입력**: corp_code 텍스트 + year(s) 선택.
- **[전처리 검사 실행]** 버튼 → `onboarding_gate.run_gate(corp, year)` 호출 → gate_report를 단계별(G1~G5) PASS/FAIL + 이탈 목록(충돌/소실/오매핑/튀는값) 표로 표시.
- **[LLM 전수검사]** 버튼 → 게이트가 만든 dump + `_HOLISTIC_AUDIT_PROMPT.md` 9렌즈를 LLM(OPENAI/GOOGLE, 기존 agent 모듈 재사용)에 보내 findings 산출 → P1결함/원공시/P2후보로 분류 표시. (API 미설정 시 안내 메시지, 크래시 금지.)
- **이탈 등록 폼**: 각 이탈(오매핑·미존재)에 대해 quirk 등록 — account_override(account_id+label+force_canonical) 또는 alias_addition(canonical+alias) 입력 → `config/company_quirks.yaml`에 **안전 append**(작은 파일이라 load→dict 갱신→dump 가능, 단 UTF-8·기존 주석 보존 노력, mojibake 0). corp_code/year 데이터 키로.
- **[재검사]** → run_gate 재실행. gate_passed True(이탈 0)면 **[Phase1/2 분석 진입]** 버튼 활성(없으면 비활성 + 사유 표시).
- 상태는 st.session_state로 관리.

설계-현장 불일치(run_gate 인터페이스 상이 등) 시 멈추고 STATUS: NEEDS_CONTEXT.

## 4. 단계 체크리스트 (순서 고정)
- [ ] Step 1: onboarding_gate.py(run_gate 시그니처·gate_report 구조)·app.py·company_quirks.yaml·홀리스틱 프롬프트·agent LLM 모듈 읽고 인용
- [ ] Step 2: `dashboard/onboarding.py` 작성(입력→게이트→리포트→등록폼→재검사→진입) → 증거: 핵심 함수 전문
- [ ] Step 3: import-smoke → 증거: `PYTHONPATH=. uv run python -c "import dashboard.onboarding"` 에러 0
- [ ] Step 4: quirk 등록 안전성 검증 → 증거: 폼이 company_quirks.yaml에 append 후 `load_company_quirks`로 재로드되고 mojibake 0 (임시 복사본으로 검증, 실파일 비움 유지)
- [ ] Step 5(마지막): 흐름 스모크 — 한 회사로 run_gate 호출→리포트 dict 표시 경로 동작(streamlit 미실행 환경이면 run_gate 직접 호출로 대체 증거)
      증거: `PYTHONPATH=. uv run python -c "from src.normalize.onboarding_gate import run_gate; r=run_gate('<corp>','<year>'); print(list(r.keys()))"` 출력

## 5. 금지 사항 (1건 위반 시 전체 실패)
- 하드코딩: corp_code·연도·계정명을 코드에 박지 말 것(입력·데이터).
- .env/시크릿/API키 출력·커밋·로그 금지. API 미설정 시 안내만(크래시 금지).
- company_quirks.yaml 등록 시 mojibake 유발 금지(UTF-8, 검증). canonical_accounts.yaml(11k)은 이 UI에서 건드리지 말 것(quirk만 등록 — 일반패턴 승격은 별도 스캐너).
- 테스트 약화 금지. 범위 밖 수정 금지: dashboard/onboarding.py(신규)·필요한 dashboard/app.py 라우팅 최소 추가만. src/normalize/·config 로직 변경 금지(run_gate·load_company_quirks 호출만).
- run_gate·홀리스틱 프롬프트 로직 재구현 금지(호출만).

## 6. 최종 검증
- import-smoke(Step 3) 에러 0 · quirk append 안전(Step 4) · run_gate 호출 동작(Step 5)
- mojibake 0 · API 미설정 graceful

## 7. 완료 보고 양식
STATUS: DONE | DONE_WITH_CONCERNS | NEEDS_CONTEXT | BLOCKED
체크리스트: 항목별 [x]/[ ] + 증거 원문(명령+출력)
변경 파일: 경로 목록(신규/수정 구분)
최종 검증 결과: §6 출력 원문
미완·우회·우려: 정직하게(없으면 "없음")
