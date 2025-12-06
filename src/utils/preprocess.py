# src/utils/preprocess.py
"""
Dataset-specific cleaning functions.

Each function takes a DataFrame and returns a cleaned DataFrame.
These functions handle:
- Column name normalization (lowercase, underscores, no special chars)
- BOM removal
- Whitespace trimming
- Empty string → NaN conversion
- Categorical normalization (Yes/No/Maybe, gender, age ranges)
- Likert scale detection and integer conversion

They do NOT compute derived scores (PHQ-9, GAD-7, stress, sleep).
Those are computed in the unified dataset builder.
"""
from __future__ import annotations

import re
from typing import List, Tuple

import pandas as pd
import numpy as np


# ---------------------------------------------------------------------------
# Shared Utilities
# ---------------------------------------------------------------------------

def normalize_column_name(col: str) -> str:
    """
    Normalize a column name:
    - Strip BOM and whitespace
    - Lowercase
    - Replace spaces/special chars with underscores
    - Remove duplicate underscores
    - Remove leading/trailing underscores
    """
    # Strip BOM and whitespace
    col = col.replace('\ufeff', '').strip()
    # Lowercase
    col = col.lower()
    # Replace special chars with underscore
    col = re.sub(r'[^a-z0-9_]', '_', col)
    # Remove duplicate underscores
    col = re.sub(r'_+', '_', col)
    # Remove leading/trailing underscores
    col = col.strip('_')
    return col


def normalize_column_names(df: pd.DataFrame) -> pd.DataFrame:
    """Apply normalize_column_name to all columns."""
    df = df.copy()
    df.columns = [normalize_column_name(c) for c in df.columns]
    return df


def empty_to_nan(df: pd.DataFrame) -> pd.DataFrame:
    """Convert empty strings and whitespace-only to NaN."""
    df = df.copy()
    # Replace empty strings and whitespace with NaN
    df = df.replace(r'^\s*$', np.nan, regex=True)
    df = df.replace('', np.nan)
    return df


def normalize_yes_no_maybe(value) -> str | None:
    """
    Normalize yes/no/maybe variants.
    Returns 'Yes', 'No', 'Maybe', or the original value if not matched.
    """
    if pd.isna(value):
        return np.nan
    val = str(value).strip().lower()
    if val in ('yes', 'y', 'true', '1'):
        return 'Yes'
    if val in ('no', 'n', 'false', '0'):
        return 'No'
    if val in ('maybe', 'unsure', 'not sure', 'uncertain'):
        return 'Maybe'
    return value  # Return original if no match


def normalize_gender(value) -> str | None:
    """Normalize gender values."""
    if pd.isna(value):
        return np.nan
    val = str(value).strip().lower()
    if val in ('male', 'm', 'man'):
        return 'Male'
    if val in ('female', 'f', 'woman'):
        return 'Female'
    if val in ('other', 'non-binary', 'nonbinary'):
        return 'Other'
    return value  # Return original if no match


def normalize_age_range(value) -> str | None:
    """
    Normalize age range values to consistent format.
    Examples: "20-25", "20 to 25" → "20-25"
              "30-Above", ">30" → "30+"
              "Above 30" → "30+"
    """
    if pd.isna(value):
        return np.nan
    val = str(value).strip()
    
    # Normalize "Above X" or ">X" patterns
    match = re.match(r'^(above|>)\s*(\d+)$', val, re.IGNORECASE)
    if match:
        return f"{match.group(2)}+"
    
    # Normalize "X-Above" or "X+" patterns
    match = re.match(r'^(\d+)\s*[-–]\s*(above|\+)$', val, re.IGNORECASE)
    if match:
        return f"{match.group(1)}+"
    
    # Normalize "X to Y" or "X - Y" patterns
    match = re.match(r'^(\d+)\s*(to|[-–])\s*(\d+)$', val, re.IGNORECASE)
    if match:
        return f"{match.group(1)}-{match.group(3)}"
    
    return val


