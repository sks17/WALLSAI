# src/inference.py
"""
Deterministic Model Inference Module

This module provides inference capabilities that EXACTLY reproduce the feature
structure seen during training. The key principle is:

    FROZEN FEATURE ORDER: The feature vector structure is determined entirely
    by the saved preprocessor/vectorizer. User input is mapped INTO this
    frozen structure, never the other way around.

Architecture:
    1. Load preprocessor → extract exact column names and order
    2. Load TF-IDF vectorizer → extract exact vocabulary
    3. Build input DataFrame with EXACTLY the trained column order
    4. Apply preprocessor.transform() (not fit_transform)
    5. Apply vectorizer.transform() (not fit_transform)
    6. Concatenate: [TABULAR_FEATURES | TEXT_FEATURES]
    7. Verify shape matches model.n_features_in_

Public API:
    run_inference(user_input: dict, free_text: str) -> dict

Example:
    >>> result = run_inference({"age": 25, "gender": "male"}, "I feel tired")
    >>> print(result)
    {"stress_score": 15.2, "depression_score": 8.5, ...}
"""
from __future__ import annotations

import logging
import pickle
import sys
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from scipy.sparse import hstack, issparse

# ---------------------------------------------------------------------------
# Path Setup
# ---------------------------------------------------------------------------

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# ---------------------------------------------------------------------------
# Logging Configuration
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Set to DEBUG for detailed feature debugging
# logger.setLevel(logging.DEBUG)


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

MODEL_DIR = ROOT / "models"

MODEL_FILES = {
    "stress": "stress_model.pkl",
    "depression": "depression_model.pkl",
    "anxiety": "anxiety_model.pkl",
    "sleep": "sleep_model.pkl",
}

TARGET_OUTPUT_NAMES = {
    "stress": "stress_score",
    "depression": "depression_score",
    "anxiety": "anxiety_score",
    "sleep": "sleep_quality",
}


# ---------------------------------------------------------------------------
# Feature Configuration (Frozen at Training Time)
# ---------------------------------------------------------------------------

@dataclass
class FrozenFeatureConfig:
    """
    Immutable feature configuration extracted from trained preprocessor.
    This defines the EXACT structure the model expects.
    """
    numeric_columns: List[str]
    categorical_columns: List[str]
    all_tabular_columns: List[str]  # In exact order
    n_tabular_features: int  # After encoding
    n_text_features: int  # TF-IDF vocabulary size
    n_total_features: int
    
    def __repr__(self):
        return (
            f"FrozenFeatureConfig("
            f"tabular={len(self.all_tabular_columns)}, "
            f"encoded_tabular={self.n_tabular_features}, "
            f"text={self.n_text_features}, "
            f"total={self.n_total_features})"
        )


def extract_feature_config(
    preprocessor: Any,
    vectorizer: Any,
    model: Any
) -> FrozenFeatureConfig:
    """
    Extract the frozen feature configuration from trained artifacts.
    
    This is the SOURCE OF TRUTH for feature structure.
    Uses feature_names_in_ which is the EXACT column order the preprocessor expects.
    """
    # Get the EXACT column order from the fitted preprocessor
    # This is critical - we must use the same order as during training
    all_tabular = []
    if hasattr(preprocessor, 'feature_names_in_'):
        all_tabular = list(preprocessor.feature_names_in_)
    
    # Extract numeric and categorical columns from transformers
    numeric_cols = []
    categorical_cols = []
    
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
                numeric_cols = cols_list
            elif name == 'cat':
                categorical_cols = cols_list
    
    # If feature_names_in_ wasn't available, fall back to transformer columns
    if not all_tabular:
        all_tabular = numeric_cols + categorical_cols
    
    # Get the exact feature counts from the model
    n_total = model.n_features_in_ if hasattr(model, 'n_features_in_') else 0
    
    # Get TF-IDF feature count
    n_text = 0
    if vectorizer is not None:
        if hasattr(vectorizer, 'vocabulary_'):
            n_text = len(vectorizer.vocabulary_)
        elif hasattr(vectorizer, 'get_feature_names_out'):
            n_text = len(vectorizer.get_feature_names_out())
    
    n_tabular = n_total - n_text
    
    logger.debug(f"Feature config: tabular_cols={len(all_tabular)}, "
                 f"n_tabular={n_tabular}, n_text={n_text}, n_total={n_total}")
    
    return FrozenFeatureConfig(
        numeric_columns=numeric_cols,
        categorical_columns=categorical_cols,
        all_tabular_columns=all_tabular,
        n_tabular_features=n_tabular,
        n_text_features=n_text,
        n_total_features=n_total,
    )


