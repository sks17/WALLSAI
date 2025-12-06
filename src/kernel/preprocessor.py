"""
KERNEL Preprocessor Module

Handles preprocessing of multi-modal inputs:
- Likert scale responses (PHQ-9, GAD-7 style)
- Continuous sliders (0-100)
- Categorical variables
- Free-text features

Output is a unified feature vector of EXACTLY 100 dimensions
for the KERNEL neural network.

FIXES:
- Absolute imports for standalone execution
- Fixed 100-dimensional output
- Verification step ensures dimension match
"""
from __future__ import annotations

import json
import logging
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np

# ---------------------------------------------------------------------------
# Path Setup for Standalone Execution
# ---------------------------------------------------------------------------

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Absolute imports
from src.kernel.text_encoder import (
    TextEncoder, TextFeatures, TEXT_VECTOR_DIM,
    safe_float, safe_numpy
)

logger = logging.getLogger("walls.kernel.preprocessor")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Target input dimension for KERNEL model
# This MUST match model.EXPECTED_INPUT_DIM
TARGET_INPUT_DIM = 100

# Tabular features dimension = TARGET_INPUT_DIM - TEXT_VECTOR_DIM
TABULAR_DIM = TARGET_INPUT_DIM - TEXT_VECTOR_DIM  # 100 - 80 = 20

# Define exactly which features we extract (20 total)
TABULAR_FEATURES = [
    # PHQ-9 items (9 features)
    "phq9_1", "phq9_2", "phq9_3", "phq9_4", "phq9_5",
    "phq9_6", "phq9_7", "phq9_8", "phq9_9",
    # GAD-7 items (7 features)
    "gad7_1", "gad7_2", "gad7_3", "gad7_4",
    "gad7_5", "gad7_6", "gad7_7",
    # Stress sliders (4 features) - normalized to [0,1]
    "stress_work", "stress_relationships", "stress_financial", "stress_health",
]

assert len(TABULAR_FEATURES) == TABULAR_DIM, f"Expected {TABULAR_DIM} features, got {len(TABULAR_FEATURES)}"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------

@dataclass
class ProcessedInput:
    """Container for processed input features."""
    
    # Tabular features (normalized to [0,1])
    tabular_vector: np.ndarray  # shape: (TABULAR_DIM,)
    
    # Text features
    text_vector: np.ndarray  # shape: (TEXT_VECTOR_DIM,)
    text_features: Optional[TextFeatures]
    
    # Raw instrument scores (for clinical display)
    instrument_scores: Dict[str, float]
    
    # Metadata
    feature_names: List[str]
    missing_features: List[str]
    
    @property
    def full_vector(self) -> np.ndarray:
        """
        Concatenate all features into a single vector.
        
        Returns:
            np.float64 array of shape (TARGET_INPUT_DIM,)
        """
        result = np.concatenate([self.tabular_vector, self.text_vector])
        assert result.shape == (TARGET_INPUT_DIM,), \
            f"Expected shape ({TARGET_INPUT_DIM},), got {result.shape}"
        return result.astype(np.float64)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "tabular_vector": self.tabular_vector.tolist(),
            "text_vector": self.text_vector.tolist(),
            "instrument_scores": {k: safe_float(v) for k, v in self.instrument_scores.items()},
            "feature_names": list(self.feature_names),
            "missing_features": list(self.missing_features),
            "total_dim": int(TARGET_INPUT_DIM)
        }


# ---------------------------------------------------------------------------
# Preprocessor Class
# ---------------------------------------------------------------------------