def detect_likert_column(series: pd.Series) -> bool:
    """
    Detect if a column appears to be a Likert scale (1-5, 1-7, etc.).
    Returns True if all non-null values are integers in a small range.
    """
    non_null = series.dropna()
    if len(non_null) == 0:
        return False
    
    try:
        # Try to convert to numeric
        numeric = pd.to_numeric(non_null, errors='coerce')
        if numeric.isna().all():
            return False
        
        # Check if all values are integers in a small range
        unique_vals = numeric.dropna().unique()
        if len(unique_vals) > 10:  # Too many unique values
            return False
        
        # Check if values are integers
        if not all(float(v).is_integer() for v in unique_vals if pd.notna(v)):
            return False
        
        # Check if range is reasonable for Likert
        min_val, max_val = int(min(unique_vals)), int(max(unique_vals))
        return 0 <= min_val <= 1 and max_val <= 10
    except (ValueError, TypeError):
        return False


def convert_likert_to_int(series: pd.Series) -> pd.Series:
    """Convert Likert-like column to integers, preserving NaN."""
    return pd.to_numeric(series, errors='coerce').astype('Int64')


def extract_likert_number(value) -> int | None:
    """
    Extract numeric value from Likert-style text like "Several days (1)".
    Returns the number in parentheses if present.
    """
    if pd.isna(value):
        return np.nan
    val = str(value)
    # Look for number in parentheses at end
    match = re.search(r'\((\d+)\)\s*$', val)
    if match:
        return int(match.group(1))
    # Try direct numeric conversion
    try:
        return int(float(val))
    except (ValueError, TypeError):
        return np.nan


# ---------------------------------------------------------------------------
# Dataset-Specific Cleaning Functions
# ---------------------------------------------------------------------------

def clean_abadi(df: pd.DataFrame) -> pd.DataFrame:
    """
    Clean the Abadi et al. (2023) COVID-19 social-psychological dataset.
    
    This dataset has coded Likert items (A3.1, A5.3*, etc.).
    Asterisks denote reverse-coded items.
    """
    df = df.copy()
    
    # Normalize column names
    df = normalize_column_names(df)
    
    # Convert empty to NaN
    df = empty_to_nan(df)
    
    # Identify reverse-coded columns (those with asterisks in original name)
    # Note: after normalization, asterisks become underscores
    reverse_coded = []
    for col in df.columns:
        # Check if original column had asterisk
        if '_' in col and col.count('_') > col.replace('a', '').count('_'):
            # This is a heuristic; better to track from original
            pass
    
    # Convert numeric columns to appropriate types
    for col in df.columns:
        if col in ('respondentid', 'country'):
            continue
        # Try to convert to numeric
        numeric_series = pd.to_numeric(df[col], errors='coerce')
        if not numeric_series.isna().all():
            df[col] = numeric_series.astype('Int64')
    
    return df


def clean_mmc2(df: pd.DataFrame) -> pd.DataFrame:
    """
    Clean the mmc2 mental health dataset.
    
    Contains:
    - Demographics (age, sex, BMI, marital status, education, occupation, etc.)
    - Loneliness items (past 30 days)
    - PHQ-9 items (past 2 weeks) - values like "Several days (1)"
    - GAD-7 items (past 2 weeks) - values like "Not at all (0)"
    - Sleep items (timing, quality, frequency)
    """
    df = df.copy()
    
    # Store original columns for PHQ/GAD detection later
    original_cols = list(df.columns)
    
    # Normalize column names
    df = normalize_column_names(df)
    
    # Convert empty to NaN
    df = empty_to_nan(df)
    
    # Process demographics
    # Age normalization
    age_cols = [c for c in df.columns if 'age' in c]
    for col in age_cols:
        df[col] = df[col].apply(normalize_age_range)
    
    # Gender/sex normalization
    sex_cols = [c for c in df.columns if 'sex' in c]
    for col in sex_cols:
        df[col] = df[col].apply(normalize_gender)
    
    # Process PHQ-9 and GAD-7 items: extract numeric from text
    # These columns contain values like "Several days (1)", "Not at all (0)"
    for col in df.columns:
        # Detect columns with Likert text format
        sample = df[col].dropna().head(10)
        if len(sample) > 0:
            sample_str = str(sample.iloc[0])
            # Check if it's Likert text format
            if re.search(r'\(\d+\)\s*$', sample_str):
                df[col] = df[col].apply(extract_likert_number)
    
    # Process sleep timing columns
    # Normalize time ranges - keep as categorical for now
    
    return df


