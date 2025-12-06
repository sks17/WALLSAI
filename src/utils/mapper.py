# src/utils/mapper.py
"""
Column Mapping and Scoring Utilities

This module provides functions to map cleaned dataset columns
to a canonical unified schema and compute derived scores.

Key functions:
- detect_columns(df): Returns a diagnostics report of available columns
- map_demographics(df): Maps demographic columns
- map_stress(df): Computes stress score from stress-related columns
- map_phq9(df): Computes PHQ-9 depression score
- map_gad7(df): Computes GAD-7 anxiety score
- map_sleep(df): Computes sleep quality score
- build_unified_row(df, source_name): Builds a unified DataFrame row
"""
from __future__ import annotations

import difflib
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# Canonical Schema
# ---------------------------------------------------------------------------

CANONICAL_COLUMNS = [
    # Demographics
    "age",
    "gender",
    "occupation",
    "economic_status",
    "country",
    "residence_area",
    "marital_status",
    "education",
    # Target scores
    "depression_score",      # PHQ-9 total
    "anxiety_score",         # GAD-7 total
    "stress_score",          # Stress scale mean
    "sleep_quality",         # Sleep quality score
    # Lifestyle/behavioral
    "lifestyle_change",
    "frustration",
    "social_isolation",
    "weight_change",
    "mood_swings",
    "coping_struggle",
    # Legacy disorder classification
    "disorder",
    # Metadata
    "source_dataset",
]


# ---------------------------------------------------------------------------
# Fuzzy Matching Utilities
# ---------------------------------------------------------------------------

def fuzzy_match(target: str, candidates: List[str], threshold: float = 0.60) -> Optional[str]:
    """
    Find the best fuzzy match for target among candidates.
    Returns None if no match exceeds the threshold.
    """
    best_col = None
    best_score = threshold
    
    target_lower = target.lower()
    for col in candidates:
        col_lower = col.lower()
        # Direct substring match gets high priority
        if target_lower in col_lower or col_lower in target_lower:
            score = 0.85
        else:
            score = difflib.SequenceMatcher(None, col_lower, target_lower).ratio()
        
        if score > best_score:
            best_score = score
            best_col = col
    
    return best_col


def fuzzy_match_phrases(phrases: List[str], columns: List[str], threshold: float = 0.55) -> List[str]:
    """
    Find columns that match any of the given phrases.
    Returns list of matching column names (deduplicated, order preserved).
    """
    matched = []
    for col in columns:
        col_lower = col.lower()
        for phrase in phrases:
            phrase_lower = phrase.lower()
            # Check substring
            if phrase_lower in col_lower:
                matched.append(col)
                break
            # Check fuzzy
            score = difflib.SequenceMatcher(None, col_lower, phrase_lower).ratio()
            if score >= threshold:
                matched.append(col)
                break
    
    # Deduplicate while preserving order
    seen = set()
    result = []
    for col in matched:
        if col not in seen:
            seen.add(col)
            result.append(col)
    return result


def keyword_match(keywords: List[str], columns: List[str]) -> List[str]:
    """Find columns containing any of the keywords (case-insensitive)."""
    matched = []
    for col in columns:
        col_lower = col.lower()
        if any(kw.lower() in col_lower for kw in keywords):
            matched.append(col)
    return matched


# ---------------------------------------------------------------------------
# Column Detection & Diagnostics
# ---------------------------------------------------------------------------

