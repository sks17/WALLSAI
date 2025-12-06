"""
Data package initializer.

Provides helpers for loading schemas and datasets.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

BASE_DIR = Path(__file__).resolve().parent
SCHEMA_PATH = BASE_DIR / "schema.json"


def load_schema() -> Dict[str, Any]:
    """Load the feature/label schema from JSON."""
    with SCHEMA_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


from .loader import load_schema as load_schema  # re-export for convenience
