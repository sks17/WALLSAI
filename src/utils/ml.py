# src/utils/ml.py
"""
Machine Learning Utilities

This module provides modular ML utilities for the training pipeline:
- Preprocessing pipelines (numeric + categorical)
- TF-IDF vectorization (with safe fallback)
- Training matrix construction
- Model training and evaluation
- Model saving/loading
"""
from __future__ import annotations

import os
import pickle
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd
from pandas.api.types import is_numeric_dtype
from scipy.sparse import hstack, issparse
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.impute import SimpleImputer
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.feature_extraction.text import TfidfVectorizer


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Minimum rows required to train a model
MIN_TRAINING_ROWS = 20

# Columns to exclude from features
METADATA_COLUMNS = ["source_dataset"]


# ---------------------------------------------------------------------------
# Training Summary Data Class
# ---------------------------------------------------------------------------

@dataclass
class TrainingSummary:
    """Summary of training a single model."""
    target: str
    status: str = "pending"  # "trained", "skipped", "error"
    rows: int = 0
    features: int = 0
    mae: Optional[float] = None
    rmse: Optional[float] = None
    r2: Optional[float] = None
    skip_reason: Optional[str] = None
    warnings: List[str] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict:
        return {
            "target": self.target,
            "status": self.status,
            "rows": self.rows,
            "features": self.features,
            "mae": self.mae,
            "rmse": self.rmse,
            "r2": self.r2,
            "skip_reason": self.skip_reason,
            "warnings": self.warnings,
        }


# ---------------------------------------------------------------------------
# Preprocessing
# ---------------------------------------------------------------------------

def identify_column_types(
    df: pd.DataFrame, 
    target_columns: List[str],
    text_column: Optional[str] = None
) -> Tuple[List[str], List[str], bool]:
    """
    Identify numeric and categorical feature columns.
    
    Args:
        df: Input DataFrame
        target_columns: Columns to exclude (targets + metadata)
        text_column: Optional text column name to exclude
    
    Returns:
        (numeric_columns, categorical_columns, text_present)
    """
    exclude = set(target_columns + METADATA_COLUMNS)
    if text_column:
        exclude.add(text_column)
    
    feature_cols = [c for c in df.columns if c not in exclude]
    
    numeric_cols = []
    categorical_cols = []
    
    for col in feature_cols:
        if is_numeric_dtype(df[col]):
            numeric_cols.append(col)
        elif df[col].dtype == object:
            categorical_cols.append(col)
    
    text_present = text_column is not None and text_column in df.columns
    
    return numeric_cols, categorical_cols, text_present


def build_preprocessor(
    numeric_columns: List[str],
    categorical_columns: List[str]
) -> ColumnTransformer:
    """
    Build a preprocessing pipeline for tabular features.
    
    Handles:
    - Numeric columns: median imputation + standard scaling
    - Categorical columns: most_frequent imputation + one-hot encoding
    
    Args:
        numeric_columns: List of numeric column names
        categorical_columns: List of categorical column names
    
    Returns:
        Fitted ColumnTransformer
    """
    transformers = []
    
    if numeric_columns:
        numeric_pipeline = Pipeline([
            ("impute", SimpleImputer(strategy="median")),
            ("scale", StandardScaler()),
        ])
        transformers.append(("num", numeric_pipeline, numeric_columns))
    
    if categorical_columns:
        categorical_pipeline = Pipeline([
            ("impute", SimpleImputer(strategy="most_frequent")),
            ("onehot", OneHotEncoder(handle_unknown="ignore", sparse_output=True)),
        ])
        transformers.append(("cat", categorical_pipeline, categorical_columns))
    
    preprocessor = ColumnTransformer(
        transformers=transformers,
        remainder="drop",
    )
    
    return preprocessor


def build_tfidf_vectorizer(
    texts: Optional[pd.Series] = None,
    max_features: int = 200
) -> TfidfVectorizer:
    """
    Build and fit a TF-IDF vectorizer.
    
    If no valid texts are provided, fits on a dummy token to avoid
    empty vocabulary errors.
    
    Args:
        texts: Optional Series of text data
        max_features: Maximum vocabulary size
    
    Returns:
        Fitted TfidfVectorizer
    """
    vectorizer = TfidfVectorizer(max_features=max_features)
    
    if texts is None:
        # No text column - fit on dummy
        vectorizer.fit(["noop"])
        return vectorizer
    
    # Clean texts
    cleaned = texts.fillna("").astype(str).str.strip().tolist()
    valid_texts = [t for t in cleaned if t]
    
    if not valid_texts:
        # All texts empty - fit on dummy
        vectorizer.fit(["noop"])
        return vectorizer
    
    vectorizer.fit(valid_texts)
    return vectorizer


