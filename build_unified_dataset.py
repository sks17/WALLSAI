import os
import re
import hashlib
import difflib
import pandas as pd
from typing import List, Dict, Tuple

# IMPORTANT:
# After modifying this file, DO NOT run inside Cursor.
# Run manually in the terminal:
#     python build_unified_dataset.py
#     python train_models.py
# This avoids prior TypeErrors and ensures fresh preprocessing.

DATA_DIR = "newData"
OUTPUT_FILE = "unified_training.csv"

CANONICAL_COLS = [
    "age",
    "gender",
    "occupation",
    "economic_status",
    "country",
    "stress_score",
    "anxiety_score",
    "depression_score",
    "sleep_quality",
    "lifestyle_change",
    "frustration",
    "social_isolation",
    "weight_change",
    "mood_swings",
    "coping_struggle",
    "source_dataset",
]


def standardize_columns(cols: List[str]) -> List[str]:
    clean = []
    seen = {}
    for c in cols:
        c0 = str(c).replace("\ufeff", "")
        c1 = re.sub(r"[^0-9a-zA-Z]+", "_", c0.lower()).strip("_")
        if c1 == "":
            c1 = "col"
        # ensure uniqueness
        if c1 in seen:
            seen[c1] += 1
            c1 = f"{c1}_{seen[c1]}"
        else:
            seen[c1] = 0
        clean.append(c1)
    return clean


def fuzzy_find_column(possible_names: List[str], df_columns: List[str], threshold: float = 0.65) -> str:
    best_col = None
    best_score = threshold
    for col in df_columns:
        for name in possible_names:
            score = difflib.SequenceMatcher(None, col.lower(), name.lower()).ratio()
            if score >= best_score:
                best_score = score
                best_col = col
    return best_col


def load_cleaned() -> List[pd.DataFrame]:
    dfs = []
    for fname in os.listdir(DATA_DIR):
        if not (fname.lower().endswith("_cleaned.csv") or fname.lower().endswith("_cleaned_cleaned.csv")):
            continue
        path = os.path.join(DATA_DIR, fname)
        df = pd.read_csv(path, encoding="utf-8", low_memory=False)
        df.columns = standardize_columns(df.columns.tolist())
        df["source_dataset"] = fname
        dfs.append(df)
    return dfs


def debug_columns(dfs: List[pd.DataFrame]):
    lines = []
    for df in dfs:
        source = df.get("source_dataset", ["unknown"]).iloc[0] if "source_dataset" in df.columns else "unknown"
        cols = df.columns.tolist()
        print(f"[DEBUG] Columns for {source}:")
        print(cols)
        lines.append(f"{source}:\n" + "\n".join(cols) + "\n")
    debug_path = os.path.join(DATA_DIR, "column_inventory_debug.txt")
    with open(debug_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"[DEBUG] Consolidated column list written to {debug_path}")


def map_columns(df: pd.DataFrame) -> pd.DataFrame:
    mapped = {col: pd.NA for col in CANONICAL_COLS}
    mapping = fuzzy_map_columns(df)

    def pick(name):
        col = mapping.get(name)
        return df[col] if col else pd.NA

    mapped["age"] = pick("age")
    mapped["gender"] = pick("gender")
    mapped["occupation"] = pick("occupation")
    mapped["economic_status"] = pick("economic_status")
    mapped["country"] = pick("country")
    mapped["lifestyle_change"] = pick("lifestyle_change")
    mapped["frustration"] = pick("frustration")
    mapped["social_isolation"] = pick("social_isolation")
    mapped["weight_change"] = pick("weight_change")
    mapped["mood_swings"] = pick("mood_swings")
    mapped["coping_struggle"] = pick("coping_struggle")
    mapped["sleep_quality"] = compute_sleep(df, mapping)
    mapped["depression_score"] = compute_phq9(df, mapping)
    mapped["anxiety_score"] = compute_gad7(df, mapping)
    mapped["stress_score"] = compute_stress(df, mapping)

    mapped["source_dataset"] = df["source_dataset"]

    out = pd.DataFrame(mapped)
    return out


def numeric_cols_by_keywords(df: pd.DataFrame, keywords: List[str]) -> List[str]:
    cols = []
    for c in df.columns:
        cl = c.lower()
        if any(k in cl for k in keywords):
            cols.append(c)
    num_cols = []
    for c in cols:
        ser = pd.to_numeric(df[c], errors="coerce")
        if ser.notna().any():
            num_cols.append(c)
    return num_cols


def fuzzy_best_match(colname: str, targets: List[str], threshold: float = 0.8) -> str:
    cand = difflib.get_close_matches(colname, targets, n=1, cutoff=threshold)
    return cand[0] if cand else ""


