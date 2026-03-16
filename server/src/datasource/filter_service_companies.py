from __future__ import annotations

from pathlib import Path
from typing import Optional

import pandas as pd


def _infer_excel_engine(file_path: Path) -> Optional[str]:
    suffix = file_path.suffix.lower()
    if suffix == ".xls":
        return "xlrd"
    if suffix == ".xlsx":
        return "openpyxl"
    return None


DATASOURCE_DIR = Path(__file__).resolve().parent
INPUT_FILE_XLSX = DATASOURCE_DIR / "data_j.xlsx"
INPUT_FILE_XLS = DATASOURCE_DIR / "data_j.xls"
OUTPUT_FILE = DATASOURCE_DIR / "data_j_service_companies.xlsx"

COL_33_CODE = "33業種コード"
COL_33_NAME = "33業種区分"
TARGET_33_CODES = {"9050"}
TARGET_33_NAMES = {"サービス業"}


def resolve_input_file(file_path: Optional[Path | str] = None) -> Path:
    if file_path is not None:
        provided = Path(file_path)
        candidates = [provided]
        if not provided.is_absolute():
            # Also resolve relative paths from this script's directory.
            candidates.append(DATASOURCE_DIR / provided)

        for candidate in candidates:
            if candidate.exists():
                return candidate

        checked = ", ".join(str(p) for p in candidates)
        raise FileNotFoundError(f"JPX Excel file not found. Checked: {checked}")

    for candidate in (INPUT_FILE_XLSX, INPUT_FILE_XLS):
        if candidate.exists():
            return candidate

    raise FileNotFoundError(
        "JPX Excel file not found. Checked: " f"{INPUT_FILE_XLSX}, {INPUT_FILE_XLS}"
    )


def load_jpx_data(file_path: Optional[Path | str] = None) -> pd.DataFrame:
    resolved_file_path = resolve_input_file(file_path)

    if not resolved_file_path.exists():
        raise FileNotFoundError(f"JPX Excel file not found: {resolved_file_path}")

    engine = _infer_excel_engine(resolved_file_path)

    try:
        return pd.read_excel(resolved_file_path, engine=engine)
    except ImportError as exc:
        if resolved_file_path.suffix.lower() == ".xls":
            raise ImportError(
                "Reading .xls requires 'xlrd'. Install it with: pip install xlrd"
            ) from exc
        if resolved_file_path.suffix.lower() == ".xlsx":
            raise ImportError(
                "Reading .xlsx requires 'openpyxl'. Install it with: pip install openpyxl"
            ) from exc
        raise


def normalize_industry_columns(df: pd.DataFrame) -> pd.DataFrame:
    required_columns = [COL_33_CODE, COL_33_NAME]
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        raise ValueError(f"Missing required columns: {missing_columns}")

    normalized_df = df.copy()

    normalized_df[COL_33_CODE] = (
        normalized_df[COL_33_CODE]
        .astype(str)
        .str.strip()
        .str.replace(".0", "", regex=False)
        .str.zfill(4)
    )
    normalized_df[COL_33_NAME] = normalized_df[COL_33_NAME].astype(str).str.strip()

    return normalized_df


def filter_target_industries(df: pd.DataFrame) -> pd.DataFrame:
    industry_mask = df[COL_33_CODE].isin(TARGET_33_CODES) | df[COL_33_NAME].isin(
        TARGET_33_NAMES
    )
    return df.loc[industry_mask].copy()


def extract_target_industries(
    input_file: Optional[Path | str] = None,
    output_file: Path = OUTPUT_FILE,
) -> pd.DataFrame:
    df = load_jpx_data(input_file)
    normalized_df = normalize_industry_columns(df)
    filtered_df = filter_target_industries(normalized_df)

    try:
        filtered_df.to_excel(output_file, index=False, engine="openpyxl")
    except ImportError as exc:
        raise ImportError(
            "Writing .xlsx requires 'openpyxl'. Install it with: pip install openpyxl"
        ) from exc

    return filtered_df


if __name__ == "__main__":
    result_df = extract_target_industries()
    print(f"filtered rows: {len(result_df)}")
    print(f"saved to: {OUTPUT_FILE}")