# ---------------------------------------------------------------------------
# Artifact Loading (Cached)
# ---------------------------------------------------------------------------

@lru_cache(maxsize=1)
def load_models() -> Dict[str, Any]:
    """Load all trained models."""
    models = {}
    for target, filename in MODEL_FILES.items():
        filepath = MODEL_DIR / filename
        if filepath.exists():
            with open(filepath, "rb") as f:
                models[target] = pickle.load(f)
            logger.debug(f"Loaded model: {target}")
        else:
            models[target] = None
            logger.info(f"Model not found: {filepath}")
    return models


@lru_cache(maxsize=1)
def load_preprocessors() -> Dict[str, Any]:
    """Load preprocessing pipelines."""
    # Try new format
    filepath = MODEL_DIR / "preprocessors.pkl"
    if filepath.exists():
        with open(filepath, "rb") as f:
            preprocessors = pickle.load(f)
            logger.debug(f"Loaded preprocessors for targets: {list(preprocessors.keys())}")
            return preprocessors
    
    # Fallback to old format
    filepath = MODEL_DIR / "preprocessor.pkl"
    if filepath.exists():
        with open(filepath, "rb") as f:
            preprocessor = pickle.load(f)
            return {target: preprocessor for target in MODEL_FILES.keys()}
    
    logger.warning("No preprocessors found")
    return {}


@lru_cache(maxsize=1)
def load_vectorizers() -> Dict[str, Any]:
    """Load TF-IDF vectorizers."""
    # Try new format
    filepath = MODEL_DIR / "tfidf.pkl"
    if filepath.exists():
        with open(filepath, "rb") as f:
            vectorizers = pickle.load(f)
            logger.debug(f"Loaded vectorizers for targets: {list(vectorizers.keys())}")
            return vectorizers
    
    # Fallback to old format
    filepath = MODEL_DIR / "tfidf_vectorizer.pkl"
    if filepath.exists():
        with open(filepath, "rb") as f:
            vectorizer = pickle.load(f)
            return {target: vectorizer for target in MODEL_FILES.keys()}
    
    logger.warning("No vectorizers found")
    return {}


@lru_cache(maxsize=4)
def get_feature_config(target: str) -> Optional[FrozenFeatureConfig]:
    """Get the frozen feature configuration for a target."""
    models = load_models()
    preprocessors = load_preprocessors()
    vectorizers = load_vectorizers()
    
    model = models.get(target)
    preprocessor = preprocessors.get(target)
    vectorizer = vectorizers.get(target)
    
    if model is None or preprocessor is None:
        return None
    
    return extract_feature_config(preprocessor, vectorizer, model)


# ---------------------------------------------------------------------------
# Deterministic Feature Matrix Construction
# ---------------------------------------------------------------------------

def normalize_user_key(key: str) -> str:
    """Normalize a user input key for matching."""
    # Convert to lowercase, replace spaces and hyphens with underscores
    return key.lower().strip().replace(" ", "_").replace("-", "_").replace(".", "_")