def clean_pone(df: pd.DataFrame) -> pd.DataFrame:
    """
    Clean the pone.0246894.s005 stress factors dataset.
    
    Contains:
    - ID
    - fear of infection (numeric)
    - difficulty in outside activities (numeric)
    - economic loss (numeric)
    - disturbance in eating and sleeping (numeric)
    - adaptive stress (numeric)
    - perception of stress (numeric)
    """
    df = df.copy()
    
    # Normalize column names
    df = normalize_column_names(df)
    
    # Convert empty to NaN
    df = empty_to_nan(df)
    
    # All columns except ID should be numeric
    for col in df.columns:
        if col != 'id':
            df[col] = pd.to_numeric(df[col], errors='coerce').astype('Int64')
    
    return df


def clean_lifestyle(df: pd.DataFrame) -> pd.DataFrame:
    """
    Clean the mental_health_finaldata_1 lifestyle/stress dataset.
    
    Contains:
    - Age (ranges like 20-25, 30-Above)
    - Gender (Male/Female)
    - Occupation (Corporate, Business, Student, Housewife, Others)
    - Days_Indoors (Go out Every day, 1-14 days, etc.)
    - Yes/No/Maybe columns: Growing_Stress, Quarantine_Frustrations,
      Changes_Habits, Mental_Health_History, Weight_Change, Coping_Struggles,
      Work_Interest, Social_Weakness
    - Mood_Swings (Low/Medium/High)
    """
    df = df.copy()
    
    # Normalize column names
    df = normalize_column_names(df)
    
    # Convert empty to NaN
    df = empty_to_nan(df)
    
    # Age normalization
    if 'age' in df.columns:
        df['age'] = df['age'].apply(normalize_age_range)
    
    # Gender normalization
    if 'gender' in df.columns:
        df['gender'] = df['gender'].apply(normalize_gender)
    
    # Yes/No/Maybe normalization
    yes_no_cols = [
        'growing_stress', 'quarantine_frustrations', 'changes_habits',
        'mental_health_history', 'weight_change', 'coping_struggles',
        'work_interest', 'social_weakness'
    ]
    for col in yes_no_cols:
        if col in df.columns:
            df[col] = df[col].apply(normalize_yes_no_maybe)
    
    # Capitalize occupation
    if 'occupation' in df.columns:
        df['occupation'] = df['occupation'].str.strip().str.title()
    
    # Capitalize mood_swings
    if 'mood_swings' in df.columns:
        df['mood_swings'] = df['mood_swings'].str.strip().str.title()
    
    # Normalize days_indoors
    if 'days_indoors' in df.columns:
        df['days_indoors'] = df['days_indoors'].str.strip()
    
    return df


def clean_dataset(df: pd.DataFrame) -> pd.DataFrame:
    """
    Clean the legacy dataset.csv (from Static/Data/).
    
    This is the original model input dataset with:
    - 24 binary yes/no symptom columns
    - 1 Disorder label column (Anxiety, Depression, Loneliness, Stress, Normal)
    
    Column names are like: feeling.nervous, panic, breathing.rapidly, etc.
    Values are: yes, no
    """
    df = df.copy()
    
    # Normalize column names (. becomes _)
    df = normalize_column_names(df)
    
    # Convert empty to NaN
    df = empty_to_nan(df)
    
    # Normalize yes/no values
    symptom_cols = [c for c in df.columns if c != 'disorder']
    for col in symptom_cols:
        df[col] = df[col].apply(normalize_yes_no_maybe)
    
    # Capitalize disorder labels
    if 'disorder' in df.columns:
        df['disorder'] = df['disorder'].str.strip().str.title()
    
    return df


# ---------------------------------------------------------------------------
# Cleaning Function Registry
# ---------------------------------------------------------------------------

def get_cleaner_for_file(filename: str):
    """
    Return the appropriate cleaning function based on filename.
    Returns None if no cleaner is found.
    """
    filename_lower = filename.lower()
    
    if 'abadi' in filename_lower:
        return clean_abadi
    if 'mmc2' in filename_lower:
        return clean_mmc2
    if 'mental_health' in filename_lower or 'finaldata' in filename_lower:
        return clean_lifestyle
    if 'pone' in filename_lower:
        return clean_pone
    if filename_lower == 'dataset.csv':
        return clean_dataset
    
    return None


def list_available_cleaners() -> List[Tuple[str, str]]:
    """Return list of (pattern, function_name) for available cleaners."""
    return [
        ('abadi*', 'clean_abadi'),
        ('mmc2*', 'clean_mmc2'),
        ('mental_health* / finaldata*', 'clean_lifestyle'),
        ('pone*', 'clean_pone'),
        ('dataset.csv', 'clean_dataset'),
    ]

