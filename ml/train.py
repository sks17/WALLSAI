from __future__ import annotations

"""
Training script for the PyTorch MLP classifier.
"""
import os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Tuple

import torch
from torch import nn
from torch.utils.data import DataLoader, TensorDataset, random_split

from data.loader import load_schema, load_csv
from ml.model import MLPClassifier, ModelConfig
from ml.preprocess import Preprocessor

BASE_DIR = Path(__file__).resolve().parent
ROOT_DIR = BASE_DIR.parent
MODEL_PATH = BASE_DIR / "model.pt"
METADATA_PATH = BASE_DIR / "metadata.json"
DATA_PATH = ROOT_DIR / "Static" / "Data" / "dataset.csv"


def _build_dataloaders(
    features, labels, batch_size: int = 32, val_ratio: float = 0.2
) -> Tuple[DataLoader, DataLoader]:
    dataset = TensorDataset(features, labels)
    val_size = max(1, int(len(dataset) * val_ratio))
    train_size = len(dataset) - val_size
    train_set, val_set = random_split(dataset, [train_size, val_size])
    train_loader = DataLoader(train_set, batch_size=batch_size, shuffle=True)
    val_loader = DataLoader(val_set, batch_size=batch_size, shuffle=False)
    return train_loader, val_loader


def _evaluate(model: MLPClassifier, dataloader: DataLoader, device: torch.device) -> float:
    model.eval()
    correct = 0
    total = 0
    with torch.inference_mode():
        for x_batch, y_batch in dataloader:
            x_batch = x_batch.to(device)
            y_batch = y_batch.to(device)
            logits = model(x_batch)
            preds = torch.argmax(logits, dim=1)
            correct += (preds == y_batch).sum().item()
            total += y_batch.size(0)
    return correct / total if total else 0.0


def train(
    config: ModelConfig,
    data_path: str | Path = DATA_PATH,
    epochs: int = 25,
    lr: float = 1e-3,
    batch_size: int = 32,
) -> Dict[str, Any]:
    """Train the MLP classifier and persist artifacts."""
    df = load_csv(data_path)
    schema = load_schema()
    preprocessor = Preprocessor(schema["features"], schema["labels"])
    features, labels, label_to_idx = preprocessor.preprocess_batch(df, label_col="Disorder")

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = MLPClassifier(config).to(device)
    criterion = nn.CrossEntropyLoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=lr)

    train_loader, val_loader = _build_dataloaders(features, labels, batch_size=batch_size)

    for epoch in range(epochs):
        model.train()
        running_loss = 0.0
        for x_batch, y_batch in train_loader:
            x_batch = x_batch.to(device)
            y_batch = y_batch.to(device)
            optimizer.zero_grad()
            logits = model(x_batch)
            loss = criterion(logits, y_batch)
            loss.backward()
            optimizer.step()
            running_loss += loss.item() * x_batch.size(0)

        val_acc = _evaluate(model, val_loader, device)
        avg_loss = running_loss / len(train_loader.dataset)
        print(f"Epoch {epoch+1}/{epochs} - loss: {avg_loss:.4f} - val_acc: {val_acc:.4f}")

    # Persist artifacts
    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    torch.save(model.state_dict(), MODEL_PATH)

    version = datetime.now(timezone.utc).isoformat()
    relative_model_path = Path("ml") / "model.pt"
    relative_metadata_path = Path("ml") / "metadata.json"
    metadata: Dict[str, Any] = {
        "features": schema["features"],
        "labels": schema["labels"],
        "label_to_idx": label_to_idx,
        "version": version,
        "model_path": str(relative_model_path),
        "config": asdict(config),
    }
    with METADATA_PATH.open("w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    return {
        "model_path": str(relative_model_path),
        "metadata_path": str(relative_metadata_path),
        "version": version,
        "val_accuracy": val_acc,
    }


if __name__ == "__main__":
    default_schema = load_schema()
    cfg = ModelConfig(
        input_dim=len(default_schema["features"]),
        hidden_dims=[64, 32, 16],
        num_classes=len(default_schema["labels"]),
        dropout=0.1,
    )
    summary = train(cfg, DATA_PATH)
    print(summary)


