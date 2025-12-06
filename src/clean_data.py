# src/clean_data.py
"""
Data Cleaning Pipeline

This script reads raw CSV files from /raw_data/ and produces cleaned versions
in /cleaned_data/. Each raw file gets exactly ONE cleaned output:
    <name>_cleaned.csv

IMPORTANT:
- This script ONLY reads from /raw_data/
- It NEVER reprocesses files that are already cleaned
- It NEVER produces _cleaned_cleaned.csv files
- Run manually: python src/clean_data.py

Usage:
    python src/clean_data.py

The script will:
1. Scan /raw_data/ for CSV files
2. Apply the appropriate cleaning function to each
3. Save cleaned files to /cleaned_data/
4. Print a detailed log of all operations
"""
from __future__ import annotations

import hashlib
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd
import numpy as np

# Ensure project root is in path
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.utils.preprocess import (
    clean_abadi,
    clean_mmc2,
    clean_pone,
    clean_lifestyle,
    clean_dataset,
    get_cleaner_for_file,
)


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

RAW_DATA_DIR = ROOT / "raw_data"
CLEANED_DATA_DIR = ROOT / "cleaned_data"

# Map of source files to their canonical names for cleaned output
# This ensures consistent naming regardless of original filename
FILE_CANONICAL_NAMES = {
    "abadi": "abadi",
    "mmc2": "mmc2",
    "mental_health": "mental_health_finaldata",
    "finaldata": "mental_health_finaldata",
    "pone": "pone_stress",
    "dataset.csv": "dataset",
}


# ---------------------------------------------------------------------------
# Utility Functions
# ---------------------------------------------------------------------------

def compute_checksum(df: pd.DataFrame) -> str:
    """Compute MD5 checksum of DataFrame for tracking."""
    # Hash based on shape and column names
    content = f"{df.shape}|{list(df.columns)}|{len(df)}"
    return hashlib.md5(content.encode()).hexdigest()[:12]


def get_canonical_name(filename: str) -> str:
    """Get the canonical output name for a file."""
    filename_lower = filename.lower()
    
    for pattern, canonical in FILE_CANONICAL_NAMES.items():
        if pattern in filename_lower:
            return canonical
    
    # Default: use original name without extension
    return Path(filename).stem


def load_csv_robust(filepath: Path) -> pd.DataFrame:
    """
    Load a CSV file with robust encoding handling.
    Tries UTF-8 first, then falls back to latin1.
    """
    try:
        df = pd.read_csv(filepath, encoding='utf-8')
    except UnicodeDecodeError:
        df = pd.read_csv(filepath, encoding='latin1')
    
    # Strip BOM from column names
    df.columns = [c.replace('\ufeff', '').strip() for c in df.columns]
    
    return df


def is_already_cleaned(filename: str) -> bool:
    """Check if a file is already a cleaned file (to avoid re-cleaning)."""
    return '_cleaned' in filename.lower()


def get_raw_files() -> List[Path]:
    """
    Get list of raw CSV files to process.
    Excludes any files that are already cleaned.
    """
    if not RAW_DATA_DIR.exists():
        return []
    
    files = []
    for f in RAW_DATA_DIR.glob("*.csv"):
        if not is_already_cleaned(f.name):
            files.append(f)
    
    return sorted(files)


# ---------------------------------------------------------------------------
# Cleaning Orchestration
# ---------------------------------------------------------------------------

def clean_single_file(filepath: Path) -> Tuple[Optional[pd.DataFrame], Dict]:
    """
    Clean a single CSV file.
    
    Returns:
        Tuple of (cleaned_df or None, log_dict)
    """
    log = {
        "filename": filepath.name,
        "filepath": str(filepath),
        "timestamp": datetime.now().isoformat(),
        "status": "unknown",
        "original_rows": 0,
        "cleaned_rows": 0,
        "rows_removed": 0,
        "columns_original": [],
        "columns_cleaned": [],
        "columns_modified": [],
        "checksum": "",
        "error": None,
    }
    
    try:
        # Load the file
        df = load_csv_robust(filepath)
        log["original_rows"] = len(df)
        log["columns_original"] = list(df.columns)
        
        # Get the appropriate cleaner
        cleaner = get_cleaner_for_file(filepath.name)
        
        if cleaner is None:
            log["status"] = "skipped"
            log["error"] = f"No cleaner found for file: {filepath.name}"
            return None, log
        
        # Apply cleaning
        df_cleaned = cleaner(df)
        
        # Drop completely empty rows (all NaN)
        df_cleaned = df_cleaned.dropna(how='all')
        
        log["cleaned_rows"] = len(df_cleaned)
        log["rows_removed"] = log["original_rows"] - log["cleaned_rows"]
        log["columns_cleaned"] = list(df_cleaned.columns)
        
        # Track modified columns
        modified = []
        for i, (orig, clean) in enumerate(zip(log["columns_original"], log["columns_cleaned"])):
            if orig != clean:
                modified.append(f"{orig} → {clean}")
        log["columns_modified"] = modified
        
        log["checksum"] = compute_checksum(df_cleaned)
        log["status"] = "success"
        
        return df_cleaned, log
        
    except Exception as e:
        log["status"] = "error"
        log["error"] = str(e)
        return None, log