# ---------------------------------------------------------------------------
# Training Matrix Construction
# ---------------------------------------------------------------------------

def build_training_matrix(
    df: pd.DataFrame,
    preprocessor: ColumnTransformer,
    vectorizer: Optional[TfidfVectorizer] = None,
    text_column: Optional[str] = None,
    fit_preprocessor: bool = True
) -> Tuple[np.ndarray, int]:
    """
    Build the feature matrix for training.
    
    Args:
        df: Input DataFrame (already filtered for target)
        preprocessor: ColumnTransformer for tabular features
        vectorizer: Optional TfidfVectorizer for text
        text_column: Name of text column (if any)
        fit_preprocessor: Whether to fit the preprocessor
    
    Returns:
        (feature_matrix, feature_count)
    """
    # Transform tabular features
    if fit_preprocessor:
        X_tab = preprocessor.fit_transform(df)
    else:
        X_tab = preprocessor.transform(df)
    
    # Handle text features if present
    if vectorizer is not None and text_column and text_column in df.columns:
        texts = df[text_column].fillna("").astype(str)
        try:
            X_text = vectorizer.transform(texts)
        except Exception:
            # Fallback: create zero matrix
            X_text = np.zeros((len(df), 1))
        
        # Combine tabular and text features
        if issparse(X_tab):
            X_all = hstack([X_tab, X_text])
        else:
            X_all = np.hstack([X_tab, X_text.toarray() if issparse(X_text) else X_text])
    else:
        X_all = X_tab
    
    # Convert to dense if needed for HistGradientBoosting
    if issparse(X_all):
        X_all = X_all.toarray()
    
    return X_all, X_all.shape[1]


# ---------------------------------------------------------------------------
# Model Training
# ---------------------------------------------------------------------------

def train_one_target(
    df: pd.DataFrame,
    target: str,
    all_targets: List[str],
    text_column: Optional[str] = None
) -> Tuple[Optional[Any], TrainingSummary, ColumnTransformer, Optional[TfidfVectorizer]]:
    """
    Train a model for a single target variable.
    
    Args:
        df: Full unified DataFrame
        target: Target column name
        all_targets: List of all target columns (to exclude from features)
        text_column: Optional text column name
    
    Returns:
        (model, summary, preprocessor, vectorizer)
    """
    summary = TrainingSummary(target=target)
    
    # Filter to rows with valid target
    df_target = df.dropna(subset=[target]).copy()
    
    if len(df_target) == 0:
        summary.status = "skipped"
        summary.skip_reason = "No rows with valid target values"
        return None, summary, None, None
    
    # Convert target to numeric
    y = pd.to_numeric(df_target[target], errors="coerce")
    valid_mask = y.notna()
    df_target = df_target[valid_mask]
    y = y[valid_mask]
    
    if len(df_target) < MIN_TRAINING_ROWS:
        summary.status = "skipped"
        summary.skip_reason = f"Insufficient rows ({len(df_target)} < {MIN_TRAINING_ROWS})"
        summary.rows = len(df_target)
        return None, summary, None, None
    
    summary.rows = len(df_target)
    
    # Identify column types
    numeric_cols, cat_cols, text_present = identify_column_types(
        df_target, all_targets, text_column
    )
    
    if not numeric_cols and not cat_cols:
        summary.status = "skipped"
        summary.skip_reason = "No feature columns found"
        return None, summary, None, None
    
    # Log column info
    if not numeric_cols:
        summary.warnings.append("No numeric columns found")
    if not cat_cols:
        summary.warnings.append("No categorical columns found")
    
    # Build preprocessor
    preprocessor = build_preprocessor(numeric_cols, cat_cols)
    
    # Build TF-IDF vectorizer
    vectorizer = None
    if text_present and text_column in df_target.columns:
        vectorizer = build_tfidf_vectorizer(df_target[text_column])
    else:
        vectorizer = build_tfidf_vectorizer(None)  # Dummy vectorizer
    
    # Build training matrix
    try:
        X, feature_count = build_training_matrix(
            df_target, preprocessor, vectorizer, text_column, fit_preprocessor=True
        )
        summary.features = feature_count
    except Exception as e:
        summary.status = "error"
        summary.skip_reason = f"Failed to build features: {str(e)}"
        return None, summary, preprocessor, vectorizer
    
    # Train model
    model = HistGradientBoostingRegressor(
        max_depth=6,
        learning_rate=0.05,
        max_iter=100,
        random_state=42
    )
    
    try:
        model.fit(X, y)
        
        # Evaluate on training set
        predictions = model.predict(X)
        summary.mae = mean_absolute_error(y, predictions)
        summary.rmse = np.sqrt(mean_squared_error(y, predictions))
        summary.r2 = r2_score(y, predictions)
        summary.status = "trained"
        
    except Exception as e:
        summary.status = "error"
        summary.skip_reason = f"Training failed: {str(e)}"
        return None, summary, preprocessor, vectorizer
    
    return model, summary, preprocessor, vectorizer