@dataclass
class ColumnDiagnostics:
    """Diagnostics report for a single dataset."""
    source_name: str
    total_columns: int
    total_rows: int
    
    # Mapped columns
    demographics_found: Dict[str, str] = field(default_factory=dict)
    demographics_missing: List[str] = field(default_factory=list)
    
    phq9_items: List[str] = field(default_factory=list)
    gad7_items: List[str] = field(default_factory=list)
    stress_items: List[str] = field(default_factory=list)
    sleep_items: List[str] = field(default_factory=list)
    lifestyle_items: Dict[str, str] = field(default_factory=dict)
    disorder_column: Optional[str] = None
    
    # Row contributions per target
    rows_with_depression: int = 0
    rows_with_anxiety: int = 0
    rows_with_stress: int = 0
    rows_with_sleep: int = 0
    rows_with_disorder: int = 0
    
    def to_dict(self) -> Dict:
        return {
            "source": self.source_name,
            "total_columns": self.total_columns,
            "total_rows": self.total_rows,
            "demographics_found": self.demographics_found,
            "demographics_missing": self.demographics_missing,
            "phq9_items": len(self.phq9_items),
            "gad7_items": len(self.gad7_items),
            "stress_items": len(self.stress_items),
            "sleep_items": len(self.sleep_items),
            "rows_with_depression": self.rows_with_depression,
            "rows_with_anxiety": self.rows_with_anxiety,
            "rows_with_stress": self.rows_with_stress,
            "rows_with_sleep": self.rows_with_sleep,
            "rows_with_disorder": self.rows_with_disorder,
        }


# Demographic aliases for fuzzy matching
DEMOGRAPHIC_ALIASES = {
    "age": ["age", "age_range", "age range", "2_age_range_in_years"],
    "gender": ["gender", "sex", "3_sex"],
    "occupation": ["occupation", "job", "work", "7_occupation"],
    "economic_status": ["economic_status", "economic", "income", "financial", "8_economic_status"],
    "country": ["country", "nation", "region"],
    "residence_area": ["residence", "residence_area", "urban", "rural", "9_residence_area"],
    "marital_status": ["marital", "marital_status", "married", "5_marital_status"],
    "education": ["education", "education_level", "6_education_level"],
}

# Lifestyle aliases
LIFESTYLE_ALIASES = {
    "lifestyle_change": ["lifestyle_change", "changes_habits", "habit", "lifestyle"],
    "frustration": ["frustration", "quarantine_frustrations", "frustrated"],
    "social_isolation": ["social_weakness", "social_isolation", "lonely", "loneliness", 
                         "companionship", "left_out", "isolation", "withdrawn"],
    "weight_change": ["weight_change", "weight"],
    "mood_swings": ["mood_swings", "mood"],
    "coping_struggle": ["coping_struggles", "coping", "struggle"],
}

# PHQ-9 item phrases (depression screening)
PHQ9_PHRASES = [
    "little interest",
    "pleasure in doing",
    "feeling down",
    "depressed",
    "hopeless",
    "trouble falling",
    "staying asleep",
    "sleeping too much",
    "feeling tired",
    "little energy",
    "poor appetite",
    "over_eating",
    "overeating",
    "feeling bad about yourself",
    "failure",
    "trouble concentrating",
    "moving or speaking",
    "slowly",
    "fidgety",
    "restless",
    "better off dead",
    "hurting yourself",
]

# GAD-7 item phrases (anxiety screening)
GAD7_PHRASES = [
    "feeling nervous",
    "anxious",
    "on edge",
    "not being able to stop",
    "control worrying",
    "worrying too much",
    "trouble relaxing",
    "restless",
    "hard to sit still",
    "easily annoyed",
    "irritable",
    "feeling afraid",
    "something awful",
]

# Stress-related keywords
STRESS_KEYWORDS = [
    "stress", "infection", "fear", "economic_loss", "difficulty", 
    "disturbance", "adaptive", "perception", "growing_stress"
]

# Sleep-related phrases
SLEEP_PHRASES = [
    "sleep", "bed", "bedtime", "fall asleep", "wake up", "waking",
    "hours of actual sleep", "hours slept", "sleep latency",
    "bathroom", "snore", "dreams", "temperature", "pain",
    "sleep quality", "enthusiasm", "sleep_quality"
]