def fuzzy_map_columns(df: pd.DataFrame) -> Dict[str, str]:
    mapping = {}
    aliases = {
        "age": ["age", "age range", "age_range", "age range in years"],
        "gender": ["gender", "sex", "biological sex"],
        "occupation": ["occupation", "job", "work"],
        "country": ["country"],
        "economic_status": ["economic status", "economic", "income", "financial"],
        "lifestyle_change": ["lifestyle change", "changes_habits", "changes habits", "lifestyle", "habit"],
        "frustration": ["frustration", "quarantine_frustrations"],
        "social_isolation": ["social_weakness", "lonely", "isolation", "companionship", "left_out"],
        "weight_change": ["weight_change", "weight change", "weight"],
        "mood_swings": ["mood_swings", "mood swings", "mood"],
        "coping_struggle": ["coping_struggles", "coping", "struggle"],
    }

    for target, names in aliases.items():
        mapping[target] = fuzzy_find_column(names, df.columns, threshold=0.65)

    # PHQ and GAD items via fuzzy phrases
    phq_phrases = [
        "little interest",
        "feeling down",
        "trouble falling",
        "low energy",
        "poor appetite",
        "feeling bad",
        "trouble concentrating",
        "moving slowly",
        "dead or hurting yourself",
    ]
    gad_phrases = [
        "nervous",
        "can't control worrying",
        "worrying too much",
        "trouble relaxing",
        "restless",
        "annoyed or irritable",
        "something awful might happen",
    ]

    def fuzzy_items(phrases: List[str]) -> List[str]:
        found = []
        for col in df.columns:
            for p in phrases:
                score = difflib.SequenceMatcher(None, col.lower(), p.lower()).ratio()
                if score >= 0.6:
                    found.append(col)
                    break
        return list(dict.fromkeys(found))  # dedupe, preserve order

    mapping["phq_items"] = fuzzy_items(phq_phrases)
    mapping["gad_items"] = fuzzy_items(gad_phrases)

    stress_keywords = ["stress", "infection", "economic", "difficulty", "loss", "disturbance", "adaptive"]
    mapping["stress_items"] = [c for c in df.columns if any(k in c.lower() for k in stress_keywords)]

    sleep_phrases = [
        "sleep latency",
        "fall asleep",
        "wake up",
        "hours of actual sleep",
        "hours in bed",
        "sleep quality",
        "bathroom",
        "snore",
        "night awakening",
        "dreams",
        "temperature",
        "pain",
    ]
    mapping["sleep_items"] = fuzzy_items(sleep_phrases)

    return mapping


def compute_phq9(df: pd.DataFrame, mapping: Dict[str, List[str]]):
    candidates = mapping.get("phq_items", [])
    valid = [c for c in candidates if c in df.columns]
    if len(valid) < 2:
        return pd.Series([pd.NA] * len(df))
    stacked = []
    for col in valid:
        stacked.append(pd.to_numeric(df[col], errors="coerce"))
    temp = pd.concat(stacked, axis=1)
    return temp.sum(axis=1)


def compute_gad7(df: pd.DataFrame, mapping: Dict[str, List[str]]):
    candidates = mapping.get("gad_items", [])
    valid = [c for c in candidates if c in df.columns]
    if len(valid) < 2:
        return pd.Series([pd.NA] * len(df))
    stacked = []
    for col in valid:
        stacked.append(pd.to_numeric(df[col], errors="coerce"))
    temp = pd.concat(stacked, axis=1)
    return temp.sum(axis=1)


def compute_stress(df: pd.DataFrame, mapping: Dict[str, List[str]]):
    candidates = mapping.get("stress_items", [])
    valid = [c for c in candidates if c in df.columns]
    if len(valid) < 2:
        return pd.Series([pd.NA] * len(df))
    temp = pd.DataFrame(index=df.index)
    for col in valid:
        temp[col] = pd.to_numeric(df[col], errors="coerce")
    return temp.mean(axis=1)


def compute_sleep(df: pd.DataFrame, mapping: Dict[str, List[str]]):
    candidates = mapping.get("sleep_items", [])
    valid = [c for c in candidates if c in df.columns]
    if len(valid) < 2:
        return pd.Series([pd.NA] * len(df))
    temp = pd.DataFrame(index=df.index)
    for col in valid:
        temp[col] = pd.to_numeric(df[col], errors="coerce")
    return temp.mean(axis=1)


def main():
    dfs = load_cleaned()
    if not dfs:
        print("No cleaned datasets found.")
        return
    debug_columns(dfs)

    mapped_dfs = []
    for df in dfs:
        mapped_dfs.append(map_columns(df))

    unified = pd.concat(mapped_dfs, ignore_index=True)
    before = len(unified)
    after = len(unified)

    unified.to_csv(OUTPUT_FILE, index=False, encoding="utf-8")

    print(f"Merged datasets: {len(dfs)}")
    print(f"Rows before filter: {before}")
    print(f"Rows after filter: {after}")
    print("Preview:")
    print(unified.head().to_string(index=False))


if __name__ == "__main__":
    main()

# NOTE TO USER:
# After saving this file, manually run:
# python build_unified_dataset.py
# python train_models.py
# Do NOT attempt to run scripts inside Cursor.

