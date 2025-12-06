# IMPORTANT:
# This file no longer drops rows with missing values.
# Rows with partial data are preserved for ML training.

import hashlib
import os
import re
from datetime import datetime
from typing import List, Tuple

import pandas as pd


DATA_DIR = "newData"
OUTPUT_SUFFIX = "_cleaned.csv"

# Likert map (not applied, for reference)
LIKERT_MAP = {
    1: "Strongly disagree",
    2: "Disagree",
    3: "Neutral",
    4: "Agree",
    5: "Strongly agree",
    6: "Very strongly agree",
    7: "Extremely strongly agree",
}


def read_csv_safe(path: str) -> pd.DataFrame:
    for enc in ("utf-8", "latin1"):
        try:
            df = pd.read_csv(path, encoding=enc)
            break
        except UnicodeDecodeError:
            continue
    else:
        raise UnicodeDecodeError("All decoding attempts failed", b"", 0, 0, "")

    df.rename(columns=lambda c: str(c).replace("\ufeff", ""), inplace=True)
    return df


def normalize_yes_no_maybe(val: str):
    if pd.isna(val):
        return pd.NA
    s = str(val).strip()
    low = s.lower()
    if low in {"yes", "y", "true"}:
        return "Yes"
    if low in {"no", "n", "false"}:
        return "No"
    if low in {"maybe", "unsure", "not sure"}:
        return "Maybe"
    return s.strip().title() if isinstance(val, str) else val


def normalize_age(val: str):
    if pd.isna(val):
        return pd.NA
    s = str(val).strip()
    s = s.replace("–", "-").replace("—", "-").replace("to", "-").replace(" ", "")
    s_lower = s.lower()
    if s_lower in {"30-above", "above30", ">30", "30above"}:
        return "30+"
    if re.match(r"^\d{2}-\d{2}$", s):
        return s
    return s


def normalize_times(val: str):
    if pd.isna(val):
        return pd.NA
    s = str(val).strip()
    match = re.match(r"(\d{1,2})[:\.](\d{2})", s)
    if match:
        h, m = match.groups()
        return f"{int(h):02d}:{int(m):02d}"
    window = re.findall(r"(\d+)\s*to\s*(\d+)", s.lower())
    if window:
        a, b = map(int, window[0])
        return f"{(a + b) // 2}"
    if "more than 60" in s.lower():
        return "60"
    return s


def normalize_duration(val: str):
    if pd.isna(val):
        return pd.NA
    s = str(val).lower()
    rng = re.findall(r"(\d+)\s*to\s*(\d+)", s)
    if rng:
        a, b = map(int, rng[0])
        return (a + b) / 2
    if "more than 60" in s:
        return 60
    nums = re.findall(r"\d+", s)
    return float(nums[0]) if nums else val


def detect_likert(df: pd.DataFrame) -> List[str]:
    likert_cols = []
    for col in df.columns:
        series = pd.to_numeric(df[col], errors="coerce")
        non_na = series.dropna()
        if non_na.empty:
            continue
        uniq = set(non_na.unique().tolist())
        if uniq.issubset({0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10}) and 2 <= len(uniq) <= 7:
            likert_cols.append(col)
            df[col] = series.astype("Int64")
    return likert_cols


def flag_reverse_items(df: pd.DataFrame) -> Tuple[pd.DataFrame, List[str]]:
    reverse_items = []
    new_cols = []
    for col in df.columns:
        if str(col).endswith("*"):
            base = str(col).rstrip("*")
            reverse_items.append(base)
            new_cols.append(base)
        else:
            new_cols.append(col)
    df.columns = new_cols
    return df, reverse_items


def map_phq_gad(df: pd.DataFrame):
    phq_cols = [c for c in df.columns if "weeks" in str(c).lower() and "last two weeks" in str(c).lower()][:9]
    gad_cols = [c for c in df.columns if "last two weeks" in str(c).lower() and len(phq_cols) <= len(gad_cols := [])]
    map_vals = {
        "not at all (0)": 0,
        "several days (1)": 1,
        "half of days (2)": 2,
        "more than half of the days (2)": 2,
        "nearly every day (3)": 3,
    }
    def clean_scale(x):
        if pd.isna(x):
            return pd.NA
        s = str(x).strip().lower()
        if s in map_vals:
            return map_vals[s]
        m = re.match(r".*\((\d+)\)", s)
        if m:
            return int(m.group(1))
        if s.isdigit():
            return int(s)
        return pd.NA

    if phq_cols:
        for c in phq_cols:
            df[c] = df[c].apply(clean_scale)
        df["PHQ9_TOTAL"] = df[phq_cols].apply(pd.to_numeric, errors="coerce").sum(axis=1)
    if gad_cols:
        for c in gad_cols:
            df[c] = df[c].apply(clean_scale)
        df["GAD7_TOTAL"] = df[gad_cols].apply(pd.to_numeric, errors="coerce").sum(axis=1)


def process_file(path: str):
    fname = os.path.basename(path)
    try:
        df = read_csv_safe(path)
    except Exception as e:
        print(f"[ERROR] {fname}: {e}")
        return

    original_rows = len(df)

    # Normalize missing
    df = df.applymap(lambda x: x if not (isinstance(x, str) and x.strip() == "") else pd.NA)
    df = df.applymap(lambda x: pd.NA if (isinstance(x, str) and not x.strip()) else x)

    # Reverse-coded items
    df, reverse_items = flag_reverse_items(df)

    # Strip whitespace/case
    df.columns = [str(c).strip() for c in df.columns]
    for col in df.columns:
        df[col] = df[col].apply(lambda v: v.strip() if isinstance(v, str) else v)

    # Normalize yes/no/maybe and age ranges
    for col in df.columns:
        df[col] = df[col].apply(normalize_yes_no_maybe)
        if "age" in col.lower():
            df[col] = df[col].apply(normalize_age)

    # Detect likert numerics
    detect_likert(df)

    # Sleep/time normalization
    for col in df.columns:
        if any(k in col.lower() for k in ["bed", "sleep", "time", "minute", "hour"]):
            df[col] = df[col].apply(normalize_times)
            df[col] = df[col].apply(normalize_duration)

    # PHQ/GAD scoring where present
    map_phq_gad(df)

    # Drop only rows that are completely empty
    df_clean = df.dropna(how="all")
    cleaned_rows = len(df_clean)
    removed = original_rows - cleaned_rows

    checksum_src = f"{cleaned_rows}|{','.join(df_clean.columns)}"
    checksum = hashlib.md5(checksum_src.encode("utf-8")).hexdigest()

    out_path = os.path.join(DATA_DIR, fname.replace(".csv", OUTPUT_SUFFIX))
    try:
        df_clean.to_csv(out_path, index=False, encoding="utf-8")
    except Exception:
        df_clean.to_csv(out_path, index=False, encoding="latin1")

    print(
        f"[OK] {fname} -> {out_path} | original: {original_rows} | cleaned: {cleaned_rows} | "
        f"removed: {removed} | reverse-coded: {reverse_items} | checksum: {checksum}"
    )


def main():
    files = [f for f in os.listdir(DATA_DIR) if f.lower().endswith(".csv")]
    for f in files:
        process_file(os.path.join(DATA_DIR, f))


if __name__ == "__main__":
    main()

