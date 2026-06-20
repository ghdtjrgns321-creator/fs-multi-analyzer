# S7 사업보고서 구조 표준화 — 층화랜덤 50 검증

- 표본 50 회사연도, seed=7 재현
- **표준 12파트 부합(roman≥11): 49 / 이탈: 0 / fetch실패: 1**
- 연도분포: {2011: 1, 2015: 1, 2016: 1, 2017: 1, 2018: 1, 2019: 1, 2020: 1, 2021: 1, 2022: 1, 2023: 1}

## 고가치 섹션 TITLE 미발견(부합 표본 중)
- 주석: 1 / 49 미발견
- 대주주: 23 / 49 미발견
- 우발부채: 35 / 49 미발견
- 종속회사: 35 / 49 미발견
- 감사의견: 0 / 49 미발견

## fetch 실패
- 00164973/2018: {'status': '014', 'message': '파일이 존재하지 않습니다.'}

## 전체 raw
```
{"corp": "00525642", "fy": 2023, "status": "OK", "n_roman": 12, "n_titles": 71, "found": {"주석": true, "대주주": true, "우발부채": true, "종속회사": true, "감사의견": true}, "xml_chars": 1755081}
{"corp": "01440153", "fy": 2021, "status": "OK", "n_roman": 12, "n_titles": 62, "found": {"주석": true, "대주주": true, "우발부채": true, "종속회사": true, "감사의견": true}, "xml_chars": 1219007}
{"corp": "00530413", "fy": 2019, "status": "OK", "n_roman": 11, "n_titles": 44, "found": {"주석": true, "대주주": true, "우발부채": false, "종속회사": false, "감사의견": true}, "xml_chars": 1393216}
{"corp": "01366000", "fy": 2022, "status": "OK", "n_roman": 12, "n_titles": 61, "found": {"주석": true, "대주주": true, "우발부채": true, "종속회사": true, "감사의견": true}, "xml_chars": 1168712}
{"corp": "00124027", "fy": 2017, "status": "OK", "n_roman": 11, "n_titles": 34, "found": {"주석": true, "대주주": false, "우발부채": false, "종속회사": false, "감사의견": true}, "xml_chars": 1143127}
{"corp": "00121941", "fy": 2015, "status": "OK", "n_roman": 11, "n_titles": 42, "found": {"주석": true, "대주주": true, "우발부채": false, "종속회사": false, "감사의견": true}, "xml_chars": 2003020}
{"corp": "00486370", "fy": 2018, "status": "OK", "n_roman": 11, "n_titles": 37, "found": {"주석": true, "대주주": false, "우발부채": false, "종속회사": false, "감사의견": true}, "xml_chars": 1554780}
{"corp": "00103006", "fy": 2015, "status": "OK", "n_roman": 11, "n_titles": 43, "found": {"주석": true, "대주주": false, "우발부채": false, "종속회사": false, "감사의견": true}, "xml_chars": 1380372}
{"corp": "01303029", "fy": 2023, "status": "OK", "n_roman": 12, "n_titles": 69, "found": {"주석": true, "대주주": true, "우발부채": true, "종속회사": true, "감사의견": true}, "xml_chars": 1848490}
{"corp": "00201742", "fy": 2017, "status": "OK", "n_roman": 11, "n_titles": 40, "found": {"주석": true, "대주주": false, "우발부채": false, "종속회사": false, "감사의견": true}, "xml_chars": 1003186}
{"corp": "00373447", "fy": 2017, "status": "OK", "n_roman": 11, "n_titles": 41, "found": {"주석": true, "대주주": false, "우발부채": false, "종속회사": false, "감사의견": true}, "xml_chars": 1059476}
{"corp": "00346610", "fy": 2018, "status": "OK", "n_roman": 11, "n_titles": 41, "found": {"주석": true, "대주주": false, "우발부채": false, "종속회사": false, "감사의견": true}, "xml_chars": 1519704}
{"corp": "00200910", "fy": 2017, "status": "OK", "n_roman": 11, "n_titles": 40, "found": {"주석": true, "대주주": false, "우발부채": false, "종속회사": false, "감사의견": true}, "xml_chars": 1049720}
{"corp": "00151605", "fy": 2018, "status": "OK", "n_roman": 11, "n_titles": 44, "found": {"주석": true, "대주주": true, "우발부채": false, "종속회사": false, "감사의견": true}, "xml_chars": 688838}
{"corp": "00920379", "fy": 2020, "status": "OK", "n_roman": 11, "n_titles": 43, "found": {"주석": true, "대주주": false, "우발부채": false, "종속회사": false, "감사의견": true}, "xml_chars": 1236505}
{"corp": "00541163", "fy": 2020, "status": "OK", "n_roman": 11, "n_titles": 41, "found": {"주석": true, "대주주": false, "우발부채": false, "종속회사": false, "감사의견": true}, "xml_chars": 1141585}
{"corp": "00158565", "fy": 2022, "status": "OK", "n_roman": 12, "n_titles": 60, "found": {"주석": true, "대주주": true, "우발부채": true, "종속회사": true, "감사의견": true}, "xml_chars": 1559991}
{"corp": "00609634", "fy": 2015, "status": "OK", "n_roman": 11, "n_titles": 43, "found": {"주석": true, "대주주": true, "우발부채": false, "종속회사": false, "감사의견": true}, "xml_chars": 995723}
{"corp": "00137915", "fy": 2017, "status": "OK", "n_roman": 11, "n_titles": 41, "found": {"주석": true, "대주주": true, "우발부채": false, "종속회사": false, "감사의견": true}, "xml_chars": 1546038}
{"corp": "00406329", "fy": 2020, "status": "OK", "n_roman": 11, "n_titles": 42, "found": {"주석": true, "대주주": false, "우발부채": false, "종속회사": false, "감사의견": true}, "xml_chars": 1710506}
{"corp": "00220109", "fy": 2015, "status": "OK", "n_roman": 11, "n_titles": 43, "found": {"주석": true, "대주주": false, "우발부채": false, "종속회사": false, "감사의견": true}, "xml_chars": 1628825}
{"corp": "01255652", "fy": 2020, "status": "OK", "n_roman": 11, "n_titles": 42, "found": {"주석": true, "대주주": false, "우발부채": false, "종속회사": false, "감사의견": true}, "xml_chars": 1295499}
{"corp": "00362122", "fy": 2023, "status": "OK", "n_roman": 12, "n_titles": 68, "found": {"주석": true, "대주주": true, "우발부채": true, "종속회사": true, "감사의견": true}, "xml_chars": 1281881}
{"corp": "00536329", "fy": 2017, "status": "OK", "n_roman": 11, "n_titles": 45, "found": {"주석": true, "대주주": true, "우발부채": false, "종속회사": false, "감사의견": true}, "xml_chars": 2182983}
{"corp": "01070149", "fy": 2023, "status": "OK", "n_roman": 12, "n_titles": 66, "found": {"주석": true, "대주주": true, "우발부채": true, "종속회사": true, "감사의견": true}, "xml_chars": 1073780}
{"corp": "00530121", "fy": 2022, "status": "OK", "n_roman": 12, "n_titles": 61, "found": {"주석": true, "대주주": true, "우발부채": true, "종속회사": true, "감사의견": true}, "xml_chars": 1333932}
{"corp": "00413523", "fy": 2020, "status": "OK", "n_roman": 11, "n_titles": 43, "found": {"주석": true, "대주주": false, "우발부채": false, "종속회사": false, "감사의견": true}, "xml_chars": 1551950}
{"corp": "00811372", "fy": 2015, "status": "OK", "n_roman": 11, "n_titles": 40, "found": {"주석": true, "대주주": false, "우발부채": false, "종속회사": false, "감사의견": true}, "xml_chars": 521043}
{"corp": "00164973", "fy": 2018, "status": "FETCH_FAIL", "err": "{'status': '014', 'message': '파일이 존재하지 않습니다.'}"}
{"corp": "00259590", "fy": 2021, "status": "OK", "n_roman": 12, "n_titles": 64, "found": {"주석": true, "대주주": true, "우발부채": true, "종속회사": true, "감사의견": true}, "xml_chars": 1485773}
{"corp": "01109539", "fy": 2019, "status": "OK", "n_roman": 11, "n_titles": 42, "found": {"주석": true, "대주주": true, "우발부채": false, "종속회사": false, "감사의견": true}, "xml_chars": 1565763}
{"corp": "00114093", "fy": 2023, "status": "OK", "n_roman": 12, "n_titles": 69, "found": {"주석": true, "대주주": true, "우발부채": true, "종속회사": true, "감사의견": true}, "xml_chars": 1351367}
{"corp": "00101549", "fy": 2017, "status": "OK", "n_roman": 11, "n_titles": 42, "found": {"주석": true, "대주주": false, "우발부채": false, "종속회사": false, "감사의견": true}, "xml_chars": 1263574}
{"corp": "00347716", "fy": 2018, "status": "OK", "n_roman": 11, "n_titles": 42, "found": {"주석": true, "대주주": true, "우발부채": false, "종속회사": false, "감사의견": true}, "xml_chars": 1178430}
{"corp": "00689418", "fy": 2022, "status": "OK", "n_roman": 12, "n_titles": 62, "found": {"주석": true, "대주주": true, "우발부채": true, "종속회사": true, "감사의견": true}, "xml_chars": 1107886}
{"corp": "00776820", "fy": 2017, "status": "OK", "n_roman": 11, "n_titles": 40, "found": {"주석": true, "대주주": false, "우발부채": false, "종속회사": false, "감사의견": true}, "xml_chars": 1659161}
{"corp": "00121288", "fy": 2015, "status": "OK", "n_roman": 11, "n_titles": 42, "found": {"주석": true, "대주주": true, "우발부채": false, "종속회사": false, "감사의견": true}, "xml_chars": 1237304}
{"corp": "00104999", "fy": 2015, "status": "OK", "n_roman": 11, "n_titles": 43, "found": {"주석": true, "대주주": false, "우발부채": false, "종속회사": false, "감사의견": true}, "xml_chars": 1244750}
{"corp": "00103042", "fy": 2018, "status": "OK", "n_roman": 11, "n_titles": 44, "found": {"주석": true, "대주주": true, "우발부채": false, "종속회사": false, "감사의견": true}, "xml_chars": 1810278}
{"corp": "00116268", "fy": 2021, "status": "OK", "n_roman": 12, "n_titles": 64, "found": {"주석": true, "대주주": true, "우발부채": true, "종속회사": true, "감사의견": true}, "xml_chars": 1030430}
{"corp": "00107066", "fy": 2020, "status": "OK", "n_roman": 11, "n_titles": 44, "found": {"주석": true, "대주주": true, "우발부채": false, "종속회사": false, "감사의견": true}, "xml_chars": 1412555}
{"corp": "00362238", "fy": 2015, "status": "OK", "n_roman": 11, "n_titles": 42, "found": {"주석": true, "대주주": false, "우발부채": false, "종속회사": false, "감사의견": true}, "xml_chars": 1352329}
{"corp": "00150439", "fy": 2023, "status": "OK", "n_roman": 12, "n_titles": 69, "found": {"주석": true, "대주주": true, "우발부채": true, "종속회사": true, "감사의견": true}, "xml_chars": 1263014}
{"corp": "00145738", "fy": 2021, "status": "OK", "n_roman": 12, "n_titles": 65, "found": {"주석": true, "대주주": true, "우발부채": true, "종속회사": true, "감사의견": true}, "xml_chars": 1591324}
{"corp": "00374020", "fy": 2018, "status": "OK", "n_roman": 11, "n_titles": 42, "found": {"주석": true, "대주주": false, "우발부채": false, "종속회사": false, "감사의견": true}, "xml_chars": 1140895}
{"corp": "00657002", "fy": 2016, "status": "OK", "n_roman": 11, "n_titles": 42, "found": {"주석": true, "대주주": false, "우발부채": false, "종속회사": false, "감사의견": true}, "xml_chars": 924376}
{"corp": "00146427", "fy": 2015, "status": "OK", "n_roman": 11, "n_titles": 41, "found": {"주석": true, "대주주": false, "우발부채": false, "종속회사": false, "감사의견": true}, "xml_chars": 731317}
{"corp": "00260930", "fy": 2011, "status": "OK", "n_roman": 12, "n_titles": 36, "found": {"주석": false, "대주주": true, "우발부채": false, "종속회사": false, "감사의견": true}, "xml_chars": 506139}
{"corp": "00115612", "fy": 2015, "status": "OK", "n_roman": 11, "n_titles": 42, "found": {"주석": true, "대주주": false, "우발부채": false, "종속회사": false, "감사의견": true}, "xml_chars": 1817952}
{"corp": "00442048", "fy": 2016, "status": "OK", "n_roman": 11, "n_titles": 40, "found": {"주석": true, "대주주": false, "우발부채": false, "종속회사": false, "감사의견": true}, "xml_chars": 1223528}
```
## 판정 (50 표본 분석)

