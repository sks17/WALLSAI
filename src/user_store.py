"""
User Data Store Module

This module provides a lightweight persistence layer for storing user evaluation
history as JSON files. Designed to be easily migrated to a real database later.

Usage:
    from src.user_store import UserStore
    
    store = UserStore()
    
    # Append a prediction
    store.append_prediction(
        user_id="user@example.com",
        tabular_inputs={"feeling.nervous": "yes", ...},
        free_text="I feel tired",
        scores={"stress_score": 15.2, ...},
        prediction="Stress",
        confidence=0.72
    )
    
    # Load history
    history = store.load_history("user@example.com", limit=50)
    
    # Get stats
    stats = store.get_user_stats("user@example.com")

Data Structure:
    Each user has a JSON file with this structure:
    {
        "user_id": "user@example.com",
        "created_at": "2025-12-05T07:25:00Z",
        "updated_at": "2025-12-05T08:30:00Z",
        "events": [
            {
                "id": "a1b2c3d4",
                "timestamp": "2025-12-05T07:25:42Z",
                "inputs": {
                    "tabular": { "feeling.nervous": "yes", ... },
                    "free_text": "I feel tired but hopeful."
                },
                "outputs": {
                    "prediction": "Stress",
                    "confidence": 0.7234,
                    "probabilities": { "Stress": 0.72, ... },
                    "scores": {
                        "stress_score": 72.34,
                        "depression_score": 8.45,
                        "anxiety_score": 12.34,
                        "sleep_quality": 6.23
                    }
                }
            }
        ]
    }
"""
from __future__ import annotations

import json
import logging
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# Setup logging
logger = logging.getLogger("walls.user_store")