def run_cleaning_pipeline() -> List[Dict]:
    """
    Run the full cleaning pipeline on all raw files.
    
    Returns:
        List of log dictionaries for each file processed.
    """
    print("=" * 70)
    print("DATA CLEANING PIPELINE")
    print("=" * 70)
    print(f"Timestamp: {datetime.now().isoformat()}")
    print(f"Raw data directory: {RAW_DATA_DIR}")
    print(f"Cleaned data directory: {CLEANED_DATA_DIR}")
    print()
    
    # Ensure output directory exists
    CLEANED_DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    # Get files to process
    raw_files = get_raw_files()
    
    if not raw_files:
        print("⚠️  No raw CSV files found in raw_data/")
        print("    Please copy your raw data files to the raw_data/ directory.")
        return []
    
    print(f"Found {len(raw_files)} raw file(s) to process:")
    for f in raw_files:
        print(f"  - {f.name}")
    print()
    
    all_logs = []
    
    for filepath in raw_files:
        print("-" * 70)
        print(f"Processing: {filepath.name}")
        
        df_cleaned, log = clean_single_file(filepath)
        all_logs.append(log)
        
        if df_cleaned is None:
            print(f"  ❌ Status: {log['status']}")
            if log['error']:
                print(f"  Error: {log['error']}")
            continue
        
        # Determine output filename
        canonical = get_canonical_name(filepath.name)
        output_name = f"{canonical}_cleaned.csv"
        output_path = CLEANED_DATA_DIR / output_name
        
        # Save cleaned file
        df_cleaned.to_csv(output_path, index=False)
        
        print(f"  ✅ Status: {log['status']}")
        print(f"  Original rows: {log['original_rows']}")
        print(f"  Cleaned rows: {log['cleaned_rows']}")
        print(f"  Rows removed: {log['rows_removed']}")
        print(f"  Columns: {len(log['columns_original'])} → {len(log['columns_cleaned'])}")
        if log['columns_modified']:
            print(f"  Modified columns: {len(log['columns_modified'])}")
            for mod in log['columns_modified'][:5]:  # Show first 5
                print(f"    • {mod}")
            if len(log['columns_modified']) > 5:
                print(f"    ... and {len(log['columns_modified']) - 5} more")
        print(f"  Checksum: {log['checksum']}")
        print(f"  Output: {output_path.name}")
    
    print()
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    
    success_count = sum(1 for log in all_logs if log['status'] == 'success')
    error_count = sum(1 for log in all_logs if log['status'] == 'error')
    skipped_count = sum(1 for log in all_logs if log['status'] == 'skipped')
    
    print(f"Total files processed: {len(all_logs)}")
    print(f"  ✅ Success: {success_count}")
    print(f"  ❌ Errors: {error_count}")
    print(f"  ⏭️  Skipped: {skipped_count}")
    
    if success_count > 0:
        print()
        print("Cleaned files created:")
        for log in all_logs:
            if log['status'] == 'success':
                canonical = get_canonical_name(log['filename'])
                print(f"  cleaned_data/{canonical}_cleaned.csv")
    
    if error_count > 0:
        print()
        print("Errors encountered:")
        for log in all_logs:
            if log['status'] == 'error':
                print(f"  {log['filename']}: {log['error']}")
    
    print()
    print("🔒 GUARANTEE: No _cleaned_cleaned.csv files were created.")
    print("    This script only reads from raw_data/ and never reprocesses cleaned files.")
    
    return all_logs


# ---------------------------------------------------------------------------
# Main Entry Point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # Check if raw_data directory has files
    if not RAW_DATA_DIR.exists():
        print(f"Creating raw_data directory at: {RAW_DATA_DIR}")
        RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    if not any(RAW_DATA_DIR.glob("*.csv")):
        print()
        print("⚠️  The raw_data/ directory is empty!")
        print()
        print("Please copy your raw CSV files to raw_data/:")
        print("  - Abadi et al. (2023)... .csv → raw_data/")
        print("  - mmc2.csv → raw_data/")
        print("  - mental_health_finaldata_1.csv → raw_data/")
        print("  - pone.0246894.s005.csv → raw_data/")
        print("  - Static/Data/dataset.csv → raw_data/")
        print()
        print("Then run this script again: python src/clean_data.py")
        sys.exit(0)
    
    # Run the pipeline
    logs = run_cleaning_pipeline()

