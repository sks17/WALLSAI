from __future__ import annotations

"""
Prediction helper module.

Loads the trained PyTorch model and runs inference on incoming survey answers.
"""
import os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List

import torch
from torch import Tensor
from ml.model import MLPClassifier, ModelConfig
from ml.preprocess import Preprocessor

BASE_DIR = Path(__file__).resolve().parent
MODEL_DIR = BASE_DIR.parent / "ml"
MODEL_PATH = MODEL_DIR / "model.pt"
METADATA_PATH = MODEL_DIR / "metadata.json"


@lru_cache(maxsize=1)
def _load_metadata() -> Dict[str, Any]:
    with METADATA_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


@lru_cache(maxsize=1)
def _load_model() -> MLPClassifier:
    metadata = _load_metadata()
    cfg = metadata.get("config") or {}
    config = ModelConfig(
        input_dim=cfg.get("input_dim", 24),
        hidden_dims=cfg.get("hidden_dims", [64, 32, 16]),
        num_classes=cfg.get("num_classes", 5),
        dropout=cfg.get("dropout", 0.1),
    )
    model = MLPClassifier.from_pretrained(MODEL_PATH, config)
    return model


def _to_probabilities(probs: Tensor, labels: List[str]) -> Dict[str, float]:
    return {label: float(prob) for label, prob in zip(labels, probs)}


def run_inference(answers: List[object]) -> dict[str, Any]:
    """
    Run inference on a list of yes/no answers.
    """
    metadata = _load_metadata()
    labels: List[str] = metadata["labels"]
    features_schema: List[str] = metadata["features"]

    preprocessor = Preprocessor(features_schema, labels)
    encoded: Tensor = preprocessor.encode_answers(answers)

    model = _load_model()
    with torch.inference_mode():
        probs_tensor = model.predict_proba(encoded)[0]

    confidences = _to_probabilities(probs_tensor.tolist(), labels)
    prediction_label = max(confidences.items(), key=lambda kv: kv[1])[0]

    return {
        "prediction": prediction_label,
        "confidence": confidences[prediction_label],
        "probabilities": confidences,
        "model_version": metadata.get("version"),
    }


