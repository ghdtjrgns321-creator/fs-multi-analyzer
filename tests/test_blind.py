"""blind 마스킹 테스트 — 백테스트 사전지식 오염 차단(관점 입력에서 회사 정체 제거)."""

from __future__ import annotations

from src.report.blind import blind_materials, company_aliases, mask_text


def test_mask_target_company_name():
    # 대상 회사명은 어떤 표기로 나와도 같은 토큰으로 — 표기 차이로 정체가 새면 안 된다.
    aliases = company_aliases({"company_name": "아스트", "corp_code": "00409681"})
    masked = mask_text("주식회사아스트는 2020년에 아스트 브랜드로", aliases)
    assert "아스트" not in masked
    assert masked.count("[대상회사]") == 2


def test_mask_other_company_forms():
    # 계열사·거래상대는 회사형 표기로 등장한다 — 조합만으로 모회사가 특정되므로 함께 가린다.
    masked = mask_text("연결대상 종속회사로 '(주)에이에스티지', ㈜카프에어로가 있다", [])
    assert "에이에스티지" not in masked
    assert "카프에어로" not in masked
    assert "[회사1]" in masked and "[회사2]" in masked


def test_same_company_gets_same_token():
    masked = mask_text("(주)오르비텍 지분취득. 이후 (주)오르비텍 지분 매각", [])
    assert masked.count("[회사1]") == 2
    assert "[회사2]" not in masked


def test_identity_fields_masked_by_key():
    # 동종사 이름처럼 회사형 표기가 없는 값은 필드명으로 판별해 가린다.
    material = {
        "company_name": "아스트",
        "benchmark": {
            "target_company": "아스트",
            "target_corp_code": "00409681",
            "peers": [{"company_name": "한국항공우주산업", "value": 3.1}],
        },
    }
    out = blind_materials({"industry": material}, {"company_name": "아스트"})["industry"]
    assert out["company_name"] == "[대상회사]"
    assert out["benchmark"]["target_company"] == "[대상회사]"
    assert out["benchmark"]["target_corp_code"] == "[대상회사]"
    assert out["benchmark"]["peers"][0]["company_name"] == "[동종사]"
    assert out["benchmark"]["peers"][0]["value"] == 3.1  # 숫자는 불변


def test_numbers_and_account_names_unchanged():
    # 마스킹이 분석 재료를 훼손하면 실험 자체가 무의미하다 — 계정·금액은 그대로.
    material = {"rows": [{"series_key": "CFS:재고자산", "value": 168532992835}]}
    out = blind_materials({"numeric": material}, {"company_name": "아스트"})["numeric"]
    assert out["rows"][0] == {"series_key": "CFS:재고자산", "value": 168532992835}


def test_url_and_domain_masked():
    masked = mask_text("문의는 www.astk.co.kr 참조", [])
    assert "astk" not in masked


def test_bare_name_masked_with_same_token():
    # 같은 문서가 '(주)오르비텍'과 '오르비텍'을 섞어 쓴다(실측) — 접두어 없는 맨 이름도 가린다.
    masked = mask_text("(주)오르비텍 지분취득 후 오르비텍 주식 처분", [])
    assert "오르비텍" not in masked
    assert masked.count("[회사1]") == 2


def test_profile_identity_fields_masked():
    # 프로필 원본이 그대로 실리는 경로가 있다(실측: 종목코드·법인번호·대표자·영문명).
    material = {"profile": {"stock_code": "067390", "ceo_nm": "홍길동", "corp_name_eng": "AST Inc."}}
    out = blind_materials({"external": material}, {"company_name": "아스트"})["external"]
    assert out["profile"] == {
        "stock_code": "[대상회사]",
        "ceo_nm": "[대상회사]",
        "corp_name_eng": "[대상회사]",
    }
