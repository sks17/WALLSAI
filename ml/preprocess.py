from __future__ import annotations

"""
Preprocessing utilities for model inputs.

Transforms yes/no survey answers into numeric tensors aligned with the schema.
"""
import os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from dataclasses import dataclass
from typing import Iterable, List, Tuple

import torch
from torch import Tensor

from data import load_schema

YES_VALUES = {"yes", "y", "true", "1", True}
NO_VALUES = {"no", "n", "false", "0", False}


@dataclass
class Preprocessor:
    """Converts raw survey answers to model-ready tensors."""

    feature_names: List[str]
    label_names: List[str] | None = None

    def __init__(self, feature_names: List[str] | None = None, label_names: List[str] | None = None):
        schema = load_schema()
        self.feature_names = feature_names or schema["features"]
        self.label_names = label_names or schema.get("labels")

    def _to_float(self, value: object) -> float:
        val = str(value).strip().lower()
        if val in YES_VALUES:
            return 1.0
        if val in NO_VALUES:
            return 0.0
        raise ValueError(f"Unsupported answer value: {value!r}")

    def encode_answers(self, answers: Iterable[object]) -> Tensor:
        """
        Map ordered yes/no answers to a float tensor of shape (1, num_features).
        """
        normalized = [self._to_float(a) for a in answers]
        if len(normalized) != len(self.feature_names):
            raise ValueError(
                f"Expected {len(self.feature_names)} answers; got {len(normalized)}."
            )
        return torch.tensor([normalized], dtype=torch.float32)

    def preprocess_batch(
        self, df: pd.DataFrame, label_col: str = "Disorder"
    ) -> Tuple[Tensor, Tensor, dict[str, int]]:
        """
        Convert a DataFrame with yes/no feature columns (and labels) into tensors.

        Returns feature tensor, label tensor, and label-to-index mapping.
        """
        # Import pandas lazily so inference-only environments don't need it
        try:
            import pandas as pd  # type: ignore
        except ImportError as exc:  # pragma: no cover - only hit in prod without pandas
            raise ImportError(
                "pandas is required for training/preprocessing batches. "
                "Install requirements-dev.txt when running training jobs."
            ) from exc

        missing = [f for f in self.feature_names if f not in df.columns]
        if missing:
            raise ValueError(f"Missing expected features: {missing}")

        feature_df = df[self.feature_names].applymap(self._to_float)
        features = torch.tensor(feature_df.values, dtype=torch.float32)

        if label_col not in df.columns:
            raise ValueError(f"Label column '{label_col}' not found in DataFrame.")

        labels_series = df[label_col].astype(str)
        label_order = self.label_names or list(dict.fromkeys(labels_series.tolist()))
        label_to_idx = {label: idx for idx, label in enumerate(label_order)}
        labels = torch.tensor(
            [label_to_idx[label] for label in labels_series.tolist()],
            dtype=torch.long,
        )
        return features, labels, label_to_idx


