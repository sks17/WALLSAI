"""
KERNEL Text Encoder Module

Replaces TF-IDF with modern NLP techniques:
1. Sentence Transformers for semantic embeddings
2. VADER for sentiment analysis
3. Keyword extraction for interpretability

FIXES:
- All outputs are JSON-safe Python primitives
- Embeddings are np.float64 arrays
- Deterministic, fixed-size vectors

Usage:
    from src.kernel.text_encoder import TextEncoder
    
    encoder = TextEncoder()
    features = encoder.encode("I've been feeling really anxious lately")
"""
from __future__ import annotations

import logging
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import numpy as np

# Ensure project root is in path for standalone execution
ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

logger = logging.getLogger("walls.kernel.text_encoder")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Fixed embedding dimension for consistency
EMBEDDING_DIM = 64  # Reduced from 384 to fit model input
SENTIMENT_DIM = 4   # positive, negative, neutral, compound
KEYWORD_DIM = 5     # depression, anxiety, stress, sleep, crisis
FLAG_DIM = 7        # binary flags

# Total text vector dimension
TEXT_VECTOR_DIM = EMBEDDING_DIM + SENTIMENT_DIM + KEYWORD_DIM + FLAG_DIM  # 80

# ---------------------------------------------------------------------------
# Clinical Keywords for Mental Health Detection
# ---------------------------------------------------------------------------

CLINICAL_KEYWORDS = {
    "depression": [
        "depressed", "hopeless", "worthless", "empty", "numb", "sad",
        "crying", "tears", "death", "die", "suicide", "self-harm",
        "give up", "no point", "burden", "failure", "hate myself"
    ],
    "anxiety": [
        "anxious", "worried", "panic", "fear", "scared", "nervous",
        "racing heart", "can't breathe", "dread", "overwhelmed",
        "on edge", "tense", "restless", "apprehensive"
    ],
    "stress": [
        "stressed", "pressure", "deadline", "overworked", "exhausted",
        "burned out", "burnout", "too much", "can't cope", "breaking point",
        "overwhelmed", "frantic", "hectic"
    ],
    "sleep": [
        "insomnia", "can't sleep", "nightmares", "tired", "exhausted",
        "fatigue", "no energy", "oversleeping", "restless nights"
    ],
    "crisis": [
        "suicide", "kill myself", "end it", "don't want to live",
        "better off dead", "self-harm", "hurt myself", "cutting"
    ]
}


# ---------------------------------------------------------------------------
# Safe Type Conversion Helpers
# ---------------------------------------------------------------------------

def safe_float(x: Any) -> float:
    """Convert any numeric type to a Python float."""
    if x is None:
        return 0.0
    try:
        # Handle PyTorch tensors
        if hasattr(x, 'item'):
            return float(x.item())
        # Handle numpy types
        if hasattr(x, 'dtype'):
            return float(x)
        return float(x)
    except (TypeError, ValueError):
        return 0.0


def safe_numpy(x: Any) -> np.ndarray:
    """
    Recursively convert tensors/arrays to numpy float64.
    
    Handles:
    - PyTorch tensors
    - Numpy arrays of any dtype
    - Lists/tuples
    - Scalars
    """
    # PyTorch tensor
    if hasattr(x, 'detach') and hasattr(x, 'cpu'):
        x = x.detach().cpu().numpy()
    
    # Convert to numpy if not already
    if not isinstance(x, np.ndarray):
        x = np.array(x)
    
    # Ensure float64 for JSON compatibility
    return x.astype(np.float64)


def safe_dict(d: Dict[str, Any]) -> Dict[str, float]:
    """Convert all values in a dict to Python floats."""
    return {k: safe_float(v) for k, v in d.items()}


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------

