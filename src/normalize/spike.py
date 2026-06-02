"""L1 normalization spike runner."""

from __future__ import annotations

from pathlib import Path

from src.db.normalized import write_normalized_financials
from src.normalize.pipeline import normalize_company_year
from src.normalize.report import build_report

DEFAULT_CORP_CODE = "00126380"
DEFAULT_YEARS = (2022, 2023, 2024, 2025)


def normalize_company_years(
    corp_code: str = DEFAULT_CORP_CODE,
    years: tuple[int, ...] = DEFAULT_YEARS,
    data_dir: Path | None = None,
) -> dict[str, object]:
    """Normalize raw CFS/OFS files and persist each year to DuckDB."""

    frames = []
    db_paths = {}
    for year in years:
        frame = normalize_company_year(corp_code, year, data_dir=data_dir)
        db_paths[str(year)] = str(write_normalized_financials(frame, corp_code, year, data_dir))
        frames.append(frame)

    return {"corp_code": corp_code, "db_paths": db_paths, "report": build_report(frames)}


def main() -> None:
    result = normalize_company_years()
    print(result["corp_code"])
    print(result["db_paths"])


if __name__ == "__main__":
    main()
