from __future__ import annotations

"""
PyTorch MLP classifier implementation.

Architecture (fixed for this project):
- input_dim = 24
- hidden layers: [64, 32, 16]
- output_dim = 5

Includes a convenience loader for inference.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List

import torch
from torch import Tensor, nn


@dataclass
class ModelConfig:
    """Configuration for the MLP classifier."""

    input_dim: int
    hidden_dims: List[int]
    num_classes: int
    dropout: float = 0.1


class MLPClassifier(nn.Module):
    """Feed-forward MLP with ReLU activations and dropout."""

    def __init__(self, config: ModelConfig):
        super().__init__()
        self.config = config

        dims: List[int] = [config.input_dim, *config.hidden_dims, config.num_classes]
        layers: list[nn.Module] = []
        for in_dim, out_dim in zip(dims[:-2], dims[1:-1]):
            layers.append(nn.Linear(in_dim, out_dim))
            layers.append(nn.ReLU())
            layers.append(nn.Dropout(p=config.dropout))
        # Final classification layer (no dropout after)
        layers.append(nn.Linear(dims[-2], dims[-1]))

        self.network = nn.Sequential(*layers)

    def forward(self, x: Tensor) -> Tensor:
        """Forward pass returning logits."""
        return self.network(x)

    @torch.inference_mode()
    def predict_proba(self, x: Tensor) -> Tensor:
        """Return softmax probabilities for the provided inputs."""
        logits = self.forward(x)
        return torch.softmax(logits, dim=-1)

    @classmethod
    def from_pretrained(cls, model_path: Path | str, config: ModelConfig) -> "MLPClassifier":
        """
        Load a pretrained model from disk.

        Parameters
        ----------
        model_path : Path | str
            Path to the saved `.pt` file.
        config : ModelConfig
            Configuration describing the architecture.
        """
        model = cls(config)
        state_dict = torch.load(Path(model_path), map_location=torch.device("cpu"))
        model.load_state_dict(state_dict)
        model.eval()
        return model


