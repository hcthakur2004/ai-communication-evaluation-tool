import os
from typing import List, Optional, Dict
import pandas as pd

# Expected columns (case-insensitive, flexible names)
COLUMN_ALIASES: Dict[str, List[str]] = {
    "criterion": ["criterion", "criteria", "name", "title"],
    "description": ["description", "desc", "detail", "rubric_description"],
    "keywords": ["keywords", "keys", "phrases", "terms"],
    "weight": ["weight", "score_weight", "importance", "priority"],
    "min_words": ["min_words", "minword", "min", "minlength"],
    "max_words": ["max_words", "maxword", "max", "maxlength"],
}


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    col_map = {}
    lower_cols = {c.lower().strip(): c for c in df.columns}
    for target, aliases in COLUMN_ALIASES.items():
        for alias in aliases:
            if alias in lower_cols:
                col_map[lower_cols[alias]] = target
                break
    # Keep unknown columns as-is
    df = df.rename(columns=col_map)
    return df


def _clean_keywords(val: Optional[str]) -> List[str]:
    if pd.isna(val):
        return []
    if not isinstance(val, str):
        val = str(val)
    # Split by comma and strip
    return [kw.strip().lower() for kw in val.split(",") if kw and kw.strip()]


def load_rubric(excel_path: str) -> pd.DataFrame:
    """Load rubric from Excel file. Supports first sheet by default.

    Returns a DataFrame with normalized columns: criterion, description, keywords, weight, min_words, max_words
    """
    if not os.path.exists(excel_path):
        raise FileNotFoundError(f"Rubric Excel not found at: {excel_path}")

    # Read first sheet
    df = pd.read_excel(excel_path, engine="openpyxl")
    df = _normalize_columns(df)

    # Required columns
    if "criterion" not in df.columns:
        # Try to construct criterion from description if missing
        if "description" in df.columns:
            df["criterion"] = df["description"].astype(str).str.slice(0, 40)
        else:
            df["criterion"] = [f"Criterion {i+1}" for i in range(len(df))]

    if "description" not in df.columns:
        df["description"] = df["criterion"].astype(str)

    # Optional columns defaults
    if "keywords" not in df.columns:
        df["keywords"] = ""
    if "weight" not in df.columns:
        # Default equal weights
        df["weight"] = 1.0
    if "min_words" not in df.columns:
        df["min_words"] = pd.NA
    if "max_words" not in df.columns:
        df["max_words"] = pd.NA

    # Clean types
    df["criterion"] = df["criterion"].astype(str)
    df["description"] = df["description"].astype(str)
    df["keywords_list"] = df["keywords"].apply(_clean_keywords)

    # Ensure numeric
    df["weight"] = pd.to_numeric(df["weight"], errors="coerce").fillna(1.0)
    df["min_words"] = pd.to_numeric(df["min_words"], errors="coerce")
    df["max_words"] = pd.to_numeric(df["max_words"], errors="coerce")

    # Normalize weights to sum to 1 for overall scoring
    total_weight = df["weight"].sum()
    if total_weight == 0:
        df["norm_weight"] = 1.0 / max(len(df), 1)
    else:
        df["norm_weight"] = df["weight"] / total_weight

    return df