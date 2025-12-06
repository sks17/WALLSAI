"""
KERNEL API Module

Flask API endpoints for the KERNEL mental health assessment system.

Endpoints:
- POST /api/kernel/predict - Run inference with uncertainty
- GET /api/kernel/schema - Get assessment schema
- GET /api/kernel/status - Check model status
- GET /api/kernel/thresholds - Get clinical thresholds
- GET /api/kernel/history - Get user history
- GET /api/kernel/debug - Debug last request
"""
from __future__ import annotations

import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from flask import Blueprint, jsonify, request

# Ensure project root is in path
ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Use absolute imports
from src.kernel.preprocessor import KernelPreprocessor, TARGET_INPUT_DIM
from src.kernel.model import KernelModel, PredictionResult, EXPECTED_INPUT_DIM

logger = logging.getLogger("walls.kernel.api")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

MODEL_PATH = ROOT / "models" / "kernel_model.pt"
SCHEMA_PATH = ROOT / "data" / "kernel_schema.json"
USER_DATA_DIR = ROOT / "user_data"

# Singleton instances
_model: Optional[KernelModel] = None
_preprocessor: Optional[KernelPreprocessor] = None

# Debug storage
_last_request: Dict[str, Any] = {}


# ---------------------------------------------------------------------------
# Blueprint
# ---------------------------------------------------------------------------

kernel_bp = Blueprint("kernel", __name__)


# ---------------------------------------------------------------------------
# Model Loading
# ---------------------------------------------------------------------------

def get_model() -> KernelModel:
    """Get or create the model instance."""
    global _model
    
    if _model is None:
        if MODEL_PATH.exists():
            _model = KernelModel.load(MODEL_PATH)
        else:
            # Create default model (will use heuristics until trained)
            logger.warning(f"Model not found at {MODEL_PATH}, using default")
            _model = KernelModel(input_dim=get_preprocessor().total_input_dim)
    
    return _model


def get_preprocessor() -> KernelPreprocessor:
    """Get or create the preprocessor instance."""
    global _preprocessor
    
    if _preprocessor is None:
        _preprocessor = KernelPreprocessor(SCHEMA_PATH)
    
    return _preprocessor


# ---------------------------------------------------------------------------
# User Data Storage
# ---------------------------------------------------------------------------

def save_kernel_evaluation(
    user_id: str,
    responses: Dict[str, Any],
    free_text: str,
    result: PredictionResult,
    instrument_scores: Dict[str, float]
) -> str:
    """Save evaluation in RL-ready format."""
    USER_DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    eval_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    timestamp = datetime.now().isoformat()
    
    # RL-ready structure
    record = {
        "id": eval_id,
        "user_id": user_id,
        "timestamp": timestamp,
        "state": {
            "responses": responses,
            "free_text": free_text,
            "instrument_scores": instrument_scores
        },
        "action": {
            "model_version": result.model_version,
            "inference_mode": result.inference_mode
        },
        "outputs": result.to_dict(),
        "reward": {
            "user_feedback": None,  # To be filled later
            "clinical_validation": None
        }
    }
    
    # Append to user file
    user_file = USER_DATA_DIR / f"{user_id}_kernel.json"
    
    if user_file.exists():
        with open(user_file, "r", encoding="utf-8") as f:
            history = json.load(f)
    else:
        history = []
    
    history.append(record)
    
    with open(user_file, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2)
    
    return eval_id


# ---------------------------------------------------------------------------
# API Endpoints
# ---------------------------------------------------------------------------

