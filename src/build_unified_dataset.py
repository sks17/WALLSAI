# src/build_unified_dataset.py
"""
Unified Dataset Builder

This script reads cleaned CSV files from /cleaned_data/ and produces
a unified training dataset at /unified_dataset/unified_training.csv.

IMPORTANT:
- This script ONLY reads from /cleaned_data/
- It does NOT read from newData/, _cleaned_cleaned.csv, or legacy paths
- It does NOT perform cleaning — only mapping and scoring
- Run manually: python src/build_unified_dataset.py

Expected input files in /cleaned_data/:
- abadi_cleaned.csv
- mmc2_cleaned.csv
- mental_health_finaldata_cleaned.csv
- pone_stress_cleaned.csv
- dataset_cleaned.csv (legacy model input)

Output:
- /unified_dataset/unified_training.csv
"""
from __future__ import annotations

import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

import pandas as pd
import numpy as np

# Ensure project root is in path
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.utils.mapper import (
    CANONICAL_COLUMNS,
    ColumnDiagnostics,
    build_unified_dataframe,
    detect_columns,
    print_diagnostics,
)


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

CLEANED_DATA_DIR = ROOT / "cleaned_data"
UNIFIED_DATASET_DIR = ROOT / "unified_dataset"
OUTPUT_FILE = UNIFIED_DATASET_DIR / "unified_training.csv"

# Expected cleaned files and their canonical names
EXPECTED_FILES = {
    "abadi_cleaned.csv": "abadi",
    "mmc2_cleaned.csv": "mmc2",
    "mental_health_finaldata_cleaned.csv": "mental_health_finaldata",
    "pone_stress_cleaned.csv": "pone_stress",
    "dataset_cleaned.csv": "dataset",
}


# ---------------------------------------------------------------------------
# Data Loading
# ---------------------------------------------------------------------------

def load_cleaned_datasets() -> List[Tuple[pd.DataFrame, str]]:
    """
    Load all cleaned datasets from /cleaned_data/.
    
    Returns:
        List of (DataFrame, source_name) tuples
    """
    datasets = []
    
    if not CLEANED_DATA_DIR.exists():
        print(f"❌ Cleaned data directory not found: {CLEANED_DATA_DIR}")
        print("   Run 'python src/clean_data.py' first to generate cleaned files.")
        return datasets
    
    # List available files
    available_files = list(CLEANED_DATA_DIR.glob("*_cleaned.csv"))
    
    if not available_files:
        print(f"❌ No cleaned files found in {CLEANED_DATA_DIR}")
        print("   Run 'python src/clean_data.py' first to generate cleaned files.")
        return datasets
    
    print(f"📂 Scanning {CLEANED_DATA_DIR}")
    print(f"   Found {len(available_files)} cleaned file(s):")
    
    for filepath in sorted(available_files):
        filename = filepath.name
        
        # Skip any double-cleaned files (should not exist in new pipeline)
        if "_cleaned_cleaned" in filename.lower():
            print(f"   ⏭️  Skipping (double-cleaned): {filename}")
            continue
        
        # Get canonical name
        source_name = EXPECTED_FILES.get(filename, filepath.stem)
        
        print(f"   📄 Loading: {filename} → source='{source_name}'")
        
        try:
            df = pd.read_csv(filepath, encoding="utf-8", low_memory=False)
            datasets.append((df, source_name))
        except Exception as e:
            print(f"   ❌ Error loading {filename}: {e}")
    
    return datasets


# ---------------------------------------------------------------------------
# Main Pipeline
# ---------------------------------------------------------------------------

def build_unified_dataset() -> Tuple[pd.DataFrame, List[ColumnDiagnostics]]:
    """
    Build the unified training dataset from all cleaned files.
    
    Returns:
        (unified_dataframe, list_of_diagnostics)
    """
    print("=" * 70)
    print("UNIFIED DATASET BUILDER")
    print("=" * 70)
    print(f"Timestamp: {datetime.now().isoformat()}")
    print(f"Input directory: {CLEANED_DATA_DIR}")
    print(f"Output file: {OUTPUT_FILE}")
    print()
    
    # Load all cleaned datasets
    datasets = load_cleaned_datasets()
    
    if not datasets:
        print("\n❌ No datasets to process. Exiting.")
        return pd.DataFrame(), []
    
    print()
    print("-" * 70)
    print("MAPPING & SCORING")
    print("-" * 70)
    
    all_unified = []
    all_diagnostics = []
    
    for df, source_name in datasets:
        # Build unified DataFrame for this dataset
        unified_df, diag = build_unified_dataframe(df, source_name)
        
        all_unified.append(unified_df)
        all_diagnostics.append(diag)
        
        # Print diagnostics
        print_diagnostics(diag)
    
    # Concatenate all unified DataFrames
    print()
    print("-" * 70)
    print("MERGING DATASETS")
    print("-" * 70)
    
    if not all_unified:
        print("❌ No data to merge.")
        return pd.DataFrame(), all_diagnostics
    
    unified = pd.concat(all_unified, ignore_index=True)
    
    print(f"\nTotal rows before filtering: {len(unified):,}")
    
    # Count rows per source
    source_counts = unified["source_dataset"].value_counts()
    print("\nRows per source dataset:")
    for source, count in source_counts.items():
        print(f"   {source}: {count:,} rows")
    
    # Count non-null targets
    print("\nTarget coverage (rows with non-null values):")
    for target in ["depression_score", "anxiety_score", "stress_score", "sleep_quality", "disorder"]:
        non_null = unified[target].notna().sum()
        pct = (non_null / len(unified)) * 100 if len(unified) > 0 else 0
        print(f"   {target}: {non_null:,} rows ({pct:.1f}%)")
    
    # DO NOT drop rows globally - that happens during training
    # Only note if rows have NO useful information at all
    all_targets = ["depression_score", "anxiety_score", "stress_score", "sleep_quality", "disorder"]
    rows_with_any_target = unified[all_targets].notna().any(axis=1).sum()
    rows_no_target = len(unified) - rows_with_any_target
    
    if rows_no_target > 0:
        print(f"\n⚠️  {rows_no_target:,} rows have no target values (will be filtered during training)")
    
    return unified, all_diagnostics