class KernelPreprocessor:
    """
    Preprocessor for KERNEL multi-modal inputs.
    
    Handles:
    - Likert scales: Normalize to [0, 1]
    - Sliders: Normalize to [0, 1]
    - Text: Sentence embedding + sentiment
    - Missing values: Default to 0.5 (neutral)
    
    Output is ALWAYS exactly TARGET_INPUT_DIM dimensions.
    """
    
    def __init__(self, schema_path: Optional[Path] = None):
        """
        Initialize preprocessor.
        
        Args:
            schema_path: Path to kernel_schema.json (optional)
        """
        self.schema = self._load_schema(schema_path)
        self.text_encoder = TextEncoder()
        
        # Feature configuration
        self.feature_names = TABULAR_FEATURES.copy()
        self.tabular_dim = TABULAR_DIM
        
        # Normalization ranges for each feature
        self.normalization_params = self._build_normalization_params()
        
        logger.info(f"KernelPreprocessor initialized: tabular_dim={self.tabular_dim}, text_dim={self.text_encoder.vector_dim}")
    
    def _load_schema(self, path: Optional[Path]) -> Dict[str, Any]:
        """Load the assessment schema."""
        if path is None:
            path = ROOT / "data" / "kernel_schema.json"
        
        if not path.exists():
            logger.warning(f"Schema not found at {path}, using defaults")
            return {"sections": [], "instruments": {}}
        
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load schema: {e}")
            return {"sections": [], "instruments": {}}
    
    def _build_normalization_params(self) -> Dict[str, tuple]:
        """Build normalization parameters for each feature."""
        params = {}
        
        for name in self.feature_names:
            if name.startswith("phq9_"):
                # PHQ-9: 0-3 Likert scale
                params[name] = (0, 3)
            elif name.startswith("gad7_"):
                # GAD-7: 0-3 Likert scale
                params[name] = (0, 3)
            elif name.startswith("stress_"):
                # Stress sliders: 0-100
                params[name] = (0, 100)
            else:
                # Default: assume 0-1
                params[name] = (0, 1)
        
        return params
    
    def preprocess(
        self,
        responses: Dict[str, Any],
        free_text: str = ""
    ) -> ProcessedInput:
        """
        Preprocess raw responses into model-ready features.
        
        Args:
            responses: Dict mapping question IDs to values
            free_text: Optional free-text input
            
        Returns:
            ProcessedInput with exactly TARGET_INPUT_DIM dimensions
        """
        # Initialize tabular vector
        tabular_vector = np.zeros(self.tabular_dim, dtype=np.float64)
        missing_features = []
        
        # Process each tabular feature
        for idx, name in enumerate(self.feature_names):
            if name in responses:
                value = responses[name]
                min_val, max_val = self.normalization_params[name]
                
                # Normalize to [0, 1]
                if max_val > min_val:
                    normalized = (safe_float(value) - min_val) / (max_val - min_val)
                else:
                    normalized = 0.5
                
                tabular_vector[idx] = np.clip(normalized, 0.0, 1.0)
            else:
                # Missing value - use 0.5 (neutral/middle)
                tabular_vector[idx] = 0.5
                missing_features.append(name)
        
        # Process text
        text_features = self.text_encoder.encode(free_text)
        text_vector = self.text_encoder.to_vector(text_features)
        
        # Verify dimensions
        assert tabular_vector.shape == (self.tabular_dim,), \
            f"Tabular vector shape mismatch: {tabular_vector.shape}"
        assert text_vector.shape == (TEXT_VECTOR_DIM,), \
            f"Text vector shape mismatch: {text_vector.shape}"
        
        # Calculate instrument scores (for display)
        instrument_scores = self._calculate_instrument_scores(responses)
        
        result = ProcessedInput(
            tabular_vector=tabular_vector,
            text_vector=text_vector,
            text_features=text_features,
            instrument_scores=instrument_scores,
            feature_names=self.feature_names.copy(),
            missing_features=missing_features
        )
        
        # Final verification
        full_vec = result.full_vector
        assert full_vec.shape == (TARGET_INPUT_DIM,), \
            f"Full vector shape mismatch: {full_vec.shape}, expected ({TARGET_INPUT_DIM},)"
        
        return result
    
    def _calculate_instrument_scores(self, responses: Dict[str, Any]) -> Dict[str, float]:
        """
        Calculate validated instrument scores (PHQ-9, GAD-7, etc.).
        """
        scores = {}
        
        # PHQ-9 (sum of phq9_1 to phq9_9)
        phq9_items = [f"phq9_{i}" for i in range(1, 10)]
        phq9_values = [safe_float(responses.get(item, 0)) for item in phq9_items]
        phq9_provided = sum(1 for item in phq9_items if item in responses)
        
        if phq9_provided > 0:
            scores["phq9_total"] = sum(phq9_values)
            scores["phq9_average"] = scores["phq9_total"] / 9.0
            scores["phq9_items_provided"] = float(phq9_provided)
        
        # GAD-7 (sum of gad7_1 to gad7_7)
        gad7_items = [f"gad7_{i}" for i in range(1, 8)]
        gad7_values = [safe_float(responses.get(item, 0)) for item in gad7_items]
        gad7_provided = sum(1 for item in gad7_items if item in responses)
        
        if gad7_provided > 0:
            scores["gad7_total"] = sum(gad7_values)
            scores["gad7_average"] = scores["gad7_total"] / 7.0
            scores["gad7_items_provided"] = float(gad7_provided)
        
        # Stress intensity (average of stress sliders)
        stress_items = ["stress_work", "stress_relationships", "stress_financial", "stress_health"]
        stress_values = [safe_float(responses.get(item)) for item in stress_items if item in responses]
        
        if stress_values:
            scores["stress_intensity"] = sum(stress_values) / len(stress_values)
        
        return scores
    
    @property
    def total_input_dim(self) -> int:
        """Total input dimension for the model."""
        return TARGET_INPUT_DIM