@kernel_bp.route("/predict", methods=["POST"])
def predict():
    """
    Run KERNEL inference with uncertainty estimation.
    
    Request Body:
    {
        "responses": {
            "phq9_1": 2,
            "phq9_2": 1,
            "gad7_1": 2,
            "stress_work": 75,
            ...
        },
        "free_text": "I've been feeling anxious...",
        "user_id": "optional_user_id",
        "save": true,
        "mc_samples": 10  # Optional, for uncertainty estimation
    }
    
    Response:
    {
        "scores": {
            "stress": {"mean": 45.2, "std": 8.3, "ci_lower": 38.9, "ci_upper": 51.5},
            "depression": {...},
            "anxiety": {...},
            "sleep_quality": {...},
            "wellbeing": {...}
        },
        "classifications": {
            "stress": "moderate",
            "depression": "mild",
            ...
        },
        "instrument_scores": {
            "phq9_total": 12,
            "gad7_total": 8,
            ...
        },
        "flags": ["POOR_SLEEP"],
        "text_analysis": {
            "sentiment": {...},
            "clinical_keywords": {...}
        },
        "evaluation_id": "20251205_123456"
    }
    """
    global _last_request
    
    # Parse request
    payload = request.get_json(force=True, silent=True) or {}
    _last_request = {
        "timestamp": datetime.now().isoformat(),
        "payload": payload
    }
    
    responses = payload.get("responses", {})
    free_text = payload.get("free_text", "")
    user_id = payload.get("user_id", "anonymous")
    should_save = payload.get("save", True)
    mc_samples = payload.get("mc_samples", 10)
    
    logger.info(f"KERNEL predict request: user={user_id}, responses={len(responses)}, text_len={len(free_text)}")
    
    if not responses:
        return jsonify({"error": "No responses provided"}), 400
    
    try:
        # Preprocess
        preprocessor = get_preprocessor()
        processed = preprocessor.preprocess(responses, free_text)
        
        logger.debug(f"Preprocessed: tabular_dim={len(processed.tabular_vector)}, text_dim={len(processed.text_vector)}")
        
        # Get model and predict
        model = get_model()
        
        # Convert to tensor if using PyTorch
        try:
            import torch
            input_tensor = torch.tensor(processed.full_vector, dtype=torch.float32)
            result = model.predict(input_tensor, n_samples=mc_samples, use_mc_dropout=True)
        except ImportError:
            result = model.predict(processed.full_vector)
        
        # Build response
        response = result.to_dict()
        response["instrument_scores"] = processed.instrument_scores
        
        # Add text analysis
        if processed.text_features:
            response["text_analysis"] = {
                "sentiment": processed.text_features.sentiment,
                "clinical_keywords": processed.text_features.keywords,
                "clinical_flags": processed.text_features.clinical_flags,
                "word_count": processed.text_features.word_count
            }
        
        # Save if requested
        if should_save:
            eval_id = save_kernel_evaluation(
                user_id=user_id,
                responses=responses,
                free_text=free_text,
                result=result,
                instrument_scores=processed.instrument_scores
            )
            response["evaluation_id"] = eval_id
        
        _last_request["response"] = response
        
        logger.info(f"KERNEL prediction complete: stress={result.stress['mean']:.1f}, depression={result.depression['mean']:.1f}")
        
        return jsonify(response), 200
        
    except Exception as e:
        logger.exception(f"KERNEL prediction error: {e}")
        return jsonify({"error": str(e)}), 500


@kernel_bp.route("/schema", methods=["GET"])
def get_schema():
    """Get the assessment schema."""
    if not SCHEMA_PATH.exists():
        return jsonify({"error": "Schema not found"}), 404
    
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        schema = json.load(f)
    
    return jsonify(schema), 200


@kernel_bp.route("/status", methods=["GET"])
def status():
    """Check model status."""
    try:
        preprocessor = get_preprocessor()
        model = get_model()
        
        return jsonify({
            "status": "ok",
            "model_version": model.version,
            "dimensions": {
                "total_input": TARGET_INPUT_DIM,
                "tabular": preprocessor.tabular_dim,
                "text": preprocessor.text_encoder.vector_dim,
                "model_expected": EXPECTED_INPUT_DIM
            },
            "dimension_match": TARGET_INPUT_DIM == EXPECTED_INPUT_DIM,
            "model_path_exists": MODEL_PATH.exists(),
            "schema_path_exists": SCHEMA_PATH.exists()
        }), 200
        
    except Exception as e:
        logger.exception("Status check failed")
        return jsonify({
            "status": "error",
            "error": str(e)
        }), 500


@kernel_bp.route("/thresholds", methods=["GET"])
def thresholds():
    """Get clinical thresholds for all instruments."""
    if not SCHEMA_PATH.exists():
        return jsonify({"error": "Schema not found"}), 404
    
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        schema = json.load(f)
    
    return jsonify({
        "instruments": schema.get("instruments", {}),
        "output_targets": schema.get("output_targets", {})
    }), 200


@kernel_bp.route("/history", methods=["GET"])
def history():
    """Get user evaluation history."""
    user_id = request.args.get("user_id", "anonymous")
    limit = request.args.get("limit", 50, type=int)
    
    user_file = USER_DATA_DIR / f"{user_id}_kernel.json"
    
    if not user_file.exists():
        return jsonify({"evaluations": [], "total": 0}), 200
    
    with open(user_file, "r", encoding="utf-8") as f:
        history = json.load(f)
    
    # Sort by timestamp descending
    history.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    
    return jsonify({
        "evaluations": history[:limit],
        "total": len(history)
    }), 200


@kernel_bp.route("/debug", methods=["GET"])
def debug():
    """Get debug info for last request."""
    return jsonify(_last_request), 200

