"""
Interpretability scaffolding.

Hooks for SHAP or Integrated Gradients will be added in a later phase.
"""
from __future__ import annotations

from typing import Any


def explain_prediction(model: Any, inputs: Any) -> dict[str, Any]:
    """
    Placeholder for model explainability.

    Returns a stub response until SHAP/IG is wired in.
    """
    return {
        "explanation": None,
        "detail": "Explainability not implemented yet. Add SHAP or IG here.",
    }