@dataclass
class TextFeatures:
    """Container for extracted text features."""
    embedding: np.ndarray  # EMBEDDING_DIM-dim semantic embedding
    sentiment: Dict[str, float]  # pos, neg, neu, compound
    keywords: Dict[str, float]  # category -> score
    clinical_flags: List[str]  # detected risk indicators
    text_length: int
    word_count: int
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON-safe dictionary."""
        return {
            "embedding_shape": list(self.embedding.shape),
            "sentiment": safe_dict(self.sentiment),
            "keywords": safe_dict(self.keywords),
            "clinical_flags": list(self.clinical_flags),
            "text_length": int(self.text_length),
            "word_count": int(self.word_count)
        }


# ---------------------------------------------------------------------------
# Text Encoder Class
# ---------------------------------------------------------------------------

class TextEncoder:
    """
    Modern text encoder using sentence transformers and sentiment analysis.
    
    Falls back gracefully if dependencies are not installed.
    All outputs are guaranteed to be JSON-safe.
    """
    
    def __init__(self):
        """Initialize the encoder."""
        self.embedding_dim = EMBEDDING_DIM
        
        # Try to load sentence transformer
        self._sentence_model = None
        self._load_sentence_transformer()
        
        # Try to load VADER sentiment
        self._vader = None
        self._load_vader()
        
        logger.info(f"TextEncoder initialized: embedding={self._sentence_model is not None}, sentiment={self._vader is not None}")
    
    def _load_sentence_transformer(self):
        """Load sentence transformer model if available."""
        try:
            from sentence_transformers import SentenceTransformer
            self._sentence_model = SentenceTransformer("all-MiniLM-L6-v2")
            logger.info("Loaded sentence transformer: all-MiniLM-L6-v2")
        except ImportError:
            logger.warning("sentence-transformers not installed, using fallback embeddings")
        except Exception as e:
            logger.warning(f"Failed to load sentence transformer: {e}")
    
    def _load_vader(self):
        """Load VADER sentiment analyzer if available."""
        try:
            from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
            self._vader = SentimentIntensityAnalyzer()
            logger.info("Loaded VADER sentiment analyzer")
        except ImportError:
            logger.warning("vaderSentiment not installed, using fallback sentiment")
        except Exception as e:
            logger.warning(f"Failed to load VADER: {e}")
    
    def encode(self, text: str) -> TextFeatures:
        """
        Encode text into features.
        
        Args:
            text: Input text string
            
        Returns:
            TextFeatures with embedding, sentiment, keywords, flags
        """
        if not text or not text.strip():
            return self._empty_features()
        
        text = text.strip()
        
        # Get embedding (always returns np.float64 array)
        embedding = self._get_embedding(text)
        
        # Get sentiment (always returns Python floats)
        sentiment = self._get_sentiment(text)
        
        # Extract keywords (always returns Python floats)
        keywords = self._extract_keywords(text)
        
        # Detect clinical flags
        clinical_flags = self._detect_clinical_flags(text)
        
        # Text stats
        word_count = len(text.split())
        
        return TextFeatures(
            embedding=embedding,
            sentiment=sentiment,
            keywords=keywords,
            clinical_flags=clinical_flags,
            text_length=len(text),
            word_count=word_count
        )
    
    def _empty_features(self) -> TextFeatures:
        """Return empty features for missing text."""
        return TextFeatures(
            embedding=np.zeros(self.embedding_dim, dtype=np.float64),
            sentiment={"positive": 0.0, "negative": 0.0, "neutral": 1.0, "compound": 0.0},
            keywords={},
            clinical_flags=[],
            text_length=0,
            word_count=0
        )
    
    def _get_embedding(self, text: str) -> np.ndarray:
        """
        Get semantic embedding for text.
        
        Always returns np.float64 array of shape (EMBEDDING_DIM,).
        """
        raw_embedding = None
        
        if self._sentence_model is not None:
            try:
                # Get raw embedding from transformer
                raw = self._sentence_model.encode(text, convert_to_numpy=True)
                raw_embedding = safe_numpy(raw)
            except Exception as e:
                logger.warning(f"Embedding failed: {e}, using fallback")
        
        if raw_embedding is None:
            # Fallback: simple hash-based embedding
            raw_embedding = self._fallback_embedding(text)
        
        # Reduce to fixed dimension via mean pooling if needed
        if len(raw_embedding) > self.embedding_dim:
            # Reshape and take mean of chunks
            chunk_size = len(raw_embedding) // self.embedding_dim
            reduced = np.zeros(self.embedding_dim, dtype=np.float64)
            for i in range(self.embedding_dim):
                start = i * chunk_size
                end = start + chunk_size
                reduced[i] = np.mean(raw_embedding[start:end])
            return reduced
        elif len(raw_embedding) < self.embedding_dim:
            # Pad with zeros
            padded = np.zeros(self.embedding_dim, dtype=np.float64)
            padded[:len(raw_embedding)] = raw_embedding
            return padded
        else:
            return raw_embedding.astype(np.float64)
    
    def _fallback_embedding(self, text: str) -> np.ndarray:
        """
        Create a simple fallback embedding when transformers aren't available.
        
        Uses a deterministic approach based on word hashing.
        """
        words = text.lower().split()
        embedding = np.zeros(self.embedding_dim, dtype=np.float64)
        
        for i, word in enumerate(words):
            # Hash word to get index
            word_hash = hash(word) % self.embedding_dim
            # Add to embedding with position decay
            weight = 1.0 / (1 + i * 0.1)
            embedding[word_hash] += weight
        
        # Normalize
        norm = np.linalg.norm(embedding)
        if norm > 0:
            embedding /= norm
        
        return embedding
    
    def _get_sentiment(self, text: str) -> Dict[str, float]:
        """
        Get sentiment scores for text.
        
        Always returns dict with Python float values.
        """
        if self._vader is not None:
            try:
                scores = self._vader.polarity_scores(text)
                return {
                    "positive": safe_float(scores["pos"]),
                    "negative": safe_float(scores["neg"]),
                    "neutral": safe_float(scores["neu"]),
                    "compound": safe_float(scores["compound"])
                }
            except Exception as e:
                logger.warning(f"Sentiment analysis failed: {e}")
        
        # Fallback: keyword-based sentiment
        return self._fallback_sentiment(text)
    
    def _fallback_sentiment(self, text: str) -> Dict[str, float]:
        """Simple keyword-based sentiment fallback."""
        text_lower = text.lower()
        
        positive_words = ["happy", "good", "great", "love", "joy", "hope", "better", "improve"]
        negative_words = ["sad", "bad", "hate", "fear", "worry", "stress", "anxious", "depressed"]
        
        pos_count = sum(1 for w in positive_words if w in text_lower)
        neg_count = sum(1 for w in negative_words if w in text_lower)
        total = pos_count + neg_count
        
        if total == 0:
            return {"positive": 0.0, "negative": 0.0, "neutral": 1.0, "compound": 0.0}
        
        pos_score = float(pos_count) / float(total)
        neg_score = float(neg_count) / float(total)
        compound = pos_score - neg_score
        
        return {
            "positive": pos_score,
            "negative": neg_score,
            "neutral": max(0.0, 1.0 - pos_score - neg_score),
            "compound": compound
        }
    
    def _extract_keywords(self, text: str) -> Dict[str, float]:
        """Extract clinical keyword categories from text."""
        text_lower = text.lower()
        keywords = {}
        
        for category, terms in CLINICAL_KEYWORDS.items():
            matches = sum(1 for term in terms if term in text_lower)
            if matches > 0:
                # Normalize by number of terms
                score = min(1.0, float(matches) / float(len(terms)) * 5.0)
                keywords[category] = round(score, 3)
        
        return keywords
    
    def _detect_clinical_flags(self, text: str) -> List[str]:
        """Detect clinical risk flags in text."""
        text_lower = text.lower()
        flags = []
        
        # Crisis detection (highest priority)
        for term in CLINICAL_KEYWORDS["crisis"]:
            if term in text_lower:
                flags.append("CRISIS_RISK")
                break
        
        # Category mentions
        for category in ["depression", "anxiety", "stress", "sleep"]:
            for term in CLINICAL_KEYWORDS[category][:5]:
                if term in text_lower:
                    flags.append(f"{category}_mentioned")
                    break
        
        # Intensity indicators
        intensity_words = ["very", "extremely", "severely", "constantly", "always"]
        if any(word in text_lower for word in intensity_words):
            flags.append("high_intensity")
        
        # Duration indicators
        duration_words = ["weeks", "months", "years", "long time", "forever"]
        if any(word in text_lower for word in duration_words):
            flags.append("prolonged_duration")
        
        return list(set(flags))
    
    def to_vector(self, features: TextFeatures) -> np.ndarray:
        """
        Convert TextFeatures to a flat vector for model input.
        
        Returns:
            np.float64 array of shape (TEXT_VECTOR_DIM,)
        """
        parts = []
        
        # Embedding (EMBEDDING_DIM dims)
        parts.append(safe_numpy(features.embedding))
        
        # Sentiment scores (SENTIMENT_DIM dims)
        sentiment_vec = np.array([
            safe_float(features.sentiment.get("positive", 0)),
            safe_float(features.sentiment.get("negative", 0)),
            safe_float(features.sentiment.get("neutral", 0)),
            safe_float(features.sentiment.get("compound", 0))
        ], dtype=np.float64)
        parts.append(sentiment_vec)
        
        # Keyword scores (KEYWORD_DIM dims)
        keyword_order = ["depression", "anxiety", "stress", "sleep", "crisis"]
        keyword_vec = np.array([
            safe_float(features.keywords.get(k, 0)) for k in keyword_order
        ], dtype=np.float64)
        parts.append(keyword_vec)
        
        # Binary flags (FLAG_DIM dims)
        flag_order = ["CRISIS_RISK", "depression_mentioned", "anxiety_mentioned", 
                      "stress_mentioned", "sleep_mentioned", "high_intensity", "prolonged_duration"]
        flag_vec = np.array([
            1.0 if f in features.clinical_flags else 0.0 for f in flag_order
        ], dtype=np.float64)
        parts.append(flag_vec)
        
        result = np.concatenate(parts)
        assert result.shape == (TEXT_VECTOR_DIM,), f"Expected {TEXT_VECTOR_DIM}, got {result.shape}"
        return result
    
    @property
    def vector_dim(self) -> int:
        """Total dimension of the feature vector."""
        return TEXT_VECTOR_DIM


# ---------------------------------------------------------------------------
# Module-level convenience functions
# ---------------------------------------------------------------------------

_encoder: Optional[TextEncoder] = None


def get_encoder() -> TextEncoder:
    """Get or create the singleton encoder."""
    global _encoder
    if _encoder is None:
        _encoder = TextEncoder()
    return _encoder


def encode_text(text: str) -> TextFeatures:
    """Encode text using the singleton encoder."""
    return get_encoder().encode(text)


def text_to_vector(text: str) -> np.ndarray:
    """Get the vector representation of text."""
    features = encode_text(text)
    return get_encoder().to_vector(features)


# ---------------------------------------------------------------------------
# Self-Test
# ---------------------------------------------------------------------------

def selftest():
    """Run self-test to verify module works correctly."""
    import json
    
    print("=" * 60)
    print("KERNEL Text Encoder Self-Test")
    print("=" * 60)
    
    encoder = TextEncoder()
    
    test_texts = [
        "I've been feeling really anxious and stressed about work lately.",
        "I'm doing great! Life is wonderful and I feel happy.",
        "I can't sleep at night. I keep having nightmares.",
        "I don't want to live anymore. Everything feels hopeless.",
        "",
    ]
    
    all_passed = True
    
    for i, text in enumerate(test_texts):
        print(f"\nTest {i+1}: '{text[:50]}{'...' if len(text) > 50 else ''}'")
        
        try:
            features = encoder.encode(text)
            
            # Verify embedding
            assert features.embedding.dtype == np.float64, "Embedding must be float64"
            assert features.embedding.shape == (EMBEDDING_DIM,), f"Embedding shape mismatch: {features.embedding.shape}"
            
            # Verify sentiment is JSON-safe
            json_str = json.dumps(features.sentiment)
            assert json_str, "Sentiment must be JSON-serializable"
            
            # Verify vector
            vec = encoder.to_vector(features)
            assert vec.dtype == np.float64, "Vector must be float64"
            assert vec.shape == (TEXT_VECTOR_DIM,), f"Vector shape mismatch: {vec.shape}"
            
            # Verify JSON-safe
            vec_list = vec.tolist()
            json_str = json.dumps(vec_list)
            assert json_str, "Vector must be JSON-serializable"
            
            print(f"  ✓ Embedding shape: {features.embedding.shape}")
            print(f"  ✓ Sentiment: {features.sentiment}")
            print(f"  ✓ Keywords: {features.keywords}")
            print(f"  ✓ Flags: {features.clinical_flags}")
            print(f"  ✓ Vector dim: {vec.shape[0]}")
            print(f"  ✓ JSON-safe: YES")
            
        except Exception as e:
            print(f"  ✗ FAILED: {e}")
            all_passed = False
    
    print("\n" + "=" * 60)
    if all_passed:
        print("All tests PASSED!")
    else:
        print("Some tests FAILED!")
    print(f"Text vector dimension: {TEXT_VECTOR_DIM}")
    print("=" * 60)
    
    return all_passed


if __name__ == "__main__":
    selftest()