def detect_columns(df: pd.DataFrame, source_name: str = "unknown") -> ColumnDiagnostics:
    """
    Analyze a DataFrame and return a diagnostics report of which columns
    map to which canonical fields.
    """
    columns = df.columns.tolist()
    diag = ColumnDiagnostics(
        source_name=source_name,
        total_columns=len(columns),
        total_rows=len(df),
    )
    
    # Detect demographics
    for target, aliases in DEMOGRAPHIC_ALIASES.items():
        match = fuzzy_match_phrases(aliases, columns, threshold=0.60)
        if match:
            diag.demographics_found[target] = match[0]
        else:
            diag.demographics_missing.append(target)
    
    # Detect lifestyle columns
    for target, aliases in LIFESTYLE_ALIASES.items():
        match = fuzzy_match_phrases(aliases, columns, threshold=0.60)
        if match:
            diag.lifestyle_items[target] = match[0]
    
    # Detect PHQ-9 items
    diag.phq9_items = fuzzy_match_phrases(PHQ9_PHRASES, columns, threshold=0.50)
    
    # Detect GAD-7 items
    diag.gad7_items = fuzzy_match_phrases(GAD7_PHRASES, columns, threshold=0.50)
    
    # Detect stress items
    diag.stress_items = keyword_match(STRESS_KEYWORDS, columns)
    
    # Detect sleep items
    diag.sleep_items = fuzzy_match_phrases(SLEEP_PHRASES, columns, threshold=0.50)
    
    # Detect disorder column (for legacy dataset)
    disorder_match = fuzzy_match("disorder", columns, threshold=0.80)
    if disorder_match:
        diag.disorder_column = disorder_match
    
    return diag


# ---------------------------------------------------------------------------
# Mapping Functions
# ---------------------------------------------------------------------------

def map_demographics(df: pd.DataFrame, diag: ColumnDiagnostics) -> Dict[str, pd.Series]:
    """
    Map demographic columns from source df to canonical names.
    Returns dict of {canonical_name: Series}.
    """
    result = {}
    
    for target, source_col in diag.demographics_found.items():
        if source_col in df.columns:
            result[target] = df[source_col].copy()
        else:
            result[target] = pd.Series([np.nan] * len(df), index=df.index)
    
    # Fill missing demographics with NaN
    for target in diag.demographics_missing:
        result[target] = pd.Series([np.nan] * len(df), index=df.index)
    
    return result


def map_lifestyle(df: pd.DataFrame, diag: ColumnDiagnostics) -> Dict[str, pd.Series]:
    """
    Map lifestyle/behavioral columns from source df to canonical names.
    Returns dict of {canonical_name: Series}.
    """
    result = {}
    
    for target, source_col in diag.lifestyle_items.items():
        if source_col in df.columns:
            result[target] = df[source_col].copy()
        else:
            result[target] = pd.Series([np.nan] * len(df), index=df.index)
    
    # Fill any missing lifestyle columns
    for target in LIFESTYLE_ALIASES.keys():
        if target not in result:
            result[target] = pd.Series([np.nan] * len(df), index=df.index)
    
    return result


def map_phq9(df: pd.DataFrame, diag: ColumnDiagnostics) -> Tuple[pd.Series, int]:
    """
    Compute PHQ-9 depression score from detected items.
    Returns (score_series, rows_with_valid_score).
    
    PHQ-9 is sum of 9 items, each scored 0-3.
    """
    items = diag.phq9_items
    valid_items = [c for c in items if c in df.columns]
    
    if len(valid_items) < 2:
        # Not enough items to compute meaningful score
        return pd.Series([np.nan] * len(df), index=df.index), 0
    
    # Convert each column to numeric individually
    numeric_cols = []
    for col in valid_items:
        numeric_cols.append(pd.to_numeric(df[col], errors="coerce"))
    
    # Stack and sum
    temp = pd.concat(numeric_cols, axis=1)
    score = temp.sum(axis=1, min_count=2)  # Require at least 2 non-NaN
    
    rows_valid = score.notna().sum()
    return score, rows_valid


def map_gad7(df: pd.DataFrame, diag: ColumnDiagnostics) -> Tuple[pd.Series, int]:
    """
    Compute GAD-7 anxiety score from detected items.
    Returns (score_series, rows_with_valid_score).
    
    GAD-7 is sum of 7 items, each scored 0-3.
    """
    items = diag.gad7_items
    valid_items = [c for c in items if c in df.columns]
    
    if len(valid_items) < 2:
        return pd.Series([np.nan] * len(df), index=df.index), 0
    
    numeric_cols = []
    for col in valid_items:
        numeric_cols.append(pd.to_numeric(df[col], errors="coerce"))
    
    temp = pd.concat(numeric_cols, axis=1)
    score = temp.sum(axis=1, min_count=2)
    
    rows_valid = score.notna().sum()
    return score, rows_valid