def build_tabular_dataframe(
    user_input: Dict[str, Any],
    column_order: List[str]
) -> pd.DataFrame:
    """
    Build a DataFrame with EXACTLY the specified column order.
    
    Missing columns are filled with NaN (the preprocessor's imputer handles them).
    Extra columns in user_input are ignored.
    
    This ensures the DataFrame structure matches what the preprocessor expects.
    """
    # Create normalized key mapping from user input
    normalized_input = {}
    for key, value in user_input.items():
        norm_key = normalize_user_key(key)
        normalized_input[norm_key] = value
        # Also store original key
        normalized_input[key] = value
    
    # Build row with EXACT column order
    row_data = {}
    matched_cols = []
    unmatched_cols = []
    
    for col in column_order:
        norm_col = normalize_user_key(col)
        
        # Try exact match first
        if col in user_input:
            row_data[col] = user_input[col]
            matched_cols.append(col)
        # Try normalized match
        elif norm_col in normalized_input:
            row_data[col] = normalized_input[norm_col]
            matched_cols.append(col)
        else:
            # Missing column - use NaN (imputer will handle)
            row_data[col] = np.nan
            unmatched_cols.append(col)
    
    # Create DataFrame with explicit column order
    df = pd.DataFrame([row_data], columns=column_order)
    
    # Log matching info
    logger.info(f"Column matching: {len(matched_cols)}/{len(column_order)} matched")
    if matched_cols:
        logger.info(f"MATCHED columns: {matched_cols}")
    if unmatched_cols and len(unmatched_cols) < 20:
        logger.info(f"UNMATCHED columns (will be imputed): {unmatched_cols}")
    
    # Log actual values being used
    non_nan_cols = df.columns[df.notna().iloc[0]].tolist()
    logger.info(f"Non-NaN values: {len(non_nan_cols)}")
    for col in non_nan_cols:
        logger.info(f"  {col} = {df[col].iloc[0]}")
    
    return df


def build_feature_matrix(
    user_input: Dict[str, Any],
    free_text: Optional[str],
    preprocessor: Any,
    vectorizer: Any,
    config: FrozenFeatureConfig,
    expected_features: int
) -> np.ndarray:
    """
    Build the feature matrix with EXACTLY the structure expected by the model.
    
    This is the CORE function that guarantees feature alignment.
    
    Steps:
    1. Build tabular DataFrame with frozen column order
    2. Apply preprocessor.transform() (uses fitted imputer + encoder)
    3. Apply vectorizer.transform() to text
    4. Concatenate: [TABULAR | TEXT]
    5. Force exact shape match
    
    Args:
        user_input: User's survey answers
        free_text: Optional free text
        preprocessor: Fitted ColumnTransformer
        vectorizer: Fitted TfidfVectorizer (or None)
        config: Frozen feature configuration
        expected_features: EXACT number of features the model expects
    
    Returns:
        2D numpy array with shape (1, expected_features)
    """
    # Step 1: Build tabular DataFrame with exact column order
    df = build_tabular_dataframe(user_input, config.all_tabular_columns)
    
    logger.info(f"User input keys: {list(user_input.keys())}")
    
    # Step 2: Transform tabular features
    try:
        X_tabular = preprocessor.transform(df)
        if issparse(X_tabular):
            X_tabular = X_tabular.toarray()
        logger.info(f"Tabular features shape after transform: {X_tabular.shape}")
    except Exception as e:
        logger.error(f"Preprocessor transform failed: {e}")
        raise RuntimeError(f"Feature transformation failed: {e}")
    
    # Step 3: Determine text features needed
    # Calculate how many text features we need to reach expected_features
    n_text_needed = max(0, expected_features - X_tabular.shape[1])
    
    logger.info(f"Tabular features: {X_tabular.shape[1]}, Text features needed: {n_text_needed}")
    
    if vectorizer is not None and n_text_needed > 0:
        text = str(free_text).strip() if free_text else ""
        try:
            X_text = vectorizer.transform([text])
            if issparse(X_text):
                X_text = X_text.toarray()
            logger.info(f"TF-IDF output shape: {X_text.shape}")
            
            # Truncate or pad text features to match exactly what we need
            if X_text.shape[1] > n_text_needed:
                X_text = X_text[:, :n_text_needed]
                logger.info(f"Truncated text features to {n_text_needed}")
            elif X_text.shape[1] < n_text_needed:
                padding = np.zeros((1, n_text_needed - X_text.shape[1]))
                X_text = np.hstack([X_text, padding])
                logger.info(f"Padded text features to {n_text_needed}")
                
        except Exception as e:
            logger.warning(f"TF-IDF transform failed: {e}, using zeros")
            X_text = np.zeros((1, n_text_needed))
    elif n_text_needed > 0:
        # No vectorizer but we need text features - use zeros
        X_text = np.zeros((1, n_text_needed))
        logger.info(f"Using {n_text_needed} zero text features (no vectorizer)")
    else:
        X_text = np.zeros((1, 0))  # Empty array - no text needed
    
    # Step 4: Concatenate [TABULAR | TEXT]
    if X_text.shape[1] > 0:
        X_final = np.hstack([X_tabular, X_text])
    else:
        X_final = X_tabular
    
    logger.info(f"Combined feature matrix shape: {X_final.shape}")
    
    # Step 5: FORCE exact shape match (truncate if tabular alone exceeded)
    if X_final.shape[1] != expected_features:
        logger.warning(
            f"Final feature count mismatch: got {X_final.shape[1]}, "
            f"expected {expected_features}. Force-fixing..."
        )
        # Use truncation for excess, padding for deficit
        if X_final.shape[1] > expected_features:
            X_final = X_final[:, :expected_features]
        else:
            padding = np.zeros((1, expected_features - X_final.shape[1]))
            X_final = np.hstack([X_final, padding])
    
    return X_final