# ---------------------------------------------------------------------------
# Model Evaluation
# ---------------------------------------------------------------------------

def evaluate_model(
    model: Any,
    X: np.ndarray,
    y: np.ndarray
) -> Dict[str, float]:
    """
    Evaluate a trained model.
    
    Returns:
        Dict with mae, rmse, r2 metrics
    """
    predictions = model.predict(X)
    
    return {
        "mae": mean_absolute_error(y, predictions),
        "rmse": np.sqrt(mean_squared_error(y, predictions)),
        "r2": r2_score(y, predictions),
    }


# ---------------------------------------------------------------------------
# Model Persistence
# ---------------------------------------------------------------------------

def save_model(model: Any, filepath: Path) -> None:
    """Save a model to disk using pickle."""
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, "wb") as f:
        pickle.dump(model, f)


def load_model(filepath: Path) -> Any:
    """Load a model from disk."""
    with open(filepath, "rb") as f:
        return pickle.load(f)


def extract_feature_metadata(
    preprocessor: ColumnTransformer,
    vectorizer: Optional[TfidfVectorizer],
    model: Any
) -> Dict[str, Any]:
    """
    Extract feature metadata from trained artifacts for inference alignment.
    
    This metadata is the SOURCE OF TRUTH for feature structure at inference time.
    """
    metadata = {
        "numeric_columns": [],
        "categorical_columns": [],
        "all_tabular_columns": [],
        "n_tabular_features": 0,
        "n_text_features": 0,
        "n_total_features": 0,
    }
    
    # Extract columns from ColumnTransformer
    if hasattr(preprocessor, 'transformers_'):
        for name, transformer, columns in preprocessor.transformers_:
            if name == 'remainder':
                continue
            if isinstance(columns, (list, np.ndarray)):
                cols_list = list(columns)
            elif isinstance(columns, str):
                cols_list = [columns]
            else:
                cols_list = []
            
            if name == 'num':
                metadata["numeric_columns"] = cols_list
            elif name == 'cat':
                metadata["categorical_columns"] = cols_list
    
    metadata["all_tabular_columns"] = (
        metadata["numeric_columns"] + metadata["categorical_columns"]
    )
    
    # Get total features from model
    if hasattr(model, 'n_features_in_'):
        metadata["n_total_features"] = model.n_features_in_
    
    # Get TF-IDF features
    if vectorizer is not None and hasattr(vectorizer, 'vocabulary_'):
        metadata["n_text_features"] = len(vectorizer.vocabulary_)
    
    # Calculate tabular features
    metadata["n_tabular_features"] = (
        metadata["n_total_features"] - metadata["n_text_features"]
    )
    
    return metadata


