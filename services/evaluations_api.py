# services/evaluations_api.py
"""
Evaluations API Blueprint

Provides Firestore-backed endpoints for:
- GET /api/evaluations - Get user's evaluations
- GET /api/evaluations/<id> - Get single evaluation
- DELETE /api/evaluations/<id> - Delete evaluation
- GET /api/evaluations/metrics - Get computed metrics

This replaces the file-based storage in src/api.py with Firestore.
"""
from __future__ import annotations

import logging
from typing import Any, Dict

from flask import Blueprint, jsonify, request, g

from .session_utils import get_current_user_id, require_auth_api
from .user_store import get_user_store, Evaluation

logger = logging.getLogger(__name__)

evaluations_bp = Blueprint('evaluations', __name__)


@evaluations_bp.route('/', methods=['GET'])
@evaluations_bp.route('/list', methods=['GET'])
def list_evaluations():
    """
    Get all evaluations for the current user.
    
    Query params:
        limit: Max number of evaluations (default: 50)
    
    Returns:
        {
            "evaluations": [...],
            "total": int
        }
    """
    user_id = get_current_user_id()
    
    if not user_id:
        # For anonymous users, return empty
        return jsonify({
            'evaluations': [],
            'total': 0,
            'message': 'Login to see your evaluation history'
        }), 200
    
    limit = request.args.get('limit', 50, type=int)
    store = get_user_store()
    
    evaluations = store.get_evaluations(user_id, limit=limit)
    
    return jsonify({
        'evaluations': [e.to_dict() for e in evaluations],
        'total': len(evaluations)
    }), 200


@evaluations_bp.route('/<eval_id>', methods=['GET'])
def get_evaluation(eval_id: str):
    """Get a specific evaluation."""
    user_id = get_current_user_id()
    
    if not user_id:
        return jsonify({'error': 'Authentication required'}), 401
    
    store = get_user_store()
    evaluation = store.get_evaluation(user_id, eval_id)
    
    if not evaluation:
        return jsonify({'error': 'Evaluation not found'}), 404
    
    return jsonify(evaluation.to_dict()), 200


@evaluations_bp.route('/<eval_id>', methods=['DELETE'])
@require_auth_api()
def delete_evaluation(eval_id: str):
    """Delete an evaluation."""
    user_id = g.user_id
    store = get_user_store()
    
    success = store.delete_evaluation(user_id, eval_id)
    
    if success:
        return jsonify({'success': True}), 200
    else:
        return jsonify({'error': 'Failed to delete evaluation'}), 400


@evaluations_bp.route('/metrics', methods=['GET'])
def get_metrics():
    """
    Get computed metrics for the current user.
    
    Returns:
        {
            "total_evaluations": int,
            "latest_scores": {...},
            "average_scores": {...},
            "trends": {...}
        }
    """
    user_id = get_current_user_id()
    
    if not user_id:
        return jsonify({
            'total_evaluations': 0,
            'latest_scores': None,
            'message': 'Login to see your metrics'
        }), 200
    
    store = get_user_store()
    metrics = store.compute_metrics(user_id)
    
    return jsonify(metrics), 200


@evaluations_bp.route('/latest', methods=['GET'])
def get_latest():
    """Get the most recent evaluation."""
    user_id = get_current_user_id()
    
    if not user_id:
        return jsonify({'error': 'Authentication required'}), 401
    
    store = get_user_store()
    evaluation = store.get_latest_evaluation(user_id)
    
    if not evaluation:
        return jsonify({
            'message': 'No evaluations yet',
            'evaluation': None
        }), 200
    
    return jsonify({'evaluation': evaluation.to_dict()}), 200


def save_prediction_to_firestore(
    user_id: str,
    inputs: Dict[str, Any],
    scores: Dict[str, float],
    prediction: str = None,
    confidence: float = None,
    probabilities: Dict[str, float] = None,
    classifications: Dict[str, str] = None,
    free_text: str = None,
    intensity_values: Dict[str, float] = None
) -> str:
    """
    Helper function to save a prediction to Firestore.
    
    Called from the prediction endpoint after running inference.
    
    Returns:
        Evaluation ID
    """
    store = get_user_store()
    
    evaluation = Evaluation(
        eval_id='',  # Will be generated
        user_id=user_id,
        timestamp='',  # Will be set
        inputs=inputs,
        scores=scores,
        prediction=prediction,
        confidence=confidence,
        probabilities=probabilities,
        classifications=classifications,
        text_features=free_text,
        intensity_values=intensity_values
    )
    
    eval_id = store.save_evaluation(evaluation)
    logger.info(f"[Evaluations] Saved evaluation {eval_id} for user {user_id}")
    
    return eval_id

