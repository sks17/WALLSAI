# src/train_models.py
"""
Model Training Pipeline

This script trains ML models for mental health prediction targets
using the unified training dataset.

IMPORTANT:
- This script ONLY reads from /unified_dataset/unified_training.csv
- It trains FOUR target models: stress, depression, anxiety, sleep
- Models are saved to /models/
- Run manually: python src/train_models.py

Prerequisites:
1. Run: python setup_raw_data.py
2. Run: python src/clean_data.py
3. Run: python src/build_unified_dataset.py
4. Run: python src/train_models.py (this script)

Output:
- models/stress_model.pkl
- models/depression_model.pkl
- models/anxiety_model.pkl
- models/sleep_model.pkl
- models/preprocessors.pkl
- models/tfidf.pkl
"""
from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

import pandas as pd
import numpy as np

# Ensure project root is in path
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.utils.ml import (
    MIN_TRAINING_ROWS,
    TrainingSummary,
    train_one_target,
    save_all_artifacts,
    analyze_dataset_contributions,
    print_training_summary,
)


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

UNIFIED_DATASET_DIR = ROOT / "unified_dataset"
UNIFIED_FILE = UNIFIED_DATASET_DIR / "unified_training.csv"
MODEL_DIR = ROOT / "models"

# Target columns to train models for
TARGETS = [
    "stress_score",
    "depression_score",
    "anxiety_score", 
    "sleep_quality",
]

# Optional text column (if present in dataset)
TEXT_COLUMN = "free_text"


# ---------------------------------------------------------------------------
# Data Loading
# ---------------------------------------------------------------------------

def load_unified_dataset() -> pd.DataFrame:
    """
    Load the unified training dataset.
    
    Returns:
        DataFrame with all training data
    """
    if not UNIFIED_FILE.exists():
        raise FileNotFoundError(
            f"Unified dataset not found: {UNIFIED_FILE}\n"
            f"Please run 'python src/build_unified_dataset.py' first."
        )
    
    df = pd.read_csv(UNIFIED_FILE, encoding="utf-8", low_memory=False)
    return df


