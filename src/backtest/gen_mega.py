"""대규모 검증셋(mega) 생성기.

기존 분식(튜닝·홀드아웃·랜덤) + 신규 분식 5건 + DART 상장사 랜덤추출 정상 ~150
→ known_cases_mega.json. 엔진 동결 검증용. 회사는 결과 보기 전에 고정한다.
"""

from __future__ import annotations

import json
import random
from pathlib import Path

import OpenDartReader

from config.settings import settings

BASE = Path("data/backtest")
PRIOR = ["known_cases.json", "known_cases_holdout.json", "known_cases_random.json"]
N_RANDOM_CLEAN = 150
SEED = 20260605

# 신규 분식 5건(서브에이전트 리서치 + 출처 2+ 교차확인, 유형 다양)
NEW_FRAUD = [
    {
        "company": "웰바이오텍",
        "stock_code": "010600",
        "fraud_year_start": 2019,
        "fraud_year_end": 2022,
        "accounts": ["매출", "매출원가", "매출채권", "재고자산"],
        "fraud_type": "가공매출",
        "confirmed": "증선위 검찰고발·과징금(2025.10)",
    },
    {
        "company": "에스엘",
        "stock_code": "005850",
        "fraud_year_start": 2018,
        "fraud_year_end": 2018,
        "accounts": ["영업이익", "매출원가", "재고자산"],
        "fraud_type": "영업이익 과대(원가조정)",
        "confirmed": "증선위 과징금 17.8억·검찰고발(2020)",
    },
    {
        "company": "이렘",
        "stock_code": "009730",
        "fraud_year_start": 2018,
        "fraud_year_end": 2020,
        "accounts": ["관계기업투자", "당기순이익", "대손충당금"],
        "fraud_type": "손상미인식(관계기업투자 과대)",
        "confirmed": "증선위 과징금 9.5억·감사인지정(2024)",
    },
    {
        "company": "더테크놀로지",
        "stock_code": "043090",
        "fraud_year_start": 2021,
        "fraud_year_end": 2022,
        "accounts": ["매출", "매출원가", "매출채권"],
        "fraud_type": "가공매출",
        "confirmed": "증선위 과징금·검찰통보(2026)",
    },
    {
        "company": "한창",
        "stock_code": "005110",
        "fraud_year_start": 2021,
        "fraud_year_end": 2022,
        "accounts": ["매출", "매출원가"],
        "fraud_type": "총액인식 매출 과대",
        "confirmed": "증선위 과징금·검찰고발(2026)",
    },
]

# 회계구조가 다른 경계 테스트(스코프 한계 확인용) — 명시 포함
BOUNDARY_CLEAN = {
    "KB금융": "105560",
    "신한지주": "055550",
    "삼성생명": "032830",
    "SK(지주)": "034730",
    "삼성엔지니어링": "028050",
    "삼성중공업": "010140",
    "ESR켄달스퀘어리츠": "365550",
    "맥쿼리인프라": "088980",
}


def _prior_fraud_and_used() -> tuple[list[dict], set[str]]:
    fraud, used = [], set()
    for fn in PRIOR:
        path = BASE / fn
        if not path.exists():
            continue
        for case in json.loads(path.read_text(encoding="utf-8"))["cases"]:
            sc = str(case.get("stock_code") or "")
            if sc:
                used.add(sc)
            if case.get("label") == "positive":
                fraud.append(case)
    return fraud, used


def _resolve(dart: OpenDartReader, stock: str) -> str | None:
    df = dart.corp_codes
    hit = df[df["stock_code"].astype(str).str.strip() == stock]
    return str(hit.iloc[0]["corp_code"]) if not hit.empty else None


def _clean_entry(dart: OpenDartReader, stock: str, name: str | None = None) -> dict | None:
    cc = _resolve(dart, stock)
    if not cc:
        return None
    nm = name or str(
        dart.corp_codes.loc[
            dart.corp_codes["stock_code"].astype(str).str.strip() == stock, "corp_name"
        ].iloc[0]
    )
    return {
        "company": nm,
        "corp_code": cc,
        "stock_code": stock,
        "market": "",
        "fraud_year_start": None,
        "fraud_year_end": None,
        "run_years": [2020, 2021, 2022, 2023],
        "accounts": [],
        "fraud_type": None,
        "fs_detectable": False,
        "confirmed": "정상",
        "label": "clean",
        "runnable": True,
        "confidence": "high",
        "sources": [],
        "notes": "mega 랜덤/경계 정상",
    }


def build() -> None:
    dart = OpenDartReader(settings.dart_api_key)
    prior_fraud, used = _prior_fraud_and_used()

    new_fraud = []
    for f in NEW_FRAUD:
        cc = _resolve(dart, f["stock_code"])
        used.add(f["stock_code"])
        new_fraud.append(
            {
                **f,
                "corp_code": cc,
                "market": "",
                "fs_detectable": True,
                "label": "positive",
                "runnable": True,
                "confidence": "high",
                # build_labels.check_dart가 run_years로 가용성을 확인하므로 분식 윈도우를 채운다
                "run_years": list(
                    range(max(2015, f["fraud_year_start"] - 2), f["fraud_year_end"] + 1)
                ),
                "sources": [],
                "notes": "mega 신규 분식",
            }
        )

    cases = prior_fraud + new_fraud

    # 경계 케이스
    for nm, sc in BOUNDARY_CLEAN.items():
        if sc in used:
            continue
        e = _clean_entry(dart, sc, nm)
        if e:
            e["notes"] = "mega 경계(회계구조 상이)"
            cases.append(e)
            used.add(sc)

    # 랜덤 상장사 추출(보통주 위주: 종목코드 끝 0)
    df = dart.corp_codes
    listed = df[df["stock_code"].astype(str).str.strip().str.len() == 6]
    pool = [
        s
        for s in listed["stock_code"].astype(str).str.strip().tolist()
        if s.endswith("0") and s not in used
    ]
    random.seed(SEED)
    random.shuffle(pool)
    added = 0
    for sc in pool:
        if added >= N_RANDOM_CLEAN:
            break
        e = _clean_entry(dart, sc)
        if e:
            cases.append(e)
            used.add(sc)
            added += 1

    payload = {
        "_meta": {
            "purpose": (
                "대규모 검증(mega). 분식 16(유형 다양) + 경계(금융·REIT·지주) "
                "+ 랜덤 상장사 150. 엔진 동결. Stage1 결론(발굴기지 판별기 아님)"
                "·거짓양성·스코프·찐빠를 대표본으로 확인."
            ),
            "commitment": (
                f"랜덤 seed={SEED} 고정, 결과 보기 전 회사 확정. "
                "엔진·채점·임계 변경 금지."
            ),
        },
        "cases": cases,
    }
    out = BASE / "known_cases_mega.json"
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    n_pos = sum(1 for c in cases if c["label"] == "positive")
    print(f"mega cases: {len(cases)} (분식 {n_pos}, 정상 {len(cases) - n_pos}) → {out}")


if __name__ == "__main__":
    build()