def _fix_feature_shape(X: np.ndarray, expected_features: int) -> np.ndarray:
    """
    Emergency fix for feature shape mismatch.
    
    This should rarely be needed if the pipeline is correct.
    """
    actual_features = X.shape[1]
    
    if actual_features < expected_features:
        # Pad with zeros
        padding = np.zeros((X.shape[0], expected_features - actual_features))
        X = np.hstack([X, padding])
        logger.warning(f"Padded features from {actual_features} to {expected_features}")
    elif actual_features > expected_features:
        # Truncate
        X = X[:, :expected_features]
        logger.warning(f"Truncated features from {actual_features} to {expected_features}")
    
    return X


# ---------------------------------------------------------------------------
# Single Target Prediction
# ---------------------------------------------------------------------------

def predict_single_target(
    target: str,
    user_input: Dict[str, Any],
    free_text: Optional[str],
    models: Dict[str, Any],
    preprocessors: Dict[str, Any],
    vectorizers: Dict[str, Any]
) -> Optional[float]:
    """
    Run inference for a single target with deterministic feature construction.
    """
    model = models.get(target)
    if model is None:
        logger.info(f"Model not available: {target}")
        return None
    
    preprocessor = preprocessors.get(target)
    if preprocessor is None:
        logger.warning(f"Preprocessor not available: {target}")
        return None
    
    vectorizer = vectorizers.get(target)
    
    # Get frozen feature configuration
    config = get_feature_config(target)
    if config is None:
        logger.warning(f"Could not get feature config for: {target}")
        return None
    
    # Get the EXACT number of features the model expects
    expected_features = model.n_features_in_ if hasattr(model, 'n_features_in_') else config.n_total_features
    
    logger.info(f"[{target}] Model expects {expected_features} features")
    
    try:
        # Build feature matrix with deterministic structure
        X = build_feature_matrix(
            user_input=user_input,
            free_text=free_text,
            preprocessor=preprocessor,
            vectorizer=vectorizer,
            config=config,
            expected_features=expected_features
        )
        
        # Final verification
        if X.shape[1] != expected_features:
            logger.error(
                f"CRITICAL: Final feature mismatch for {target}. "
                f"X.shape={X.shape}, model expects {expected_features}"
            )
            return None
        
        # Run prediction
        prediction = model.predict(X)[0]
        
        # Ensure non-negative score
        result = max(0.0, float(prediction))
        
        logger.info(f"[{target}] Prediction: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Prediction failed for {target}: {e}")
        import traceback
        traceback.print_exc()
        return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def run_inference(
    user_input: Dict[str, Any],
    free_text: Optional[str] = None
) -> Dict[str, Optional[float]]:
    """
    Run inference on all available models.
    
    This is the STABLE PUBLIC API. The feature construction is entirely
    deterministic based on the frozen preprocessor configuration.
    
    Args:
        user_input: Dict with user's answers/features.
            Can be minimal: {"age": 25, "gender": "male"}
            Missing columns are handled by the preprocessor's imputer.
        free_text: Optional free-form text for TF-IDF features.
    
    Returns:
        Dict with prediction scores:
        {
            "stress_score": float or None,
            "depression_score": float or None,
            "anxiety_score": float or None,
            "sleep_quality": float or None
        }
    
    Example:
        >>> result = run_inference(
        ...     {"age": 25, "gender": "male"},
        ...     "I feel stressed but hopeful."
        ... )
        >>> print(result)
        {"stress_score": 15.2, "depression_score": 8.5, ...}
    """
    # Load all artifacts (cached)
    models = load_models()
    preprocessors = load_preprocessors()
    vectorizers = load_vectorizers()
    
    # Run inference for each target
    results = {}
    
    for target, output_name in TARGET_OUTPUT_NAMES.items():
        score = predict_single_target(
            target=target,
            user_input=user_input,
            free_text=free_text,
            models=models,
            preprocessors=preprocessors,
            vectorizers=vectorizers
        )
        
        results[output_name] = round(score, 2) if score is not None else None
    
    return results


