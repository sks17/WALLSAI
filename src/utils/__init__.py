# src/utils package - Utility modules for data processing
"""
Utility modules:
- preprocess.py: Dataset-specific cleaning functions
- mapper.py: Column mapping and fuzzy matching
- ml.py: ML utilities (to be added)
"""
from .preprocess import (
    clean_abadi,
    clean_mmc2,
    clean_pone,
    clean_lifestyle,
    clean_dataset,
)

from .mapper import (
    CANONICAL_COLUMNS,
    detect_columns,
    map_demographics,
    map_lifestyle,
    map_phq9,
    map_gad7,
    map_stress,
    map_sleep,
    build_unified_dataframe,
    print_diagnostics,
)

from .ml import (
    MIN_TRAINING_ROWS,
    TrainingSummary,
    identify_column_types,
    build_preprocessor,
    build_tfidf_vectorizer,
    build_training_matrix,
    train_one_target,
    evaluate_model,
    save_model,
    load_model,
    save_all_artifacts,
    analyze_dataset_contributions,
    print_training_summary,
)

