"""
Flask API routes for prediction and health checks.

These endpoints are JSON-first and should be mounted under `/api`.
"""
from __future__ import annotations

from flask import Blueprint, jsonify, request

from api.predict import run_inference

api_bp = Blueprint("api", __name__)


@api_bp.get("/ping")
def ping() -> tuple[dict[str, str], int]:
    """Liveness probe."""
    return {"status": "ok"}, 200


@api_bp.post("/predict")
def predict() -> tuple[dict[str, object], int]:
    """
    Fast prediction endpoint.

    Expects JSON payload with `answers` (list of yes/no strings) matching the schema order.
    Returns a JSON response containing prediction, confidence, and probabilities.
    """
    payload = request.get_json(force=True, silent=True) or {}
    answers = payload.get("answers")

    if not isinstance(answers, list):
        return (
            jsonify(
                {
                    "error": "Invalid payload: `answers` must be a list of yes/no strings.",
                }
            ),
            400,
        )

    try:
        result = run_inference(answers)
    except Exception as exc:  # pylint: disable=broad-except
        return jsonify({"error": str(exc)}), 400

    return jsonify(result), 200


