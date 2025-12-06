# src/api.py
"""
Mental Health Prediction API

This module provides Flask API endpoints for:
- Running inference on trained models (PyTorch model)
- Storing and retrieving user evaluation history
- Computing metrics and trend analysis

Endpoints:
- POST /api/v2/predict - Run inference on user input
- GET /api/v2/history - Get evaluation history
- GET /api/v2/metrics - Get computed metrics and trends
- GET /api/v2/status - Check API and model status
- GET /api/v2/debug - Debug endpoint (shows last prediction details)

Enable debug logging by setting environment variable:
    WALLS_DEBUG=1 python app.py
"""
from __future__ import annotations

import json
import logging
import os
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from flask import Blueprint, jsonify, request

# Ensure project root is in path
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Import PyTorch model inference (the working one)
from api.predict import run_inference as pytorch_run_inference, _load_metadata

# ---------------------------------------------------------------------------
# Logging Configuration
# ---------------------------------------------------------------------------

# Check for debug mode via environment variable
DEBUG_MODE = True

# Configure logging
logging.basicConfig(
    level=logging.DEBUG if DEBUG_MODE else logging.INFO,
    format='%(asctime)s | %(name)s | %(levelname)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("walls.api")

# Store last prediction details for debugging
_last_prediction_debug = {
    "raw_payload": None,
    "parsed_answers": None,
    "answers_list": None,
    "feature_order": None,
    "pytorch_result": None,
    "final_response": None,
    "timestamp": None,
    "errors": []
}


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Note: Local file storage removed in favor of account-based Firestore persistence
# USER_DATA_DIR is deprecated

# Clinical thresholds for flagging concerning values
THRESHOLDS = {
    "depression_score": {
        "minimal": 5,
        "mild": 10,
        "moderate": 15,
        "severe": 20,
    },
    "anxiety_score": {
        "minimal": 5,
        "mild": 10,
        "moderate": 15,
        "severe": 21,
    },
    "stress_score": {
        "low": 10,
        "moderate": 20,
        "high": 30,
    },
    "sleep_quality": {
        "good": 5,
        "fair": 10,
        "poor": 15,
    },
}


# ---------------------------------------------------------------------------
# Blueprint
# ---------------------------------------------------------------------------

api_v2_bp = Blueprint("api_v2", __name__)


# ---------------------------------------------------------------------------
# User Data Storage
# ---------------------------------------------------------------------------

def ensure_user_data_dir():
    """Deprecated: Local storage removed in favor of Firestore."""
    pass


def save_evaluation(
    user_id: str,
    input_data: Dict[str, Any],
    scores: Dict[str, Optional[float]],
    free_text: Optional[str] = None,
    intensity_values: Optional[Dict[str, float]] = None,
    prediction: Optional[str] = None,
    confidence: Optional[float] = None,
    probabilities: Optional[Dict[str, float]] = None,
    classifications: Optional[Dict[str, str]] = None
) -> str:
    """
    Save a user evaluation to Firestore (account-based persistence).
    
    Args:
        user_id: User identifier (Firebase UID)
        input_data: User's input answers
        scores: Predicted scores
        free_text: Optional free text input
        intensity_values: Optional dict of intensity slider values (0-100)
        prediction: Primary prediction label
        confidence: Prediction confidence
        probabilities: All class probabilities
        classifications: Score classifications
    
    Returns:
        Evaluation ID
    """
    eval_id = str(uuid.uuid4())[:8]
    timestamp = datetime.now().isoformat()
    
    record = {
        "id": eval_id,
        "eval_id": eval_id,
        "user_id": user_id,
        "timestamp": timestamp,
        "input": input_data,
        "inputs": input_data,
        "free_text": free_text,
        "text_features": free_text,
        "scores": scores,
    }
    
    # Add optional fields
    if intensity_values:
        record["intensity_values"] = intensity_values
    if prediction:
        record["prediction"] = prediction
    if confidence is not None:
        record["confidence"] = confidence
    if probabilities:
        record["probabilities"] = probabilities
    if classifications:
        record["classifications"] = classifications
    
    # Save to Firestore (account-based persistence only)
    try:
        from services import save_evaluation as firestore_save
        firestore_save(user_id, eval_id, record)
        logger.info(f"[API] Saved evaluation to Firestore: {eval_id}")
    except ImportError:
        logger.warning("[API] Firestore not available - evaluation not persisted")
    except Exception as e:
        logger.warning(f"[API] Firestore save failed: {e}")
    
    # Also save via backend user API
    try:
        from backend.user_store import add_survey_entry
        add_survey_entry(user_id, record)
    except ImportError:
        pass
    except Exception as e:
        logger.debug(f"[API] Backend save failed: {e}")
    
    return eval_id


def get_user_history(user_id: str) -> List[Dict[str, Any]]:
    """
    Get all evaluations for a user from Firestore (account-based).
    
    New users will have empty history (returns []).
    
    Args:
        user_id: User identifier (Firebase UID)
    
    Returns:
        List of evaluation records, sorted by timestamp (newest first)
    """
    # Try Firestore via services module
    try:
        from services import get_evaluations as firestore_get
        records = firestore_get(user_id, limit=100)
        if records:
            logger.debug(f"[API] Loaded {len(records)} evaluations from Firestore")
            return records
    except ImportError:
        logger.debug("[API] Services module not available")
    except Exception as e:
        logger.warning(f"[API] Firestore history load failed: {e}")
    
    # Try backend user_store
    try:
        from backend.user_store import load_survey_history
        records = load_survey_history(user_id, limit=100)
        if records:
            logger.debug(f"[API] Loaded {len(records)} evaluations from backend")
            return records
    except ImportError:
        logger.debug("[API] Backend module not available")
    except Exception as e:
        logger.warning(f"[API] Backend history load failed: {e}")
    
    # New user or no data - return empty list (all zeros)
    logger.debug(f"[API] No history found for user: {user_id}")
    return []


def get_all_evaluations() -> List[Dict[str, Any]]:
    """
    Get all evaluations across all users.
    
    Note: This function is deprecated in favor of per-user Firestore queries.
    For admin purposes only.
    
    Returns:
        List of all evaluation records (empty if Firestore not available)
    """
    logger.warning("[API] get_all_evaluations is deprecated - use per-user queries")
    return []


# ---------------------------------------------------------------------------
# Metrics Computation
# ---------------------------------------------------------------------------

def classify_score(score: Optional[float], score_type: str) -> str:
    """
    Classify a score into severity categories.
    
    Args:
        score: Numeric score value
        score_type: Type of score (depression_score, anxiety_score, etc.)
    
    Returns:
        Severity classification string
    """
    if score is None:
        return "unknown"
    
    thresholds = THRESHOLDS.get(score_type, {})
    
    if not thresholds:
        return "unknown"
    
    # Find the highest threshold the score exceeds
    classification = "minimal"
    for level, threshold in sorted(thresholds.items(), key=lambda x: x[1]):
        if score >= threshold:
            classification = level
    
    return classification


def compute_metrics(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Compute metrics from evaluation history.
    
    Args:
        records: List of evaluation records
    
    Returns:
        Dict with computed metrics
    """
    if not records:
        return {
            "total_evaluations": 0,
            "latest_scores": None,
            "trends": None,
            "flags": [],
        }
    
    latest = records[0] if records else None
    latest_scores = latest.get("scores", {}) if latest else {}
    
    # Compute trends (delta from previous)
    trends = {}
    if len(records) >= 2:
        prev_scores = records[1].get("scores", {})
        for key in ["stress_score", "depression_score", "anxiety_score", "sleep_quality"]:
            curr = latest_scores.get(key)
            prev = prev_scores.get(key)
            if curr is not None and prev is not None:
                trends[key] = {
                    "delta": round(curr - prev, 2),
                    "direction": "up" if curr > prev else "down" if curr < prev else "stable",
                }
    
    # Compute flags for concerning values
    flags = []
    for key, value in latest_scores.items():
        if value is None:
            continue
        
        classification = classify_score(value, key)
        
        if key == "depression_score" and classification in ("moderate", "severe"):
            flags.append({
                "type": "warning",
                "score": key,
                "value": value,
                "message": f"Depression score ({value}) indicates {classification} severity",
            })
        
        if key == "anxiety_score" and classification in ("moderate", "severe"):
            flags.append({
                "type": "warning",
                "score": key,
                "value": value,
                "message": f"Anxiety score ({value}) indicates {classification} severity",
            })
        
        if key == "stress_score" and classification == "high":
            flags.append({
                "type": "warning",
                "score": key,
                "value": value,
                "message": f"Stress score ({value}) indicates high stress levels",
            })
    
    # Compute averages over time
    averages = {}
    for key in ["stress_score", "depression_score", "anxiety_score", "sleep_quality"]:
        values = [r.get("scores", {}).get(key) for r in records]
        values = [v for v in values if v is not None]
        if values:
            averages[key] = round(sum(values) / len(values), 2)
    
    return {
        "total_evaluations": len(records),
        "latest_scores": latest_scores,
        "latest_timestamp": latest.get("timestamp") if latest else None,
        "trends": trends if trends else None,
        "flags": flags,
        "averages": averages,
        "classifications": {
            key: classify_score(latest_scores.get(key), key)
            for key in ["stress_score", "depression_score", "anxiety_score", "sleep_quality"]
        },
    }


# ---------------------------------------------------------------------------
# API Endpoints
# ---------------------------------------------------------------------------

def get_feature_order() -> List[str]:
    """Get the expected feature order from schema.json."""
    try:
        metadata = _load_metadata()
        return metadata.get("features", [])
    except Exception as e:
        logger.error(f"Failed to load feature order: {e}")
        return []


def convert_answers_to_list(answers: Dict[str, Any], feature_order: List[str]) -> List[str]:
    """
    Convert a dict of answers to a list in the correct order for the model.
    
    Args:
        answers: Dict with feature names as keys and yes/no as values
        feature_order: List of feature names in the order expected by the model
    
    Returns:
        List of yes/no values in the correct order
    
    Note:
        Handles intensity slider values (0-100) by converting them to yes/no
        using a threshold of 50. The raw intensity values are preserved separately.
    """
    # Features that use intensity sliders (0-100 scale)
    INTENSITY_FEATURES = {'hopelessness', 'anger', 'feeling.tired'}
    
    result = []
    for feature in feature_order:
        # Get value with case-insensitive matching
        value = answers.get(feature, "no")
        
        # Check for intensity values (stored as feature_intensity)
        intensity_key = f"{feature}_intensity"
        if intensity_key in answers and feature in INTENSITY_FEATURES:
            # Use intensity value with 50 threshold
            intensity = answers[intensity_key]
            if isinstance(intensity, (int, float)):
                value = "yes" if intensity >= 50 else "no"
                result.append(value)
                continue
        
        # Normalize to lowercase yes/no
        if isinstance(value, str):
            value = value.lower().strip()
            if value in ("yes", "true", "1", "y"):
                value = "yes"
            else:
                value = "no"
        elif isinstance(value, bool):
            value = "yes" if value else "no"
        elif isinstance(value, (int, float)):
            # For intensity slider values (0-100), use threshold of 50
            if value > 50:
                value = "yes"
            elif value > 0 and value <= 1:
                # Legacy: values like 0.5 meant yes
                value = "yes"
            else:
                value = "no"
        else:
            value = "no"
        
        result.append(value)
    
    return result


def extract_intensity_values(answers: Dict[str, Any]) -> Dict[str, float]:
    """
    Extract intensity slider values from answers dict.
    
    Args:
        answers: Dict with feature names as keys
    
    Returns:
        Dict with intensity feature names and their values (0-100)
    """
    intensities = {}
    for key, value in answers.items():
        if key.endswith('_intensity') and isinstance(value, (int, float)):
            intensities[key] = value
    return intensities


@api_v2_bp.route("/status", methods=["GET"])
def status():
    """
    Check API and model status.
    
    Returns:
        JSON with API status and model availability
    """
    try:
        metadata = _load_metadata()
        has_model = Path(ROOT / "ml" / "model.pt").exists()
        
        return jsonify({
            "status": "ok",
            "model_loaded": has_model,
            "model_version": metadata.get("version"),
            "features": metadata.get("features", []),
            "labels": metadata.get("labels", []),
        }), 200
    except Exception as e:
        return jsonify({
            "status": "error",
            "error": str(e)
        }), 500


@api_v2_bp.route("/predict", methods=["POST"])
def predict():
    """
    Run inference on user input using the PyTorch model.
    
    Expects JSON payload:
    {
        "answers": { 
            "feeling.nervous": "Yes",
            "panic": "No",
            ... (24 features from schema.json)
        },
        "free_text": "optional string",
        "user_id": "optional user identifier",
        "save": true/false (default: true)
    }
    
    Returns:
    {
        "prediction": "Anxiety/Depression/Loneliness/Stress/Normal",
        "confidence": float (0-1),
        "probabilities": {
            "Anxiety": float,
            "Depression": float,
            "Loneliness": float,
            "Stress": float,
            "Normal": float
        },
        "scores": {
            "stress_score": float (computed from probability),
            "depression_score": float,
            "anxiety_score": float,
            "sleep_quality": float
        },
        "classifications": {...},
        "evaluation_id": "string (if saved)"
    }
    """
    global _last_prediction_debug
    
    # Reset debug state
    _last_prediction_debug = {
        "raw_payload": None,
        "parsed_answers": None,
        "answers_list": None,
        "feature_order": None,
        "pytorch_result": None,
        "final_response": None,
        "timestamp": datetime.now().isoformat(),
        "errors": []
    }
    
    payload = request.get_json(force=True, silent=True) or {}
    _last_prediction_debug["raw_payload"] = payload
    
    logger.info("=" * 60)
    logger.info("PREDICTION REQUEST RECEIVED")
    logger.info("=" * 60)
    logger.debug(f"Raw payload: {json.dumps(payload, indent=2)}")
    
    # Extract inputs
    answers = payload.get("answers", {})
    free_text = payload.get("free_text", "")
    user_id = payload.get("user_id", "anonymous")
    should_save = payload.get("save", True)
    
    _last_prediction_debug["parsed_answers"] = {
        "answers": answers,
        "free_text": free_text,
        "user_id": user_id,
        "answer_count": len(answers)
    }
    
    logger.info(f"User ID: {user_id}")
    logger.info(f"Answer count: {len(answers)}")
    logger.info(f"Free text length: {len(free_text)} chars")
    logger.debug(f"Answer keys: {list(answers.keys())}")
    
    if not isinstance(answers, dict):
        error_msg = "Invalid payload: 'answers' must be a dictionary of feature values"
        _last_prediction_debug["errors"].append(error_msg)
        logger.error(error_msg)
        return jsonify({"error": error_msg}), 400
    
    try:
        # Get feature order from schema
        feature_order = get_feature_order()
        _last_prediction_debug["feature_order"] = feature_order
        
        if not feature_order:
            error_msg = "Could not load feature schema"
            _last_prediction_debug["errors"].append(error_msg)
            logger.error(error_msg)
            return jsonify({"error": error_msg}), 500
        
        logger.info(f"Feature schema loaded: {len(feature_order)} features expected")
        
        # Check which features are provided vs missing
        provided_features = set(answers.keys())
        expected_features = set(feature_order)
        matched = provided_features & expected_features
        missing = expected_features - provided_features
        extra = provided_features - expected_features
        
        logger.info(f"Features matched: {len(matched)}/{len(feature_order)}")
        if missing:
            logger.warning(f"Missing features (will default to 'no'): {list(missing)[:5]}{'...' if len(missing) > 5 else ''}")
        if extra:
            logger.warning(f"Extra features (will be ignored): {list(extra)}")
        
        # Convert answers dict to ordered list
        answers_list = convert_answers_to_list(answers, feature_order)
        _last_prediction_debug["answers_list"] = answers_list
        
        # Count yes/no distribution
        yes_count = sum(1 for a in answers_list if a == "yes")
        no_count = sum(1 for a in answers_list if a == "no")
        logger.info(f"Yes/No distribution: {yes_count} yes, {no_count} no")
        logger.debug(f"Ordered answers: {answers_list}")
        
        # Run PyTorch inference
        logger.info("Running PyTorch inference...")
        result = pytorch_run_inference(answers_list)
        _last_prediction_debug["pytorch_result"] = result
        
        logger.info(f"Model prediction: {result.get('prediction')}")
        logger.info(f"Model confidence: {result.get('confidence'):.4f}")
        logger.debug(f"All probabilities: {result.get('probabilities')}")
        
        # Extract prediction info
        prediction = result.get("prediction", "Normal")
        confidence = result.get("confidence", 0.0)
        probabilities = result.get("probabilities", {})
        
        # Convert probabilities to numeric scores (scale 0-100 for display)
        # Higher probability = higher score for that condition
        scores = {
            "stress_score": round(probabilities.get("Stress", 0) * 100, 2),
            "depression_score": round(probabilities.get("Depression", 0) * 100, 2),
            "anxiety_score": round(probabilities.get("Anxiety", 0) * 100, 2),
            "sleep_quality": round((1 - probabilities.get("Stress", 0) - probabilities.get("Anxiety", 0) / 2) * 10, 2),
        }
        
        # Ensure sleep quality is positive and bounded
        scores["sleep_quality"] = max(0, min(10, scores["sleep_quality"]))
        
        logger.info(f"Computed scores: stress={scores['stress_score']}, depression={scores['depression_score']}, anxiety={scores['anxiety_score']}, sleep={scores['sleep_quality']}")
        
        # Compute classifications based on prediction
        classifications = {
            "stress_score": "high" if prediction == "Stress" else ("moderate" if probabilities.get("Stress", 0) > 0.3 else "low"),
            "depression_score": "severe" if prediction == "Depression" else ("moderate" if probabilities.get("Depression", 0) > 0.3 else "minimal"),
            "anxiety_score": "severe" if prediction == "Anxiety" else ("moderate" if probabilities.get("Anxiety", 0) > 0.3 else "minimal"),
            "sleep_quality": "poor" if prediction in ["Stress", "Anxiety"] else "good",
        }
        
        response = {
            "prediction": prediction,
            "confidence": round(confidence, 4),
            "probabilities": {k: round(v, 4) for k, v in probabilities.items()},
            "scores": scores,
            "classifications": classifications,
        }
        
        # Extract intensity values for saving
        intensity_values = extract_intensity_values(answers)
        if intensity_values:
            response["intensity_values"] = intensity_values
            logger.info(f"Intensity values: {intensity_values}")
        
        # Save evaluation if requested
        if should_save:
            eval_id = save_evaluation(
                user_id=user_id,
                input_data=answers,
                scores=scores,
                free_text=free_text if free_text else None,
                intensity_values=intensity_values if intensity_values else None,
                prediction=prediction,
                confidence=confidence,
                probabilities=probabilities,
                classifications=classifications
            )
            response["evaluation_id"] = eval_id
            logger.info(f"Evaluation saved: {eval_id}")
        
        _last_prediction_debug["final_response"] = response
        
        logger.info("=" * 60)
        logger.info(f"PREDICTION COMPLETE: {prediction} ({confidence:.1%} confidence)")
        logger.info("=" * 60)
        
        return jsonify(response), 200
        
    except Exception as e:
        error_msg = str(e)
        _last_prediction_debug["errors"].append(error_msg)
        logger.exception(f"Prediction error: {e}")
        return jsonify({"error": error_msg}), 500


@api_v2_bp.route("/debug", methods=["GET"])
def debug():
    """
    Get debug information about the last prediction.
    
    Useful for troubleshooting feature alignment and model behavior.
    Only available when WALLS_DEBUG=1 environment variable is set.
    """
    if not DEBUG_MODE:
        return jsonify({
            "error": "Debug endpoint disabled. Set WALLS_DEBUG=1 to enable."
        }), 403
    
    return jsonify(_last_prediction_debug), 200


@api_v2_bp.route("/history", methods=["GET"])
def history():
    """
    Get evaluation history.
    
    Query params:
        user_id: Optional user identifier (default: all users)
        limit: Max number of records (default: 50)
    
    Returns:
    {
        "evaluations": [...],
        "total": int
    }
    """
    user_id = request.args.get("user_id")
    limit = request.args.get("limit", 50, type=int)
    
    if user_id:
        records = get_user_history(user_id)
    else:
        records = get_all_evaluations()
    
    # Apply limit
    records = records[:limit]
    
    return jsonify({
        "evaluations": records,
        "total": len(records),
    }), 200


@api_v2_bp.route("/metrics", methods=["GET"])
def metrics():
    """
    Get computed metrics and trends.
    
    Query params:
        user_id: Optional user identifier (default: all users)
    
    Returns:
    {
        "total_evaluations": int,
        "latest_scores": {...},
        "trends": {...},
        "flags": [...],
        "averages": {...},
        "classifications": {...}
    }
    """
    user_id = request.args.get("user_id")
    
    if user_id:
        records = get_user_history(user_id)
    else:
        records = get_all_evaluations()
    
    metrics_data = compute_metrics(records)
    
    return jsonify(metrics_data), 200


@api_v2_bp.route("/thresholds", methods=["GET"])
def thresholds():
    """
    Get clinical thresholds for score interpretation.
    
    Returns threshold values for all score types.
    """
    return jsonify(THRESHOLDS), 200

