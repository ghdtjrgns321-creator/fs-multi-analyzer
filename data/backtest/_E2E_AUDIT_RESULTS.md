# E2E 충실도 감사 결과 — DART 원본 통독 ↔ Phase1이 LLM에 넘기는 material

> 2026-06-16. 6사 층화(차원별 1사) 실측. 잣대: 분식 탐지가 아니라 **DART가 주는 유용정보를
> Phase1이 Phase2 LLM에 빠짐없이/왜곡없이 넘기는가**. 정상 회사로 측정.

## 표본 (수집·정규화 완료)

| 차원 | 회사 | corp_code | 수집연도 | target | review_queue | 비고 |
|------|------|-----------|----------|--------|--------------|------|
| 대형 다각화 | 삼성전자 | 00126380 | 2024,2023 | 2024 | 39 | 주석 16카테고리 |
| 금융/지주 | KB금융 | 00688996 | 2024,2023 | 2024 | 18 | 계정 ~40% 미매핑 |
| 자본거래 多 | 카카오 | 00258801 | 2024,2023 | 2024 | 46 | event 6유형 43건 |
| 정정본 | 두산 | 00117212 | 2024,2023 | 2024 | 60 | 재작성 2017-20 |
| 구포맷(11PART) | LG화학 | 00356361 | 2017,2016 | 2017 | 58 | 원문 11파트 |
| 소형 단순 | 진양폴리우레탄 | 00160375 | 2024,2023 | 2024 | 2 | OFS 단일실체 |

## 한눈에 (쉬운 말)

샘플 6곳을 실제 파이프라인에 태우고, DART 원본(재무제표·주석·사업보고서 원문·정정·주요사항)을
직접 다 읽어 "Phase1이 LLM에게 건네는 묶음"과 대조했다. **큰 구멍 4개**를 찾았다.

1. **연도 하드코딩 버그(수정 완료)** — 올해(2025) 사업보고서를 아직 안 낸 회사는 분석 결과가
   통째로 **빈값**이 돼 LLM에 아무것도 안 넘어갔다. 6곳 중 3곳에서 재현. 코드가 분석연도를
   "2025"로 박아둔 탓. 데이터에서 회사별 최신연도를 읽도록 고쳤고, 기존 테스트 243개 전부 통과.
2. **사업보고서 원문이 LLM까지 0건** — 원문(소송·우발·대주주거래·연결범위 등)은 잘 받아오는데,
   거기서 검토할 부분을 골라내는 단계(온보딩 선별)를 안 돌려서 **LLM엔 한 줄도 안 간다**.
3. **정정공시(재작성) 이력이 LLM까지 안 감** — 재작성 연도는 화면 경고배지로만 뜨고,
   LLM이 받는 묶음엔 "이 회사가 과거를 다시 작성했다"는 출처 정보가 빠져 있다.
4. **자본거래 '조건'이 빠진 채로 감** — "언제 전환사채를 냈다"는 가지만, "전환가·리픽싱·발행액·
   자금용도"는 받아만 놓고 LLM엔 안 넘긴다. 이게 원래 주요사항 수집의 핵심 가치였다.

나머지는 대체로 충실히 전달된다(재무 라인·주석 섹션·자본거래 타임라인·미매핑 게시).

## 구조적 갭 (전 회사 공통)

### G1. [수정완료] target_year 리터럴 고정 → 빈 material
- **증상**: `build_company_report(corp)` 호출 시 분석 target이 항상 `max([2022,2023,2024,2025])=2025`
  로 고정. 정규화 최신연도가 2024인 회사(2025 미제출)는 review_queue·account_series·snapshot이
  전부 빈값 → numeric/flow/change 관점에 **아무것도 안 넘어감**.
- **재현**: 6사 중 카카오·KB·진양 = queue 0 (2025 데이터 없음). 삼성·두산·LG는 corpus에 2025가
  있어 통과 → 표본 다양성이 아니었으면 못 봤을 갭.
- **근인**: `src/report/company_report.py:25,37` `DEFAULT_YEARS`/`max()` 리터럴. CLAUDE.md §3가
  명시 금지한 "연도 리터럴로 계산 구동" 패턴.
- **수정**: 윈도우·target을 데이터에서 도출(`_available_norm_years`·`_present_years`, frame 실재
  최신연도). years 명시 호출(백테스트 run_years)은 그대로 존중 → target=max(present). 수정 후
  카카오 46·KB 18·진양 2로 복구. **무회귀: pytest 243 passed(+1 신규)·1 xfailed, 분식 target
  2019 불변(두산에너빌리티·디아이동일 큐 69/42 동일)**. 회귀 테스트 박음
  (`test_company_report_target_year_follows_data_not_literal`).