def save_all_artifacts(
    models: Dict[str, Any],
    preprocessors: Dict[str, ColumnTransformer],
    vectorizers: Dict[str, TfidfVectorizer],
    model_dir: Path
) -> List[str]:
    """
    Save all training artifacts to disk.
    
    Also saves feature metadata for deterministic inference alignment.
    
    Args:
        models: Dict of {target_name: model}
        preprocessors: Dict of {target_name: preprocessor}
        vectorizers: Dict of {target_name: vectorizer}
        model_dir: Directory to save to
    
    Returns:
        List of saved file paths
    """
    import json
    
    model_dir.mkdir(parents=True, exist_ok=True)
    saved_files = []
    
    # Save individual models
    for name, model in models.items():
        if model is not None:
            filepath = model_dir / f"{name}_model.pkl"
            save_model(model, filepath)
            saved_files.append(str(filepath))
    
    # Save preprocessors (one per target)
    preprocessors_path = model_dir / "preprocessors.pkl"
    with open(preprocessors_path, "wb") as f:
        pickle.dump(preprocessors, f)
    saved_files.append(str(preprocessors_path))
    
    # Save vectorizers
    vectorizers_path = model_dir / "tfidf.pkl"
    with open(vectorizers_path, "wb") as f:
        pickle.dump(vectorizers, f)
    saved_files.append(str(vectorizers_path))
    
    # Save feature metadata for inference alignment
    feature_metadata = {}
    for name, model in models.items():
        if model is not None:
            preprocessor = preprocessors.get(name)
            vectorizer = vectorizers.get(name)
            if preprocessor:
                feature_metadata[name] = extract_feature_metadata(
                    preprocessor, vectorizer, model
                )
    
    metadata_path = model_dir / "feature_metadata.json"
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(feature_metadata, f, indent=2)
    saved_files.append(str(metadata_path))
    
    return saved_files


# ---------------------------------------------------------------------------
# Diagnostics & Reporting
# ---------------------------------------------------------------------------

def analyze_dataset_contributions(
    df: pd.DataFrame,
    targets: List[str]
) -> Dict[str, Dict[str, int]]:
    """
    Analyze how many rows each source dataset contributes per target.
    
    Returns:
        Dict of {target: {source: row_count}}
    """
    if "source_dataset" not in df.columns:
        return {}
    
    contributions = {}
    for target in targets:
        contributions[target] = {}
        for source in df["source_dataset"].unique():
            source_df = df[df["source_dataset"] == source]
            valid_count = source_df[target].notna().sum()
            contributions[target][source] = valid_count
    
    return contributions


def print_training_summary(
    summaries: List[TrainingSummary],
    contributions: Dict[str, Dict[str, int]],
    saved_files: List[str]
):
    """Print a formatted training summary."""
    print()
    print("=" * 70)
    print("TRAINING SUMMARY")
    print("=" * 70)
    
    # Summary table
    print("\n📊 Model Training Results:")
    print("-" * 70)
    print(f"{'Target':<20} {'Status':<10} {'Rows':>8} {'Features':>10} {'MAE':>10} {'R²':>8}")
    print("-" * 70)
    
    for s in summaries:
        mae_str = f"{s.mae:.4f}" if s.mae is not None else "N/A"
        r2_str = f"{s.r2:.4f}" if s.r2 is not None else "N/A"
        status_emoji = "✅" if s.status == "trained" else "⏭️" if s.status == "skipped" else "❌"
        print(f"{s.target:<20} {status_emoji} {s.status:<8} {s.rows:>8} {s.features:>10} {mae_str:>10} {r2_str:>8}")
    
    print("-" * 70)
    
    # Warnings
    any_warnings = False
    for s in summaries:
        if s.skip_reason:
            if not any_warnings:
                print("\n⚠️  Skipped Models:")
                any_warnings = True
            print(f"   {s.target}: {s.skip_reason}")
        for w in s.warnings:
            if not any_warnings:
                print("\n⚠️  Warnings:")
                any_warnings = True
            print(f"   {s.target}: {w}")
    
    # Dataset contributions
    if contributions:
        print("\n📊 Dataset Contributions per Target:")
        for target, sources in contributions.items():
            print(f"\n   {target}:")
            for source, count in sources.items():
                status = "⚠️ 0 rows" if count == 0 else f"{count:,} rows"
                print(f"      {source}: {status}")
    
    # Saved files
    print("\n📁 Saved Artifacts:")
    for f in saved_files:
        print(f"   {f}")
    
    # Final status
    trained_count = sum(1 for s in summaries if s.status == "trained")
    total_count = len(summaries)
    
    print()
    print("=" * 70)
    if trained_count == total_count:
        print(f"✅ All {total_count} models trained successfully!")
    elif trained_count > 0:
        print(f"⚠️  {trained_count}/{total_count} models trained. See warnings above.")
    else:
        print(f"❌ No models were trained. Check data availability.")
    print("=" * 70)

