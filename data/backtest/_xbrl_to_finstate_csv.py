"""원본/정정 rcept XBRL → finstate_all CSV(18컬럼) 변환 + 정규화 round-trip 검증.

OpenDART finstate_all API는 최신(정정)본만 주므로, 정정 전 원본은 finstate_xml(XBRL)을 받아
우리 정규화 파이프라인 입력 형식(finstate_all_CFS/OFS.csv)으로 변환한다. presentation ELR로
sj_div(BS/IS/CIS/CF/SCE)를 매기고, ConsolidatedAndSeparate 축으로 CFS/OFS를 분리한다.

검증(round-trip): 정정 rcept를 변환→정규화한 결과가 디스크 정정본 normalized와 일치해야 신뢰.
재현: PYTHONPATH=. uv run python data/backtest/_xbrl_to_finstate_csv.py verify <corp> <fy> <정정rcept>
"""

from __future__ import annotations

import re
import sys
import tempfile
import zipfile
from pathlib import Path

import pandas as pd
from arelle import Cntlr, XbrlConst

from src.collect.opendart import DartCollector

col = DartCollector()

_GROUP_BY_HUNDREDS = {
    "2": "BS",
    "3": "IS",
    "4": "CIS",
    "5": "CF",
    "6": "SCE",
    "8": "NOTE",
    "9": "DOC",
}
_GROUP_PRIORITY = {"BS": 5, "IS": 5, "CIS": 5, "CF": 5, "SCE": 5, "NOTE": 2, "DOC": 1}
_BODY = {"BS", "IS", "CIS", "CF", "SCE"}
_SJ_NM = {
    "BS": "재무상태표",
    "IS": "손익계산서",
    "CIS": "포괄손익계산서",
    "CF": "현금흐름표",
    "SCE": "자본변동표",
}
_CSA_AXIS = "ConsolidatedAndSeparateFinancialStatementsAxis"
_PERIOD_NM = {0: "당기", 1: "전기", 2: "전전기"}

FINSTATE_COLUMNS = [
    "rcept_no",
    "reprt_code",
    "bsns_year",
    "corp_code",
    "sj_div",
    "sj_nm",
    "account_id",
    "account_nm",
    "account_detail",
    "thstrm_nm",
    "thstrm_amount",
    "frmtrm_nm",
    "frmtrm_amount",
    "bfefrmtrm_nm",
    "bfefrmtrm_amount",
    "ord",
    "currency",
    "thstrm_add_amount",
]


def _role_group(elr: str) -> str | None:
    m = re.search(r"-D(\d)\d{5}", elr)
    return _GROUP_BY_HUNDREDS.get(m.group(1)) if m else None


def _member_ko(dv: object) -> tuple[str, str]:
    """차원값(dimension value) → (member localName, 한글 라벨).

    한글 라벨이 없으면 코드(localName)를 그대로 보존한다(소실 금지). SCE 분류기가 한글 alias
    기반이라, member 코드가 아닌 DART 정정본과 동일한 한글("이익잉여금 [member]")이 필요하다.
    """
    try:
        if dv.isExplicit:  # type: ignore[attr-defined]
            ln = dv.memberQname.localName  # type: ignore[attr-defined]
            try:
                ko = dv.member.label(lang="ko")  # type: ignore[attr-defined]
            except Exception:
                ko = ""
            return (ln, ko or ln)
    except Exception:
        pass
    s = str(dv)
    return (s, s)


def resolve_sce_dimensions(
    members: list[tuple[str, str, str]],
) -> tuple[str, str, str | None]:
    """[(axis, member_localName, member_ko)] → (fs, component_detail, csa_marker_ko).

    - CSA 축(ConsolidatedAndSeparate): CFS/OFS 판정에 쓰고, 한글 마커("연결재무제표 [member]"
      /"별도재무제표 [member]")는 SCE 표 총계행(마커) account_detail로 보존한다.
    - 그 외 축(자본구성요소 등): 한글 라벨을 component_detail로 합성한다(leaf=마지막 세그먼트).

    component_detail이 비면(=CSA 외 차원 없음) 본문(BS/IS/CF) 무차원 행이거나 SCE 마커행이다.
    라우팅은 호출부가 component_detail 유무로 판단하고, SCE 마커행만 csa_marker_ko를 detail로 쓴다.
    """
    fs = "CFS"
    component_parts: list[str] = []
    csa_marker_ko: str | None = None
    for axis, member_ln, member_ko in sorted(members):
        if axis == _CSA_AXIS:
            fs = "OFS" if "Separate" in member_ln else "CFS"
            csa_marker_ko = member_ko
        else:
            component_parts.append(member_ko)
    return (fs, "|".join(component_parts), csa_marker_ko)