### G2. [수정완료] S7 사업보고서 원문 검토청크 = 0 (전 6사)
- **증상**: note_material.report_review_chunks = 0 (전 회사). 원문(12/11 PART)은 `report_doc`로
  수집·`extract_parts` 파싱 정상(LG 구포맷 11파트도 깔끔 추출 확인)인데, LLM엔 청크 0건.
- **근인**: 청크는 온보딩 GPT 선별(`run_review_chunk_selection`)이 `company_quirks.content_chunks`
  에 persist해야 채워지는데 그 단계가 어느 회사에도 실행 안 됨. **그런데 S7 확정설계
  (`_HANDOFF_S7.md` "핵심 결정")는 B안(온보딩 LLM)이 본체, 키워드 baseline이 콜드스타트
  fallback** — 그 fallback이 note_material에 **배선 안 됨**(GPT 선별만 읽음).
- **수정**: `baseline_chunks_from_parts`(report_review_keywords.yaml event_signals로 원문 PART에서
  결정론 청크 추출, null_marker '해당사항 없음' 제외) + note_material에 fallback 배선(GPT 선별
  있으면 그것, 없으면 baseline). 실데이터: 삼성 8·두산 11·LG 7·진양 6 청크 도달. 발췌 실신호 확인
  (삼성 공정위 과징금 101,217·레인보우로보틱스 콜옵션 2674억·SEA 채무보증). RED→GREEN 회귀테스트 2.

### G3. [수정완료] S9 정정공시 이력 → LLM material 미도달
- **증상**: corrections.json은 재작성 연도 정확 포착(두산 사업보고서 2017-2020 재작성=True).
  그러나 change_material엔 정정공시 출처가 없음. restatement_signals(13건)는 **FS 비교표시 괴리
  신호**(결정론)이지 정정공시 아님.
- **근인**: S9는 UI 배지(`render_restatement_badge`)에만 배선. materials.py는 corrections 미독.
- **수정**: `_correction_history(report)`(load_corrections → {year,report_kind,restated,reason}
  compact, 재작성·과거연도 우선 정렬·[:20]) + change_material에 `restatement_history` 주입. 실데이터:
  두산 11건 도달(연결재무제표 재작성 사유 포함). RED→GREEN 회귀테스트. change 관점이 이제 "FS
  소급흔적"과 "정정공시로 재작성됨(출처)"을 함께 받음.