def analyze_data_quality(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Analyze the quality of the loaded dataset.
    
    Returns:
        Dict with quality metrics
    """
    analysis = {
        "total_rows": len(df),
        "total_columns": len(df.columns),
        "targets": {},
        "sources": {},
        "warnings": [],
    }
    
    # Analyze each target
    for target in TARGETS:
        if target in df.columns:
            non_null = df[target].notna().sum()
            analysis["targets"][target] = {
                "non_null_rows": non_null,
                "null_rows": len(df) - non_null,
                "coverage_pct": (non_null / len(df)) * 100 if len(df) > 0 else 0,
            }
            
            if non_null < MIN_TRAINING_ROWS:
                analysis["warnings"].append(
                    f"{target}: Only {non_null} rows (need {MIN_TRAINING_ROWS})"
                )
        else:
            analysis["targets"][target] = {"non_null_rows": 0, "null_rows": len(df), "coverage_pct": 0}
            analysis["warnings"].append(f"{target}: Column not found in dataset")
    
    # Analyze sources
    if "source_dataset" in df.columns:
        for source in df["source_dataset"].unique():
            count = (df["source_dataset"] == source).sum()
            analysis["sources"][source] = count
    
    return analysis


# ---------------------------------------------------------------------------
# Training Pipeline
# ---------------------------------------------------------------------------

def train_all_models(df: pd.DataFrame) -> tuple:
    """
    Train models for all target variables.
    
    Returns:
        (models_dict, summaries_list, preprocessors_dict, vectorizers_dict)
    """
    models = {}
    summaries = []
    preprocessors = {}
    vectorizers = {}
    
    # Check if text column exists
    text_col = TEXT_COLUMN if TEXT_COLUMN in df.columns else None
    
    for target in TARGETS:
        print(f"\n{'─' * 50}")
        print(f"Training model for: {target}")
        print(f"{'─' * 50}")
        
        # Check target availability
        if target not in df.columns:
            summary = TrainingSummary(
                target=target,
                status="skipped",
                skip_reason="Target column not in dataset"
            )
            summaries.append(summary)
            print(f"  ⏭️  Skipped: Target column not found")
            continue
        
        # Count available rows
        available_rows = df[target].notna().sum()
        print(f"  Available rows: {available_rows:,}")
        
        if available_rows < MIN_TRAINING_ROWS:
            summary = TrainingSummary(
                target=target,
                status="skipped",
                rows=available_rows,
                skip_reason=f"Insufficient rows ({available_rows} < {MIN_TRAINING_ROWS})"
            )
            summaries.append(summary)
            print(f"  ⏭️  Skipped: Insufficient rows")
            continue
        
        # Train model
        model, summary, preprocessor, vectorizer = train_one_target(
            df=df,
            target=target,
            all_targets=TARGETS,
            text_column=text_col
        )
        
        summaries.append(summary)
        
        if summary.status == "trained":
            # Use friendly names for model files
            model_name = target.replace("_score", "").replace("_quality", "")
            models[model_name] = model
            preprocessors[model_name] = preprocessor
            vectorizers[model_name] = vectorizer
            
            print(f"  ✅ Trained successfully")
            print(f"     Rows: {summary.rows:,}")
            print(f"     Features: {summary.features}")
            print(f"     MAE: {summary.mae:.4f}")
            print(f"     R²: {summary.r2:.4f}")
        else:
            print(f"  ⏭️  {summary.status}: {summary.skip_reason}")
    
    return models, summaries, preprocessors, vectorizers


# ---------------------------------------------------------------------------
# Main Entry Point
# ---------------------------------------------------------------------------

def main():
    print("=" * 70)
    print("MODEL TRAINING PIPELINE")
    print("=" * 70)
    print(f"Timestamp: {datetime.now().isoformat()}")
    print(f"Input: {UNIFIED_FILE}")
    print(f"Output: {MODEL_DIR}/")
    print()
    
    # Load data
    print("Loading unified dataset...")
    try:
        df = load_unified_dataset()
        print(f"  ✅ Loaded {len(df):,} rows, {len(df.columns)} columns")
    except FileNotFoundError as e:
        print(f"  ❌ {e}")
        sys.exit(1)
    
    # Analyze data quality
    print("\nAnalyzing data quality...")
    quality = analyze_data_quality(df)
    
    print(f"\n📊 Dataset Overview:")
    print(f"   Total rows: {quality['total_rows']:,}")
    print(f"   Total columns: {quality['total_columns']}")
    
    if quality["sources"]:
        print(f"\n   Rows per source:")
        for source, count in quality["sources"].items():
            print(f"      {source}: {count:,}")
    
    print(f"\n   Target availability:")
    for target, info in quality["targets"].items():
        coverage = info["coverage_pct"]
        non_null = info["non_null_rows"]
        status = "✅" if non_null >= MIN_TRAINING_ROWS else "⚠️"
        print(f"      {status} {target}: {non_null:,} rows ({coverage:.1f}%)")
    
    if quality["warnings"]:
        print(f"\n   ⚠️  Warnings:")
        for w in quality["warnings"]:
            print(f"      {w}")
    
    # Train models
    print("\n" + "=" * 70)
    print("TRAINING MODELS")
    print("=" * 70)
    
    models, summaries, preprocessors, vectorizers = train_all_models(df)
    
    # Save artifacts
    print("\n" + "=" * 70)
    print("SAVING ARTIFACTS")
    print("=" * 70)
    
    if models:
        saved_files = save_all_artifacts(models, preprocessors, vectorizers, MODEL_DIR)
        print(f"\n✅ Saved {len(saved_files)} artifact(s) to {MODEL_DIR}/")
    else:
        saved_files = []
        print("\n⚠️  No models to save")
    
    # Analyze contributions
    contributions = analyze_dataset_contributions(df, TARGETS)
    
    # Print final summary
    print_training_summary(summaries, contributions, saved_files)
    
    # Return success status
    trained_count = sum(1 for s in summaries if s.status == "trained")
    return trained_count > 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