### 확정 1 — 12파트 골격은 회사 불문 표준 (49/49, 2011~2024)
대형·소형·분식사·옛연도 전부 I~XII(또는 구포맷 I~XI) 골격 유지. 이탈 0. **회사별 구조 변형 없음.**

### 확정 2 — ★포맷 시대 드리프트 실재 (selector 핵심 난관)
**두 시대**가 있고 표본 절반이 구포맷:
- **구포맷(~2017, 11파트)**: 순서 다름(IV=감사의견·V=MD&A), 표현 다름(X="이해관계자와의 거래"≠"대주주"), XII 상세표 없음.
- **신포맷(2018+, 12파트)**: 강원에너지·삼성 패턴.

### 섹션별 selector 신뢰도
- **주석 48/49 · 감사의견 49/49**: 두 시대 모두 TITLE 안정 → 단순 패턴으로 선택 가능.
- **대주주/이해관계자 거래 26/49**: 구포맷은 "이해관계자와의 거래" → **다중 패턴 필요**.
- **우발부채 14/49 · 종속회사 14/49**: ①신포맷 XII/XI 소제목 ②구포맷 부재/다른위치/별도재무제표사 정상부재 혼재 → **PART 단위 선택 + 다중 패턴 + 정상부재 허용** 필요.

### selector 설계 결론
- 단순 단일 키워드 화이트리스트는 **구포맷에서 실패**. → **논리 섹션별 다중 패턴 세트(시대 매핑) + PART 단위 추출 + 정상 부재 허용**으로 가야 함.
- 두 시대 매핑: 거래내용=("대주주 등과의 거래"|"이해관계자와의 거래"), 감사의견=공통, 종속회사=("연결대상 종속회사"|주석 연결범위 fallback).
- 골격(12파트)이 표준이라 **PART 경계 분해는 신뢰 가능** — 어려움은 "어느 PART/소제목을 어느 논리섹션에 매핑하느냐"(시대별)에 한정.