### G5. [수정완료] OFS 전용(단일실체) 회사 미매핑 누락
- **증상**: `_top_unmapped_material_accounts`가 `fs_div=="CFS"` 하드코딩 → 연결 없는 단일실체(별도만)
  회사는 unmapped "기타 중요 계정"이 통째 누락(진양폴리우레탄=0). 설계원칙("unmapped는 분석 제외가
  아니라 기타 중요 계정으로 게시")과 §3(fs_div 리터럴)을 동시에 위반.
- **발견 경로**: 소형 차원(진양 OFS 전용) + code-reviewer 교차 지적.
- **수정**: `_primary_fs_div(frame, target_year)`(CFS 있으면 CFS, 없으면 OFS) 재사용. 수정 후 진양
  unmapped 5건 도달. RED→GREEN 회귀테스트(`test_unmapped_material_surfaces_for_ofs_only_company`).
- **부수 관찰**: 진양·KB 공통으로 unmapped 상위가 SCE 라벨(자본총계·기초자본)로 오염 — SCE 행이
  unmapped_extension_account로 분류돼 "기타 중요 계정"에 혼입(별개 기존 분류 노이즈, 백로그).

### G4. [수정완료] S10 event 조건(terms) 누락 + 30건 cap
- **증상**: routed_timeline은 `{type, date, source}`만 전달. events.json엔 전환사채 19필드
  (bd_fta 발행총액·cv_prc 전환가·리픽싱 하한·fdpp_* 자금용도) 수집돼 있으나 material 미전달.
- **재현**: 카카오 전환사채 레코드 자금용도 등 수집 확인 ↔ 타임라인엔 "전환사채발행 on 20160411"만.
- **수정**: `TERM_LABELS`(DART 필드코드 24종→사람 라벨: 발행총액·전환가·리픽싱·자금용도·합병비율 등)
  + `_event_terms`로 present·non-empty만 compact 추출 → routed_timeline에 `terms` 주입. 실데이터:
  카카오 전환사채 terms={발행총액 2500억·전환가 120,014·자금용도_기타 2500억} 도달.
- **cap**: `_routed_events`가 `[:30]` 초과 시 `{_truncated:N}` sentinel 추가(silent cap 제거, §9).
  RED→GREEN 회귀테스트(기존 "terms 미포함" 단정 테스트를 새 설계로 갱신).

## 차원별 (충실히 전달된 것 / 갭)

| 차원 | 충실 전달 ✅ | 갭 |
|------|-------------|-----|
| 대형(삼성) | 주석 16카테고리 수집→material 16섹션·큐 39 | 원문 청크 0(G2) |
| 금융(KB) | 미매핑 131조 투자금융자산 "기타 중요 계정"으로 flow_material 게시(버림 0) | ★[진단정정] "COA 제조업중심 ~40% 미매핑"은 부정확. 102 미매핑 실체=무표준코드 36(35%,온보딩 alias quirk 영역·미실행)+SCE노이즈 57(56%,수정완료)+진짜 보험계정 9(9%,COA확장). 2020-22 raw header-only(과거 수집잔재) |
| 자본거래(카카오) | event 타임라인 flow/change 도달(유증·CB·교환사채·분할·합병·해외상장) | terms 누락(G4) |
| 정정(두산) | 재작성 4연도 포착·FS restatement 신호 13건 | 정정공시 출처 LLM 미도달(G3) |
| 구포맷(LG) | 11 PART 추출 정상(IV=감사의견·X=이해관계자, XII 없음) | 청크 0(G2)·타이틀 "I. I." 중복(cosmetic) |
| 소형(진양) | OFS 단일실체 정규화·큐 2(정상)·주석 10 — baseline 충실 | unmapped CFS하드코딩으로 누락(G5,수정완료) |

## 종합 — Phase1이 구조적으로 빠뜨리는 정보 차원

1. **(수정완료) 분석연도 미적응** — G1. 최신연도≠2025 회사 전멸. → 데이터 구동으로 수정.
2. **(수정완료) OFS 전용사 미매핑 누락** — G5. fs_div 하드코딩. → _primary_fs_div로 수정.
3. **(수정완료) 원문 narrative** — G2. 키워드 baseline fallback 배선(GPT 선별 없어도 0 방지).
4. **(수정완료) 정정공시 출처** — G3. change_material에 restatement_history 주입.
5. **(수정완료) 자본거래 조건** — G4. timeline에 terms(발행총액·전환가·자금용도) + cap sentinel.
6. **(수정완료) SCE 라벨 노이즈** — unmapped material에서 sj_div='SCE' 제외(기존 AGENDA_DD_SCE2D
   결정을 unmapped 경로에 마저 적용). KB SCE 57→0·진양 SCE 제거, 진짜계정 보존. SCE 빠지니 KB
   진짜 금융 미매핑(투자금융자산·이자비용·보험손익) 상위 노출.
7. **금융 계정체계(축소)** — KB 미매핑 실체는 무표준코드(온보딩 quirk 영역)+진짜 보험계정 9건뿐.
   온보딩/quirk 실행(company_quirks 등록 1개사뿐)·보험 canonical 9 추가가 보완점. (백로그)
8. **(수정완료) 주석 발췌 선택 갭(G6)** — note_material 금액블록 우선+파일 fallback. 갭 39%→0.7%(59→1).

> 2026-06-16 갱신: G1·G5(연도·fs_div 리터럴)는 70차 수정, G2·G3·G4(원문·정정·event 배선)는 72차
> 수정 완료. 남은 백로그: 금융 COA·SCE 라벨 노이즈. **숫자/의미 정합(71차)은 별도 진행 중.**

## 수정 백로그 (G1 외)

- **G2(원문 청크)**: 수집 파이프라인에 온보딩 청크선별 자동 실행 배선 또는 운영 절차 명문화.
- **G3(정정 출처)**: materials.py change_material에 corrections(restated_years·정정사유 compact) 주입.
- **G4(event terms)**: routed_timeline에 핵심 terms(발행액·전환가·자금용도) compact 포함, cap 시 로그.
- **금융 COA**: 미매핑 비중 큰 업종(금융/지주) unmapped material 우선순위 상향 검토.

## §숫자 정합 (71차 — 금액 1:1 재현·소실 funnel)

> 70차의 "도달했나"(구조) 검증을 넘어, **원본 금액 = 정규화 금액**을 account_id(IFRS 개념·
> 신구택소노미) 기반으로 6사 전수 대조. 하니스: `_e2e_reconcile.py` → `_e2e_reconcile.json`.

| 회사 | primary | 핵심계정 6 | 결과 | raw행→norm행 | 소실 |
|------|---------|-----------|------|--------------|------|
| 삼성전자 | CFS | 6/6 match | 자산514조·매출300조·당기순이익34.4조 정확 | 213→173 | 0 |
| KB금융 | CFS | 4 match·2 n/a | 자산758조·자본59.8조 정확. 매출/영업이익 n/a=**금융업 개념부재(정상)** | 390→250 | 0 |
| 카카오 | CFS | 6/6 match | 당기순이익 **-161,870,567,171 부호까지 정확** | 231→221 | 0 |
| 두산 | CFS | 6/6 match | 자산30조·매출18조 정확 | 360→270 | 0 |
| LG화학(2017) | CFS | 6/6 match | 구포맷 `ifrs_` 택소노미 자산25조·매출25.6조 정확 | 184→169 | 0 |
| 진양폴리우레탄 | OFS | 6/6 match | OFS 단일실체 자산574억·매출540억 정확 | 90→87 | 0 |

- **미스매치 0(6사 전수)**: raw finstate 당기금액과 정규화 amount가 round 후 **정확 일치**(부호 보존).
- **소실 0(6사 전수)**: raw 본표(BS/IS/CIS/CF) 고유계정이 account_id 또는 label로 normalized에 전부
  출현. raw행→norm행 격차(213→173 등)는 **SCE member 다중행·중복의 정상 collapse**이지 소실 아님.
- KB 2건 n/a는 보험/은행 지주라 IS에 매출액(ifrs-full_Revenue)·영업이익(dart_OperatingIncomeLoss)
  개념 자체가 없음(보험수익·보험서비스결과 구조) — 누락이 아니라 업종 특성.

## §의미 정합 (71차 — 주석 발췌 충실도·큐 실신호)

### 주석 발췌 ↔ 원본 (151 섹션 = 6사×2 div)
- **실질 발췌 25(17%)**: 발췌에 금액 포함. 원본과 **정확 일치**(삼성 매출채권 43,650,714,000,000·
  유동/비유동/미수금 원본 verbatim) = 충실.
- **★미surface 갭 59(39%) — G6 [수정완료]**: 원본 주석 파일엔 금액이 있는데(삼성 단기차입금 33개·
  사채 25개·장기충당부채 36개) 발췌가 헤더/마커 블록(loc:0 "재무제표 주요 주석 조회", loc:1
  "[문장영역]")을 집어 **실질 금액이 LLM에 0건**. 주석 발췌 선택 로직 갭.
  - **수정(방식B 격리)**: note_material에서만 ① 금액(쉼표묶음 `\d{1,3}(,\d{3}){2,}`) 보유 섹션 우선
    정렬 ② 발췌를 첫 금액 앵커 ③ 매칭 섹션 금액無이나 노트파일엔 有면 파일에서 직접 금액발췌
    (find_account_note_sections·account_finding·테스트 3개 무변경).
  - **측정**: 미surface 갭 **59→1(≤10 PASS)**, 실질발췌 25→**83**, 원본empty **67 불변(무날조)**.
    삼성 단기차입금 13,172,504,000,000·충당부채 11,336,513,000,000 발췌 도달 확인. 잔여 1(카카오
    자본금)은 발췌 금액 1개 보유(헤더-only 아님, 경계). RED→GREEN 회귀테스트.
- **원본도 비어있음 67(44%)**: 원본 주석이 헤더뿐(KB 단기차입금/사채 = 13자, 금융지주 미공시
  카테고리). 발췌 보일러는 **충실**(surface할 내용 없음).

### review_queue 실신호 검증 (두산·삼성)
- 큐 항목은 **실 결정론 신호**: growth_divergence(두산 당기순이익 236.42)·cfs_ofs_gap(연결-별도
  격차 정량)로 subject 계정·정량 evidence 보유. **아티팩트 아님**. (score 필드 미채움=표시 갭, 정합 무관.)
- 연결그룹(삼성·두산)은 cfs_ofs_gap이 큐 다수 — 정상(종속기업 多). LLM이 정상/이상 판단(설계대로).

### 의미 정합 종합
- **숫자는 충실**(6사 핵심계정 정확·소실 0). **주석은 혼재**: 발췌된 내용은 충실하나 **선택이
  39% 헤더를 집어 실질 미전달(G6)**. 큐는 실신호.

## 검증 규율

- 6사 전수 통독(표본 1~2 일반화 안 함). 차원별 갭은 해당 차원 회사에서 확인(G1은 3사 재현).
- hollow-PASS 회피: "material 있음"이 아니라 **원본 19필드 vs 타임라인 2필드**처럼 원본 대비 구체
  누락을 적시.
- G1 수정은 RED(2025≠2024)→GREEN→무회귀(243 passed·분식 불변) 증거 기반.