def map_stress(df: pd.DataFrame, diag: ColumnDiagnostics) -> Tuple[pd.Series, int]:
    """
    Compute stress score from detected stress-related items.
    Returns (score_series, rows_with_valid_score).
    
    Stress score is mean of available stress items.
    """
    items = diag.stress_items
    valid_items = [c for c in items if c in df.columns]
    
    if len(valid_items) == 0:
        return pd.Series([np.nan] * len(df), index=df.index), 0
    
    if len(valid_items) == 1:
        # Single column: just return its numeric values
        score = pd.to_numeric(df[valid_items[0]], errors="coerce")
        rows_valid = score.notna().sum()
        return score, rows_valid
    
    # Multiple columns: compute mean
    numeric_cols = []
    for col in valid_items:
        numeric_cols.append(pd.to_numeric(df[col], errors="coerce"))
    
    temp = pd.concat(numeric_cols, axis=1)
    score = temp.mean(axis=1, skipna=True)
    
    rows_valid = score.notna().sum()
    return score, rows_valid


def map_sleep(df: pd.DataFrame, diag: ColumnDiagnostics) -> Tuple[pd.Series, int]:
    """
    Compute sleep quality score from detected sleep items.
    Returns (score_series, rows_with_valid_score).
    
    Sleep score is mean of available sleep-related numeric items.
    """
    items = diag.sleep_items
    valid_items = [c for c in items if c in df.columns]
    
    if len(valid_items) == 0:
        return pd.Series([np.nan] * len(df), index=df.index), 0
    
    if len(valid_items) == 1:
        score = pd.to_numeric(df[valid_items[0]], errors="coerce")
        rows_valid = score.notna().sum()
        return score, rows_valid
    
    numeric_cols = []
    for col in valid_items:
        numeric_cols.append(pd.to_numeric(df[col], errors="coerce"))
    
    temp = pd.concat(numeric_cols, axis=1)
    score = temp.mean(axis=1, skipna=True)
    
    rows_valid = score.notna().sum()
    return score, rows_valid


def map_disorder(df: pd.DataFrame, diag: ColumnDiagnostics) -> pd.Series:
    """
    Map the disorder classification column (for legacy dataset.csv).
    """
    if diag.disorder_column and diag.disorder_column in df.columns:
        return df[diag.disorder_column].copy()
    return pd.Series([np.nan] * len(df), index=df.index)


# ---------------------------------------------------------------------------
# Unified Row Builder
# ---------------------------------------------------------------------------

def build_unified_dataframe(df: pd.DataFrame, source_name: str) -> Tuple[pd.DataFrame, ColumnDiagnostics]:
    """
    Build a unified DataFrame from a source dataset.
    
    Returns:
        (unified_df, diagnostics)
    """
    # Detect available columns
    diag = detect_columns(df, source_name)
    
    # Map all components
    demographics = map_demographics(df, diag)
    lifestyle = map_lifestyle(df, diag)
    
    depression_score, diag.rows_with_depression = map_phq9(df, diag)
    anxiety_score, diag.rows_with_anxiety = map_gad7(df, diag)
    stress_score, diag.rows_with_stress = map_stress(df, diag)
    sleep_quality, diag.rows_with_sleep = map_sleep(df, diag)
    disorder = map_disorder(df, diag)
    
    if diag.disorder_column:
        diag.rows_with_disorder = disorder.notna().sum()
    
    # Build unified DataFrame
    unified_data = {}
    
    # Demographics
    for col in ["age", "gender", "occupation", "economic_status", "country", 
                "residence_area", "marital_status", "education"]:
        unified_data[col] = demographics.get(col, pd.Series([np.nan] * len(df), index=df.index))
    
    # Target scores
    unified_data["depression_score"] = depression_score
    unified_data["anxiety_score"] = anxiety_score
    unified_data["stress_score"] = stress_score
    unified_data["sleep_quality"] = sleep_quality
    
    # Lifestyle
    for col in ["lifestyle_change", "frustration", "social_isolation", 
                "weight_change", "mood_swings", "coping_struggle"]:
        unified_data[col] = lifestyle.get(col, pd.Series([np.nan] * len(df), index=df.index))
    
    # Disorder classification (legacy)
    unified_data["disorder"] = disorder
    
    # Source metadata
    unified_data["source_dataset"] = source_name
    
    unified_df = pd.DataFrame(unified_data)
    
    return unified_df, diag


