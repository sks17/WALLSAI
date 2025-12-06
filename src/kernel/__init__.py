"""
KERNEL - Knowledge-Enhanced Robust Neural Evaluation Layer

This module provides the core components for the WALLS mental health
assessment system, including:

- Multi-modal input preprocessing (Likert, sliders, text)
- Sentence transformer text embeddings (fallback: hash-based)
- VADER sentiment analysis (fallback: keyword-based)
- Multi-task neural network with uncertainty
- Distributional outputs with confidence intervals

DIMENSIONS:
- Text vector: 80 dimensions (64 embedding + 4 sentiment + 5 keywords + 7 flags)
- Tabular vector: 20 dimensions (PHQ-9 + GAD-7 + stress sliders)
- Total input: 100 dimensions (FIXED)

Usage:
    from src.kernel import KernelPreprocessor, KernelModel
    
    # Preprocess inputs
    preprocessor = KernelPreprocessor()
    processed = preprocessor.preprocess(responses, free_text)
    
    # Run inference
    model = KernelModel()  # Or load from file
    result = model.predict(processed.full_vector)
"""
import sys
from pathlib import Path

# Ensure project root is in path for imports
ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Import components
from src.kernel.text_encoder import (
    TextEncoder, 
    encode_text, 
    text_to_vector,
    TEXT_VECTOR_DIM,
    EMBEDDING_DIM
)
from src.kernel.preprocessor import (
    KernelPreprocessor, 
    preprocess_input,
    TARGET_INPUT_DIM,
    TABULAR_DIM
)
from src.kernel.model import (
    KernelModel, 
    PredictionResult,
    EXPECTED_INPUT_DIM
)

__all__ = [
    # Text processing
    "TextEncoder",
    "encode_text", 
    "text_to_vector",
    "TEXT_VECTOR_DIM",
    "EMBEDDING_DIM",
    
    # Preprocessing
    "KernelPreprocessor",
    "preprocess_input",
    "TARGET_INPUT_DIM",
    "TABULAR_DIM",
    
    # Model
    "KernelModel",
    "PredictionResult",
    "EXPECTED_INPUT_DIM",
]

# Verify dimension consistency at import time
assert TARGET_INPUT_DIM == EXPECTED_INPUT_DIM, \
    f"Dimension mismatch: preprocessor={TARGET_INPUT_DIM}, model={EXPECTED_INPUT_DIM}"