# ---------------------------------------------------------------------------
# Module-level convenience function
# ---------------------------------------------------------------------------

def preprocess_input(responses: Dict[str, Any], free_text: str = "") -> ProcessedInput:
    """
    Convenience function to preprocess inputs using default preprocessor.
    """
    preprocessor = KernelPreprocessor()
    return preprocessor.preprocess(responses, free_text)


# ---------------------------------------------------------------------------
# Self-Test
# ---------------------------------------------------------------------------

def selftest():
    """Run self-test to verify module works correctly."""
    import json
    
    print("=" * 60)
    print("KERNEL Preprocessor Self-Test")
    print("=" * 60)
    print(f"Target input dimension: {TARGET_INPUT_DIM}")
    print(f"Tabular dimension: {TABULAR_DIM}")
    print(f"Text dimension: {TEXT_VECTOR_DIM}")
    print()
    
    preprocessor = KernelPreprocessor()
    
    # Test responses (some complete, some missing)
    test_responses = {
        "phq9_1": 2,
        "phq9_2": 1,
        "phq9_3": 2,
        "phq9_4": 3,
        "phq9_5": 1,
        "phq9_6": 0,
        "phq9_7": 2,
        "phq9_8": 1,
        "phq9_9": 0,
        "gad7_1": 2,
        "gad7_2": 2,
        "gad7_3": 1,
        "gad7_4": 2,
        "gad7_5": 1,
        "gad7_6": 2,
        "gad7_7": 1,
        "stress_work": 75,
        "stress_relationships": 30,
        "stress_financial": 60,
        "stress_health": 40,
    }
    
    test_text = "I've been feeling really stressed about work and having trouble sleeping."
    
    print("Test 1: Full input with text")
    try:
        result = preprocessor.preprocess(test_responses, test_text)
        full_vec = result.full_vector
        
        print(f"  ✓ Tabular vector shape: {result.tabular_vector.shape}")
        print(f"  ✓ Text vector shape: {result.text_vector.shape}")
        print(f"  ✓ Full vector shape: {full_vec.shape}")
        print(f"  ✓ Full vector dtype: {full_vec.dtype}")
        
        # Verify JSON-safe
        json_str = json.dumps(result.to_dict())
        print(f"  ✓ JSON serializable: {len(json_str)} bytes")
        
        # Verify dimension
        assert full_vec.shape == (TARGET_INPUT_DIM,), f"Dimension mismatch!"
        print(f"  ✓ Dimension check: PASSED ({TARGET_INPUT_DIM})")
        
        print(f"\n  Instrument scores:")
        for key, value in result.instrument_scores.items():
            print(f"    {key}: {value:.2f}")
        
        print(f"\n  Missing features: {len(result.missing_features)}")
        
    except Exception as e:
        print(f"  ✗ FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print("\nTest 2: Empty input")
    try:
        result = preprocessor.preprocess({}, "")
        full_vec = result.full_vector
        
        assert full_vec.shape == (TARGET_INPUT_DIM,), f"Empty input dimension mismatch!"
        print(f"  ✓ Empty input shape: {full_vec.shape}")
        print(f"  ✓ Missing features: {len(result.missing_features)}")
        
    except Exception as e:
        print(f"  ✗ FAILED: {e}")
        return False
    
    print("\nTest 3: Partial input")
    try:
        partial_responses = {"phq9_1": 2, "phq9_2": 3, "stress_work": 80}
        result = preprocessor.preprocess(partial_responses, "Feeling okay")
        full_vec = result.full_vector
        
        assert full_vec.shape == (TARGET_INPUT_DIM,), f"Partial input dimension mismatch!"
        print(f"  ✓ Partial input shape: {full_vec.shape}")
        print(f"  ✓ Missing features: {len(result.missing_features)}")
        
    except Exception as e:
        print(f"  ✗ FAILED: {e}")
        return False
    
    print("\n" + "=" * 60)
    print("All tests PASSED!")
    print(f"Final vector dimension: {TARGET_INPUT_DIM}")
    print("=" * 60)
    
    return True


if __name__ == "__main__":
    selftest()