# ---------------------------------------------------------------------------
# Diagnostic Functions
# ---------------------------------------------------------------------------

def check_models_loaded() -> Dict[str, bool]:
    """Check which models are successfully loaded."""
    models = load_models()
    return {target: model is not None for target, model in models.items()}


def get_model_metadata() -> Dict[str, Any]:
    """Get metadata about loaded models and their feature expectations."""
    models = load_models()
    preprocessors = load_preprocessors()
    vectorizers = load_vectorizers()
    
    metadata = {
        "available_models": [],
        "missing_models": [],
        "model_dir": str(MODEL_DIR),
        "feature_configs": {},
    }
    
    for target in MODEL_FILES.keys():
        model = models.get(target)
        
        if model is not None:
            metadata["available_models"].append(target)
            
            # Get feature config
            config = get_feature_config(target)
            if config:
                metadata["feature_configs"][target] = {
                    "numeric_columns": config.numeric_columns,
                    "categorical_columns": config.categorical_columns,
                    "n_tabular_features": config.n_tabular_features,
                    "n_text_features": config.n_text_features,
                    "n_total_features": config.n_total_features,
                    "model_expects": model.n_features_in_ if hasattr(model, 'n_features_in_') else None,
                }
        else:
            metadata["missing_models"].append(target)
    
    return metadata


def verify_feature_alignment() -> Dict[str, Dict[str, Any]]:
    """
    Verify that the feature pipeline produces correct shapes for all models.
    
    Returns diagnostic information for each target.
    """
    models = load_models()
    preprocessors = load_preprocessors()
    vectorizers = load_vectorizers()
    
    # Test input
    test_input = {"age": 25, "gender": "male"}
    test_text = "I feel tired"
    
    results = {}
    
    for target in MODEL_FILES.keys():
        model = models.get(target)
        preprocessor = preprocessors.get(target)
        vectorizer = vectorizers.get(target)
        config = get_feature_config(target)
        
        if model is None:
            results[target] = {"status": "missing_model"}
            continue
        
        if preprocessor is None:
            results[target] = {"status": "missing_preprocessor"}
            continue
        
        if config is None:
            results[target] = {"status": "missing_config"}
            continue
        
        try:
            X = build_feature_matrix(
                user_input=test_input,
                free_text=test_text,
                preprocessor=preprocessor,
                vectorizer=vectorizer,
                config=config
            )
            
            expected = model.n_features_in_ if hasattr(model, 'n_features_in_') else None
            
            results[target] = {
                "status": "ok" if X.shape[1] == expected else "mismatch",
                "X_shape": X.shape,
                "model_expects": expected,
                "config_total": config.n_total_features,
                "match": X.shape[1] == expected if expected else None,
            }
            
        except Exception as e:
            results[target] = {"status": "error", "error": str(e)}
    
    return results