def _body_concept_sets(model) -> dict[str, set[str]]:
    """본문 표(sj_div)별 소속 concept localName 집합. 한 concept이 여러 표에 속할 수 있다
    (당기순이익=IS·CIS·CF·SCE). finstate_all은 그런 concept을 각 표마다 행으로 출력하므로,
    group을 하나로 고정하지 않고 멤버십 집합으로 다룬다."""
    sets: dict[str, set[str]] = {sj: set() for sj in _BODY}
    base = model.relationshipSet(XbrlConst.parentChild)
    for elr in base.linkRoleUris:
        g = _role_group(elr)
        if g not in _BODY:
            continue
        sub = model.relationshipSet(XbrlConst.parentChild, elr)
        for rel in sub.modelRelationships:
            for concept in (rel.fromModelObject, rel.toModelObject):
                if concept is not None and concept.qname is not None:
                    sets[g].add(concept.qname.localName)
    return sets


def _load_model(rcept: str):
    tmpzip = Path(tempfile.gettempdir()) / f"conv_{rcept}.zip"
    try:
        ok = col._dart.finstate_xml(rcept, save_as=str(tmpzip))
    except Exception:
        return None
    if not ok or not tmpzip.exists():
        return None
    tmp = tempfile.mkdtemp()
    with zipfile.ZipFile(tmpzip) as zf:
        zf.extractall(tmp)
    ent = list(Path(tmp).glob("*.xbrl"))
    if not ent:
        return None
    cntlr = Cntlr.Cntlr(logFileName="logToBuffer")
    model = cntlr.modelManager.load(str(ent[0]))
    if model is None or not getattr(model, "facts", None):
        cntlr.modelManager.close()
        return None
    return model


def load_label_map(corp: str, fy: int) -> dict[str, str]:
    """디스크 정정본 finstate_all CSV에서 account_id→account_nm(회사 신고 라벨).

    XBRL taxonomy 라벨("지배기업의 소유주에게 귀속되는 당기순이익")은 finstate_all의 회사신고
    라벨과 달라 label alias 매핑이 어긋난다(당기순이익에 오흡수). 라벨은 분식과 무관(금액만
    분식)하므로 정정본 회사신고 라벨을 재사용해 매핑 일치를 보장한다."""
    out: dict[str, str] = {}
    for div in ("CFS", "OFS"):
        p = Path(f"data/companies/{corp}/{fy}/raw/finstate_all_{div}.csv")
        if not p.exists() or p.stat().st_size <= 5:
            continue
        try:
            df = pd.read_csv(p, dtype=str)
        except pd.errors.EmptyDataError:  # 빈 정정본 CSV(세토피아 등)
            continue
        for aid, nm in zip(df.get("account_id", []), df.get("account_nm", []), strict=False):
            if isinstance(aid, str) and aid and aid not in out and isinstance(nm, str):
                out[aid] = nm
    return out


def xbrl_to_frames(
    rcept: str, corp: str, fy: int, label_map: dict[str, str] | None = None
) -> dict[str, pd.DataFrame] | None:
    """rcept XBRL → {'CFS': df, 'OFS': df} (finstate_all 18컬럼). 본문 5표만.

    label_map: account_id→회사신고 라벨(정정본에서 추출). 주면 taxonomy 라벨 대신 사용.
    """
    model = _load_model(rcept)
    if model is None:
        return None
    label_map = label_map or {}
    csets = _body_concept_sets(model)
    ends = sorted(
        {f.context.endDatetime for f in model.facts if f.context and f.context.endDatetime},
        reverse=True,
    )
    rank = {e: i for i, e in enumerate(ends)}

    # (fs, sj, aid, detail) -> dict(period->value, label, unit, ord)
    rows: dict[tuple, dict] = {}
    order = 0
    for f in model.facts:
        if f.concept is None or f.concept.qname is None or f.context is None:
            continue
        ln = f.concept.qname.localName
        member_sjs = [sj for sj in _BODY if ln in csets[sj]]  # 속한 모든 본문 표
        if not member_sjs:
            continue
        end = f.context.endDatetime
        if end not in rank:
            continue
        per = rank[end]
        if per > 2:
            continue
        ctx = f.context
        members = [(d.localName, *_member_ko(dv)) for d, dv in (ctx.qnameDims or {}).items()]
        fs, component_detail, csa_marker_ko = resolve_sce_dimensions(members)
        try:
            v = float(f.value)
        except (ValueError, TypeError):
            continue
        aid = f"{f.concept.qname.prefix or 'ifrs'}_{ln}"
        if aid in label_map:  # 정정본 회사신고 라벨 우선(매핑 일치 보장)
            label = label_map[aid]
        else:
            try:
                label = f.concept.label(lang="ko") or ln
            except Exception:
                label = ln
        # 자본구성요소(CSA外) 차원이 붙은 fact는 SCE 전용. BS/IS/CIS/CF 본문은 차원없는 것만
        # (finstate_all 구조). 안 그러면 SCE의 자본구성요소별 순이익이 IS에 복제돼 당기순이익 오염.
        target_sjs = [sj for sj in member_sjs if sj == "SCE"] if component_detail else member_sjs
        for sj in target_sjs:  # 당기순이익(차원없음)은 IS·CIS·CF·SCE 각 표에 행 생성
            # SCE 표 총계행(구성요소 차원 없음)은 CSA 한글 마커("연결재무제표 [member]")로 표기 →
            # 분류기가 marker로 인식(검산축). 본문(BS/IS/CF)은 무차원이므로 "-"(component_detail 빈값).
            row_detail = (
                csa_marker_ko
                if (sj == "SCE" and not component_detail and csa_marker_ko)
                else component_detail
            )
            key = (fs, sj, aid, row_detail)
            if key not in rows:
                order += 1
                rows[key] = {"label": label, "unit": str(f.unitID or "KRW"), "ord": order}
            rows[key][per] = v

    out: dict[str, pd.DataFrame] = {}
    for fs in ("CFS", "OFS"):
        records = []
        for (f_fs, sj, aid, detail), d in rows.items():
            if f_fs != fs:
                continue
            cur = "KRW" if "KRW" in d["unit"].upper() or d["unit"] in ("", "nan") else d["unit"]
            records.append(
                {
                    "rcept_no": rcept,
                    "reprt_code": "11011",
                    "bsns_year": str(fy),
                    "corp_code": corp,
                    "sj_div": sj,
                    "sj_nm": _SJ_NM[sj],
                    "account_id": aid,
                    "account_nm": d["label"],
                    "account_detail": detail or "-",
                    "thstrm_nm": _PERIOD_NM[0],
                    "thstrm_amount": _fmt(d.get(0)),
                    "frmtrm_nm": _PERIOD_NM[1],
                    "frmtrm_amount": _fmt(d.get(1)),
                    "bfefrmtrm_nm": _PERIOD_NM[2],
                    "bfefrmtrm_amount": _fmt(d.get(2)),
                    "ord": d["ord"],
                    "currency": cur,
                    "thstrm_add_amount": "",
                }
            )
        out[fs] = pd.DataFrame(records, columns=FINSTATE_COLUMNS)
    return out


