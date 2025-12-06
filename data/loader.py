"""
Dataset loading utilities.

Supports CSV loading now; Firestore or other sources can be added later.
"""
from __future__ import annotations

from pathlib import Path
from typing import Union, Dict, Any

import pandas as pd
import json

ROOT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_DATA_PATH = ROOT_DIR / "Static" / "Data" / "dataset.csv"
SCHEMA_PATH = Path(__file__).resolve().parent / "schema.json"


def load_csv(path: Union[str, Path] = DEFAULT_DATA_PATH) -> pd.DataFrame:
    """Load a CSV file into a DataFrame."""
    path = Path(path)
    return pd.read_csv(path)


def load_default() -> pd.DataFrame:
    """Load the default application dataset."""
    return load_csv(DEFAULT_DATA_PATH)


def load_schema() -> Dict[str, Any]:
    """Load the feature/label schema from JSON."""
    with SCHEMA_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