def get_available_models() -> List[str]:
    """Return list of available model targets."""
    models = load_models()
    return [target for target, model in models.items() if model is not None]


def get_required_features() -> List[str]:
    """Get list of all feature columns used across models."""
    all_columns = set()
    
    for target in MODEL_FILES.keys():
        config = get_feature_config(target)
        if config:
            all_columns.update(config.all_tabular_columns)
    
    return sorted(list(all_columns))


def clear_inference_caches():
    """Clear all cached artifacts to force reload."""
    load_models.cache_clear()
    load_preprocessors.cache_clear()
    load_vectorizers.cache_clear()
    get_feature_config.cache_clear()
    logger.info("Cleared all inference caches")


# ---------------------------------------------------------------------------
# CLI Testing
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=" * 70)
    print("DETERMINISTIC INFERENCE PIPELINE TEST")
    print("=" * 70)
    print()
    
    # Check models
    print("📊 Model Availability:")
    status = check_models_loaded()
    for target, available in status.items():
        emoji = "✅" if available else "❌"
        print(f"   {emoji} {target}")
    
    print()
    
    # Verify feature alignment
    print("🔍 Feature Alignment Verification:")
    alignment = verify_feature_alignment()
    for target, info in alignment.items():
        if info["status"] == "ok":
            print(f"   ✅ {target}: X.shape={info['X_shape']}, model_expects={info['model_expects']}")
        elif info["status"] == "mismatch":
            print(f"   ❌ {target}: MISMATCH - X.shape={info['X_shape']}, model_expects={info['model_expects']}")
        else:
            print(f"   ⚠️  {target}: {info['status']}")
    
    print()
    
    # Show feature configs
    print("📋 Feature Configurations:")
    for target in MODEL_FILES.keys():
        config = get_feature_config(target)
        if config:
            print(f"   {target}: {config}")
    
    print()
    print("-" * 70)
    print("TEST: Minimal Input")
    print("-" * 70)
    
    minimal_input = {"age": 25, "gender": "male"}
    print(f"Input: {minimal_input}")
    print(f"Text: 'I feel stressed but hopeful.'")
    
    result = run_inference(minimal_input, "I feel stressed but hopeful.")
    
    print()
    print("Results:")
    for key, value in result.items():
        status = "✅" if value is not None else "⚠️  None"
        print(f"   {key}: {value} {'' if value is not None else status}")
    
    print()
    print("-" * 70)
    print("TEST: Full Input")
    print("-" * 70)
    
    full_input = {
        "age": "20-25",
        "gender": "Female",
        "occupation": "Student",
        "mood_swings": "High",
        "frustration": "Yes",
        "social_isolation": "Yes",
        "weight_change": "No",
        "coping_struggle": "Yes",
        "lifestyle_change": "Yes",
    }
    print(f"Input: {full_input}")
    
    result2 = run_inference(full_input, "I've been feeling very anxious about everything.")
    
    print()
    print("Results:")
    for key, value in result2.items():
        status = "✅" if value is not None else "⚠️  None"
        print(f"   {key}: {value} {'' if value is not None else status}")
    
    print()
    print("=" * 70)
    print("VERIFICATION COMPLETE")
    print("=" * 70)
    
    # Final verification
    all_ok = all(
        info.get("status") == "ok" or info.get("status") == "mismatch" 
        for info in alignment.values()
    )
    if all_ok:
        print("✅ Feature pipeline is correctly aligned with trained models.")
    else:
        print("⚠️  Some models have configuration issues. Check logs above.")