def _fmt(v: float | None) -> str:
    if v is None:
        return ""
    return str(int(v)) if v == int(v) else str(v)


def verify(corp: str, fy: int, corr_rcept: str) -> None:
    """정정 rcept 변환→정규화 결과가 디스크 정정본 normalized와 일치하는지(round-trip)."""
    import duckdb

    from config.settings import settings
    from src.normalize.config import load_canonical_accounts
    from src.normalize.mapper import AccountMapper
    from src.normalize.pipeline import normalize_raw_file

    frames = xbrl_to_frames(corr_rcept, corp, fy, label_map=load_label_map(corp, fy))
    if frames is None:
        print("변환 실패")
        return
    tmpdir = Path(tempfile.mkdtemp())
    mapper = AccountMapper(load_canonical_accounts(settings.config_dir / "canonical_accounts.yaml"))
    norm_parts = []
    for fs, df in frames.items():
        if df.empty:
            continue
        p = tmpdir / f"finstate_all_{fs}.csv"
        df.to_csv(p, index=False, encoding="utf-8-sig")
        norm_parts.append(normalize_raw_file(p, fs, mapper))
    converted = pd.concat(norm_parts, ignore_index=True) if norm_parts else pd.DataFrame()

    db = Path(f"data/companies/{corp}/{fy}/analysis.duckdb")
    con = duckdb.connect(str(db), read_only=True)
    disk = con.execute(
        "SELECT canonical, fs_div, sj_div, amount FROM normalized_financials WHERE mapping_status!='unmapped'"
    ).fetchdf()
    con.close()

    # canonical+fs_div 기준 금액 대조
    conv_map = {
        (r["canonical"], r["fs_div"]): r["amount"]
        for _, r in converted[converted["mapping_status"] != "unmapped"].iterrows()
    }
    disk_map = {(r["canonical"], r["fs_div"]): r["amount"] for _, r in disk.iterrows()}
    keys = set(conv_map) | set(disk_map)
    match = miss = diff = 0
    samples = []
    import math

    def _nan(x: object) -> bool:
        return x is None or (isinstance(x, float) and math.isnan(x))

    for k in keys:
        cv = conv_map.get(k)
        dv = disk_map.get(k)
        if _nan(cv) and _nan(dv):
            match += 1  # 둘 다 값없음(SCE/CF 변동행) = 실질 동일
        elif _nan(cv) or _nan(dv):
            miss += 1
            if len(samples) < 15:
                samples.append(f"  한쪽없음 {k}: 변환={cv} 디스크={dv}")
        elif abs(cv - dv) < 1.0:
            match += 1
        else:
            diff += 1
            if len(samples) < 15:
                samples.append(f"  불일치 {k}: 변환={cv:,.0f} 디스크={dv:,.0f}")
    print(f"=== round-trip {corp} FY{fy} (정정 rcept={corr_rcept}) ===")
    print(f"canonical 키 {len(keys)} | 일치 {match} 불일치 {diff} 한쪽없음 {miss}")
    for s in samples:
        print(s)


def main() -> None:
    if len(sys.argv) >= 5 and sys.argv[1] == "verify":
        verify(sys.argv[2], int(sys.argv[3]), sys.argv[4])
    else:
        print("usage: _xbrl_to_finstate_csv.py verify <corp> <fy> <정정rcept>")


if __name__ == "__main__":
    main()