def save_unified_dataset(unified: pd.DataFrame):
    """Save the unified dataset to disk."""
    # Ensure output directory exists
    UNIFIED_DATASET_DIR.mkdir(parents=True, exist_ok=True)
    
    # Save
    unified.to_csv(OUTPUT_FILE, index=False, encoding="utf-8")
    
    print()
    print("-" * 70)
    print("OUTPUT")
    print("-" * 70)
    print(f"✅ Saved unified dataset to: {OUTPUT_FILE}")
    print(f"   Total rows: {len(unified):,}")
    print(f"   Total columns: {len(unified.columns)}")
    print()
    print("Columns in unified dataset:")
    for col in unified.columns:
        non_null = unified[col].notna().sum()
        print(f"   {col}: {non_null:,} non-null values")


def print_summary(unified: pd.DataFrame, diagnostics: List[ColumnDiagnostics]):
    """Print final summary."""
    print()
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    
    print(f"\nDatasets processed: {len(diagnostics)}")
    for diag in diagnostics:
        print(f"   • {diag.source_name}: {diag.total_rows:,} rows")
    
    print(f"\nUnified dataset: {len(unified):,} total rows")
    
    # Target contributions
    print("\nTarget score contributions by dataset:")
    for diag in diagnostics:
        print(f"\n   {diag.source_name}:")
        if diag.rows_with_depression > 0:
            print(f"      Depression (PHQ-9): {diag.rows_with_depression:,}")
        if diag.rows_with_anxiety > 0:
            print(f"      Anxiety (GAD-7): {diag.rows_with_anxiety:,}")
        if diag.rows_with_stress > 0:
            print(f"      Stress: {diag.rows_with_stress:,}")
        if diag.rows_with_sleep > 0:
            print(f"      Sleep: {diag.rows_with_sleep:,}")
        if diag.rows_with_disorder > 0:
            print(f"      Disorder: {diag.rows_with_disorder:,}")
    
    # Check for datasets contributing zero to any target
    print("\n⚠️  Zero-contribution warnings:")
    any_warning = False
    for diag in diagnostics:
        if diag.rows_with_depression == 0 and diag.rows_with_anxiety == 0 and \
           diag.rows_with_stress == 0 and diag.rows_with_sleep == 0 and \
           diag.rows_with_disorder == 0:
            print(f"   ⚠️  {diag.source_name} contributes 0 rows to ALL targets")
            any_warning = True
    
    if not any_warning:
        print("   (none)")
    
    print()
    print("=" * 70)
    print("NEXT STEPS")
    print("=" * 70)
    print("The unified dataset is ready for training.")
    print("Run: python src/train_models.py")
    print()
    print("The training script will:")
    print("   • Load unified_dataset/unified_training.csv")
    print("   • Train separate models for each target")
    print("   • Filter rows per-target (only during training)")
    print("   • Save models to /models/")


# ---------------------------------------------------------------------------
# Main Entry Point
# ---------------------------------------------------------------------------

def main():
    # Check prerequisites
    if not CLEANED_DATA_DIR.exists():
        print(f"❌ Directory not found: {CLEANED_DATA_DIR}")
        print()
        print("Please run the cleaning pipeline first:")
        print("   1. python setup_raw_data.py    (copy raw files)")
        print("   2. python src/clean_data.py    (clean files)")
        print("   3. python src/build_unified_dataset.py  (this script)")
        sys.exit(1)
    
    # Build unified dataset
    unified, diagnostics = build_unified_dataset()
    
    if unified.empty:
        print("\n❌ Failed to build unified dataset.")
        sys.exit(1)
    
    # Save
    save_unified_dataset(unified)
    
    # Print summary
    print_summary(unified, diagnostics)
    
    # Preview
    print()
    print("-" * 70)
    print("PREVIEW (first 5 rows)")
    print("-" * 70)
    pd.set_option('display.max_columns', 10)
    pd.set_option('display.width', 120)
    print(unified.head().to_string())


if __name__ == "__main__":
    main()