class UserStore:
    """
    A JSON-file-based user data store.
    
    Each user's data is stored in a separate JSON file for simplicity.
    Easy to migrate to SQLite/Postgres later by swapping this class.
    """
    
    def __init__(self, data_dir: Optional[Path] = None):
        """
        Initialize the store.
        
        Args:
            data_dir: Directory for user data files. Defaults to {project_root}/user_data/
        """
        if data_dir is None:
            root = Path(__file__).resolve().parent.parent
            data_dir = root / "user_data"
        
        self.data_dir = Path(data_dir)
        self._ensure_dir()
    
    def _ensure_dir(self):
        """Create data directory if it doesn't exist."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_user_file(self, user_id: str) -> Path:
        """Get the file path for a user's data."""
        # Sanitize user_id for filename
        safe_id = "".join(c if c.isalnum() or c in "._-@" else "_" for c in user_id)
        return self.data_dir / f"{safe_id}.json"
    
    def _load_user_data(self, user_id: str) -> Dict[str, Any]:
        """Load a user's data from disk."""
        file_path = self._get_user_file(user_id)
        
        if not file_path.exists():
            return {
                "user_id": user_id,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
                "events": []
            }
        
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse user data for {user_id}: {e}")
            return {
                "user_id": user_id,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
                "events": [],
                "_parse_error": str(e)
            }
    
    def _save_user_data(self, user_id: str, data: Dict[str, Any]) -> None:
        """Save a user's data to disk."""
        file_path = self._get_user_file(user_id)
        data["updated_at"] = datetime.now().isoformat()
        
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def append_prediction(
        self,
        user_id: str,
        tabular_inputs: Dict[str, Any],
        free_text: Optional[str],
        scores: Dict[str, float],
        prediction: Optional[str] = None,
        confidence: Optional[float] = None,
        probabilities: Optional[Dict[str, float]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Append a prediction event to a user's history.
        
        Args:
            user_id: User identifier
            tabular_inputs: Survey responses (feature -> value)
            free_text: Optional free-text input
            scores: Predicted scores (stress_score, depression_score, etc.)
            prediction: Optional predicted class (Anxiety, Depression, etc.)
            confidence: Optional model confidence
            probabilities: Optional probability per class
            metadata: Optional extra metadata
        
        Returns:
            Event ID
        """
        event_id = str(uuid.uuid4())[:8]
        timestamp = datetime.now().isoformat()
        
        event = {
            "id": event_id,
            "timestamp": timestamp,
            "inputs": {
                "tabular": tabular_inputs,
                "free_text": free_text or ""
            },
            "outputs": {
                "prediction": prediction,
                "confidence": confidence,
                "probabilities": probabilities or {},
                "scores": scores
            }
        }
        
        if metadata:
            event["metadata"] = metadata
        
        # Load, append, save
        data = self._load_user_data(user_id)
        data["events"].append(event)
        self._save_user_data(user_id, data)
        
        logger.info(f"Saved prediction event {event_id} for user {user_id}")
        
        return event_id
    
    def load_history(
        self,
        user_id: str,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Load a user's prediction history.
        
        Args:
            user_id: User identifier
            limit: Maximum number of events to return
            offset: Number of events to skip
        
        Returns:
            List of events, newest first
        """
        data = self._load_user_data(user_id)
        events = data.get("events", [])
        
        # Sort by timestamp descending (newest first)
        events.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        
        return events[offset:offset + limit]
    
    def get_latest_prediction(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get the most recent prediction for a user."""
        history = self.load_history(user_id, limit=1)
        return history[0] if history else None
    
    def get_user_stats(self, user_id: str) -> Dict[str, Any]:
        """
        Get statistics for a user.
        
        Returns:
            Dict with stats: total_predictions, first_prediction, last_prediction, etc.
        """
        data = self._load_user_data(user_id)
        events = data.get("events", [])
        
        if not events:
            return {
                "user_id": user_id,
                "total_predictions": 0,
                "first_prediction": None,
                "last_prediction": None,
                "score_averages": None
            }
        
        # Sort by timestamp
        sorted_events = sorted(events, key=lambda x: x.get("timestamp", ""))
        
        # Calculate averages
        score_sums = {"stress_score": 0, "depression_score": 0, "anxiety_score": 0, "sleep_quality": 0}
        score_counts = {"stress_score": 0, "depression_score": 0, "anxiety_score": 0, "sleep_quality": 0}
        
        for event in events:
            scores = event.get("outputs", {}).get("scores", {})
            for key in score_sums.keys():
                if key in scores and scores[key] is not None:
                    score_sums[key] += scores[key]
                    score_counts[key] += 1
        
        averages = {
            key: round(score_sums[key] / score_counts[key], 2) if score_counts[key] > 0 else None
            for key in score_sums.keys()
        }
        
        return {
            "user_id": user_id,
            "total_predictions": len(events),
            "first_prediction": sorted_events[0].get("timestamp"),
            "last_prediction": sorted_events[-1].get("timestamp"),
            "score_averages": averages
        }
    
    def compute_trends(self, user_id: str, window: int = 5) -> Dict[str, Any]:
        """
        Compute trends over the last N predictions.
        
        Args:
            user_id: User identifier
            window: Number of recent predictions to analyze
        
        Returns:
            Dict with trends for each score type
        """
        history = self.load_history(user_id, limit=window)
        
        if len(history) < 2:
            return {"status": "insufficient_data", "required": 2, "available": len(history)}
        
        trends = {}
        
        for score_key in ["stress_score", "depression_score", "anxiety_score", "sleep_quality"]:
            values = [
                h.get("outputs", {}).get("scores", {}).get(score_key)
                for h in reversed(history)  # Oldest to newest
            ]
            values = [v for v in values if v is not None]
            
            if len(values) >= 2:
                first = values[0]
                last = values[-1]
                change = last - first
                
                trends[score_key] = {
                    "direction": "up" if change > 1 else ("down" if change < -1 else "stable"),
                    "change": round(change, 2),
                    "first_value": round(first, 2),
                    "last_value": round(last, 2),
                    "data_points": len(values)
                }
        
        return {"status": "ok", "trends": trends, "window": window}
    
    def get_all_users(self) -> List[str]:
        """Get list of all user IDs with stored data."""
        users = []
        for file in self.data_dir.glob("*.json"):
            try:
                with open(file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    user_id = data.get("user_id", file.stem)
                    users.append(user_id)
            except Exception:
                continue
        return users
    
    def delete_user(self, user_id: str) -> bool:
        """Delete all data for a user."""
        file_path = self._get_user_file(user_id)
        if file_path.exists():
            file_path.unlink()
            logger.info(f"Deleted user data for {user_id}")
            return True
        return False
    
    def export_all(self) -> Dict[str, Any]:
        """Export all user data (for backup/migration)."""
        all_data = {}
        for user_id in self.get_all_users():
            all_data[user_id] = self._load_user_data(user_id)
        return all_data


# ---------------------------------------------------------------------------
# Convenience Functions (for use without instantiating UserStore)
# ---------------------------------------------------------------------------

_default_store: Optional[UserStore] = None


def get_store() -> UserStore:
    """Get or create the default UserStore instance."""
    global _default_store
    if _default_store is None:
        _default_store = UserStore()
    return _default_store


def append_prediction(user_id: str, **kwargs) -> str:
    """Append a prediction to a user's history using the default store."""
    return get_store().append_prediction(user_id, **kwargs)


def load_history(user_id: str, limit: int = 100) -> List[Dict[str, Any]]:
    """Load a user's history using the default store."""
    return get_store().load_history(user_id, limit=limit)


def get_latest_prediction(user_id: str) -> Optional[Dict[str, Any]]:
    """Get the latest prediction for a user using the default store."""
    return get_store().get_latest_prediction(user_id)


def get_user_stats(user_id: str) -> Dict[str, Any]:
    """Get user stats using the default store."""
    return get_store().get_user_stats(user_id)


# ---------------------------------------------------------------------------
# CLI for testing
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("UserStore Module Test")
    print("=" * 50)
    
    store = UserStore()
    
    # Test with a sample user
    test_user = "test_user_debug"
    
    print(f"1. Adding sample prediction for '{test_user}'...")
    event_id = store.append_prediction(
        user_id=test_user,
        tabular_inputs={"feeling.nervous": "yes", "hopelessness": "no"},
        free_text="I feel a bit stressed today",
        scores={
            "stress_score": 45.2,
            "depression_score": 12.3,
            "anxiety_score": 23.4,
            "sleep_quality": 7.5
        },
        prediction="Stress",
        confidence=0.72
    )
    print(f"   Event ID: {event_id}")
    
    print(f"\n2. Loading history for '{test_user}'...")
    history = store.load_history(test_user, limit=5)
    print(f"   Found {len(history)} events")
    
    print(f"\n3. Getting stats for '{test_user}'...")
    stats = store.get_user_stats(test_user)
    print(f"   Total predictions: {stats['total_predictions']}")
    print(f"   Score averages: {stats['score_averages']}")
    
    print(f"\n4. Computing trends for '{test_user}'...")
    trends = store.compute_trends(test_user)
    print(f"   Status: {trends['status']}")
    if trends.get('trends'):
        for key, trend in trends['trends'].items():
            print(f"   {key}: {trend['direction']} ({trend['change']:+.1f})")
    
    print("\n" + "=" * 50)
    print("Test complete!")

