from pathlib import Path

import pandas as pd

from src.collect.storage import write_frame, write_json, year_dir


def test_year_dir_uses_company_year_raw_path(tmp_path: Path) -> None:
    path = year_dir(tmp_path, "00126380", 2024)

    assert path == tmp_path / "00126380" / "2024" / "raw"
    assert path.exists()


def test_write_frame_persists_csv_and_json(tmp_path: Path) -> None:
    frame = pd.DataFrame([{"account_nm": "자산총계", "thstrm_amount": "100"}])

    write_frame(frame, tmp_path / "finstate_all_CFS")

    assert (tmp_path / "finstate_all_CFS.csv").exists()
    assert (tmp_path / "finstate_all_CFS.json").exists()


def test_write_json_persists_utf8(tmp_path: Path) -> None:
    path = tmp_path / "summary.json"

    write_json({"account_nm": "매출채권"}, path)

    assert "매출채권" in path.read_text(encoding="utf-8")