# ---------------------------------------------------------------------------
# Diagnostics Reporting
# ---------------------------------------------------------------------------

def print_diagnostics(diag: ColumnDiagnostics):
    """Print a formatted diagnostics report for a dataset."""
    print(f"\n{'='*60}")
    print(f"Dataset: {diag.source_name}")
    print(f"{'='*60}")
    print(f"Total columns: {diag.total_columns}")
    print(f"Total rows: {diag.total_rows}")
    
    print(f"\n📊 Demographics Mapped:")
    if diag.demographics_found:
        for target, source in diag.demographics_found.items():
            print(f"   ✅ {target} → {source}")
    if diag.demographics_missing:
        for target in diag.demographics_missing:
            print(f"   ❌ {target} → (not found)")
    
    print(f"\n📊 Lifestyle Mapped:")
    if diag.lifestyle_items:
        for target, source in diag.lifestyle_items.items():
            print(f"   ✅ {target} → {source}")
    else:
        print("   (none)")
    
    print(f"\n📊 Scale Items Detected:")
    print(f"   PHQ-9 items: {len(diag.phq9_items)}")
    if diag.phq9_items:
        for item in diag.phq9_items[:3]:
            print(f"      • {item[:50]}...")
        if len(diag.phq9_items) > 3:
            print(f"      ... and {len(diag.phq9_items) - 3} more")
    
    print(f"   GAD-7 items: {len(diag.gad7_items)}")
    if diag.gad7_items:
        for item in diag.gad7_items[:3]:
            print(f"      • {item[:50]}...")
        if len(diag.gad7_items) > 3:
            print(f"      ... and {len(diag.gad7_items) - 3} more")
    
    print(f"   Stress items: {len(diag.stress_items)}")
    if diag.stress_items:
        for item in diag.stress_items[:3]:
            print(f"      • {item[:50]}...")
        if len(diag.stress_items) > 3:
            print(f"      ... and {len(diag.stress_items) - 3} more")
    
    print(f"   Sleep items: {len(diag.sleep_items)}")
    if diag.sleep_items:
        for item in diag.sleep_items[:3]:
            print(f"      • {item[:50]}...")
        if len(diag.sleep_items) > 3:
            print(f"      ... and {len(diag.sleep_items) - 3} more")
    
    if diag.disorder_column:
        print(f"   Disorder column: ✅ {diag.disorder_column}")
    
    print(f"\n📊 Row Contributions to Targets:")
    print(f"   Depression (PHQ-9): {diag.rows_with_depression:,} rows")
    print(f"   Anxiety (GAD-7):    {diag.rows_with_anxiety:,} rows")
    print(f"   Stress:             {diag.rows_with_stress:,} rows")
    print(f"   Sleep Quality:      {diag.rows_with_sleep:,} rows")
    if diag.disorder_column:
        print(f"   Disorder Label:     {diag.rows_with_disorder:,} rows")
    
    # Warnings
    warnings = []
    if diag.rows_with_depression == 0 and len(diag.phq9_items) > 0:
        warnings.append("⚠️  PHQ-9 items detected but 0 rows have valid depression scores")
    if diag.rows_with_anxiety == 0 and len(diag.gad7_items) > 0:
        warnings.append("⚠️  GAD-7 items detected but 0 rows have valid anxiety scores")
    if diag.rows_with_stress == 0 and len(diag.stress_items) > 0:
        warnings.append("⚠️  Stress items detected but 0 rows have valid stress scores")
    if diag.rows_with_sleep == 0 and len(diag.sleep_items) > 0:
        warnings.append("⚠️  Sleep items detected but 0 rows have valid sleep scores")
    
    if warnings:
        print(f"\n⚠️  Warnings:")
        for w in warnings:
            print(f"   {w}")

