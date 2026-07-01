"""OFS 개방 단계 검증 probe — 삼성(00126380/2024).

account_metrics_panel에 OFS 계정이 1급 series로 실리는지, 특히 삼성 누락 F
(별도 유동성장기부채)가 fs_div=OFS series로 뜨고 변화축(yoy/delta)이 살아나는지 확인.
산출물: _OFS_STAGE_SAMSUNG_PROBE.txt
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.report.company_report import build_company_report  # noqa: E402

CORP = "00126380"


def main() -> None:
    report = build_company_report(
        corp_code=CORP,
        company_provider=lambda code: {"stock_name": "삼성전자", "corp_code": code},
    )
    panel = report["account_metrics_panel"]
    target = report["target_year"]
    out: list[str] = []
    out.append(f"# OFS 개방 probe — 삼성 {CORP} (target_year={target})")

    fs_counts: dict[str, int] = {}
    for e in panel:
        fs_counts[e.get("fs_div", "")] = fs_counts.get(e.get("fs_div", ""), 0) + 1
    out.append(f"패널 계정수: 총 {len(panel)} / fs_div별 {fs_counts}")
    out.append("")

    # F: 별도(OFS) 유동성장기부채 — 계정명 변주 대비 '유동성' 포함 OFS 행 전수
    hits = [e for e in panel if e.get("fs_div") == "OFS" and "유동성" in str(e.get("account", ""))]
    out.append(f"## OFS 유동성 계열 계정 ({len(hits)}건)")
    for e in hits:
        out.append(
            f"- {e['account']} | sj={e['sj_div']} fs={e['fs_div']} | "
            f"yoy[{target}]={e['yoy_pct'].get(target)} | delta/asset={e['delta_over_assets']:.4f} | "
            f"amounts={e['amounts']}"
        )
    out.append("")

    # OFS 계정 중 변화축(yoy 비None) 상위 — F가 묻히지 않았는지 맥락
    ofs = [e for e in panel if e.get("fs_div") == "OFS"]
    ofs_yoy = [e for e in ofs if e["yoy_pct"].get(target) is not None]
    out.append(f"## OFS 계정 {len(ofs)}개 중 yoy[{target}] 산출 {len(ofs_yoy)}개")
    top = sorted(ofs_yoy, key=lambda e: abs(e["yoy_pct"][target]), reverse=True)[:15]
    for e in top:
        out.append(
            f"- {e['account']} | yoy={e['yoy_pct'][target]:.1f}% | delta/asset={e['delta_over_assets']:.4f}"
        )

    text = "\n".join(out)
    path = Path(__file__).parent / "_OFS_STAGE_SAMSUNG_PROBE.txt"
    path.write_text(text, encoding="utf-8")
    print(text)
    print(f"\n[written] {path}")

    # 판정
    f_ok = any(e["yoy_pct"].get(target) is not None or e["delta_over_assets"] > 0 for e in hits)
    has_ofs = fs_counts.get("OFS", 0) > 0
    print(
        f"\n[VERDICT] OFS 패널 포함={has_ofs} / F(유동성장기부채) 변화축 표면화={f_ok and bool(hits)}"
    )


if __name__ == "__main__":
    main()
