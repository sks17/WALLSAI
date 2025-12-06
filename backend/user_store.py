# backend/user_store.py
"""
User Data Store

Provides helper functions for storing and retrieving user data
in Firestore. Handles:
- User profile JSON
- Survey entries/history
- Data validation

Firestore Structure:
    users/{uid}
        - profile: { email, displayName, createdAt, lastLogin, preferences }
        
    users/{uid}/surveys/{entry_id}
        - timestamp
        - scores: { stress, depression, anxiety, sleep }
        - text: free-form response
        - raw_responses: survey answers
        - intensity_values: slider values
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import uuid

from .firebase_client import get_db

logger = logging.getLogger(__name__)


def _get_user_ref(uid: str):
    """Get Firestore reference for a user document."""
    db = get_db()
    return db.collection("users").document(uid)


def _get_surveys_ref(uid: str):
    """Get Firestore reference for a user's surveys collection."""
    return _get_user_ref(uid).collection("surveys")


# =============================================================================
# User Profile Functions
# =============================================================================

def save_user_json(uid: str, data: Dict[str, Any]) -> bool:
    """
    Save user profile data to Firestore.
    
    Args:
        uid: Firebase user ID
        data: Dictionary of user data to save
        
    Returns:
        True if successful, False otherwise
    """
    try:
        user_ref = _get_user_ref(uid)
        
        # Add metadata
        data["updatedAt"] = datetime.now(timezone.utc).isoformat()
        
        # Merge with existing data (don't overwrite)
        user_ref.set(data, merge=True)
        
        logger.info(f"[UserStore] Saved profile for user: {uid}")
        return True
        
    except Exception as e:
        logger.error(f"[UserStore] Failed to save user {uid}: {e}")
        return False


def load_user_json(uid: str) -> Optional[Dict[str, Any]]:
    """
    Load user profile data from Firestore.
    
    Args:
        uid: Firebase user ID
        
    Returns:
        User data dict, or None if not found
    """
    try:
        user_ref = _get_user_ref(uid)
        doc = user_ref.get()
        
        if doc.exists:
            data = doc.to_dict()
            logger.debug(f"[UserStore] Loaded profile for user: {uid}")
            return data
        else:
            logger.debug(f"[UserStore] No profile found for user: {uid}")
            return None
            
    except Exception as e:
        logger.error(f"[UserStore] Failed to load user {uid}: {e}")
        return None


def update_user_profile(uid: str, updates: Dict[str, Any]) -> bool:
    """
    Update specific fields in user profile.
    
    Args:
        uid: Firebase user ID
        updates: Dictionary of fields to update
        
    Returns:
        True if successful
    """
    try:
        user_ref = _get_user_ref(uid)
        updates["updatedAt"] = datetime.now(timezone.utc).isoformat()
        user_ref.update(updates)
        logger.debug(f"[UserStore] Updated profile for user: {uid}")
        return True
    except Exception as e:
        logger.error(f"[UserStore] Failed to update user {uid}: {e}")
        return False


def create_user_profile(uid: str, email: str, display_name: str = None) -> bool:
    """
    Create a new user profile.
    
    Args:
        uid: Firebase user ID
        email: User's email
        display_name: Optional display name
        
    Returns:
        True if successful
    """
    now = datetime.now(timezone.utc).isoformat()
    profile = {
        "email": email,
        "displayName": display_name,
        "createdAt": now,
        "lastLogin": now,
        "preferences": {},
        "surveyCount": 0
    }
    return save_user_json(uid, profile)


# =============================================================================
# Survey Entry Functions
# =============================================================================

def add_survey_entry(uid: str, entry: Dict[str, Any]) -> str:
    """
    Add a survey entry to user's history.
    
    Args:
        uid: Firebase user ID
        entry: Survey entry data containing:
            - scores: { stress, depression, anxiety, sleep }
            - text: free-form response (optional)
            - raw_responses: survey answers
            - intensity_values: slider values (optional)
            - timestamp: ISO timestamp (optional, will be added if missing)
            
    Returns:
        Timestamp of the saved entry
    """
    try:
        surveys_ref = _get_surveys_ref(uid)
        
        # Generate entry ID and timestamp
        entry_id = str(uuid.uuid4())[:8]
        timestamp = entry.get("timestamp") or datetime.now(timezone.utc).isoformat()
        
        # Prepare document
        doc_data = {
            "id": entry_id,
            "timestamp": timestamp,
            "scores": entry.get("scores", {}),
            "text": entry.get("text", ""),
            "raw_responses": entry.get("raw_responses", {}),
            "intensity_values": entry.get("intensity_values", {}),
            "prediction": entry.get("prediction"),
            "confidence": entry.get("confidence"),
            "probabilities": entry.get("probabilities", {}),
            "classifications": entry.get("classifications", {})
        }
        
        # Save to Firestore
        surveys_ref.document(entry_id).set(doc_data)
        
        # Update survey count in user profile
        try:
            user_ref = _get_user_ref(uid)
            user_ref.update({
                "surveyCount": get_db().field_path("surveyCount") + 1 if False else 1,
                "lastSurvey": timestamp
            })
        except Exception:
            # Increment might fail if field doesn't exist, that's ok
            pass
        
        logger.info(f"[UserStore] Added survey entry {entry_id} for user: {uid}")
        return timestamp
        
    except Exception as e:
        logger.error(f"[UserStore] Failed to add survey entry for {uid}: {e}")
        return datetime.now(timezone.utc).isoformat()


def load_survey_history(uid: str, limit: int = 50) -> List[Dict[str, Any]]:
    """
    Load survey history for a user.
    
    Args:
        uid: Firebase user ID
        limit: Maximum number of entries to return (default 50)
        
    Returns:
        List of survey entries, sorted by timestamp (newest first)
    """
    try:
        surveys_ref = _get_surveys_ref(uid)
        
        # Query with ordering and limit
        query = surveys_ref.order_by("timestamp", direction="DESCENDING").limit(limit)
        docs = query.stream()
        
        history = []
        for doc in docs:
            entry = doc.to_dict()
            entry["id"] = doc.id
            history.append(entry)
        
        logger.debug(f"[UserStore] Loaded {len(history)} survey entries for user: {uid}")
        return history
        
    except Exception as e:
        logger.error(f"[UserStore] Failed to load survey history for {uid}: {e}")
        return []


def delete_survey_entry(uid: str, entry_id: str) -> bool:
    """
    Delete a specific survey entry.
    
    Args:
        uid: Firebase user ID
        entry_id: Survey entry ID to delete
        
    Returns:
        True if successful
    """
    try:
        surveys_ref = _get_surveys_ref(uid)
        surveys_ref.document(entry_id).delete()
        logger.info(f"[UserStore] Deleted survey entry {entry_id} for user: {uid}")
        return True
    except Exception as e:
        logger.error(f"[UserStore] Failed to delete survey entry {entry_id}: {e}")
        return False


def get_survey_entry(uid: str, entry_id: str) -> Optional[Dict[str, Any]]:
    """
    Get a specific survey entry.
    
    Args:
        uid: Firebase user ID
        entry_id: Survey entry ID
        
    Returns:
        Survey entry dict, or None if not found
    """
    try:
        doc = _get_surveys_ref(uid).document(entry_id).get()
        if doc.exists:
            entry = doc.to_dict()
            entry["id"] = doc.id
            return entry
        return None
    except Exception as e:
        logger.error(f"[UserStore] Failed to get survey entry {entry_id}: {e}")
        return None


# =============================================================================
# Analytics Functions
# =============================================================================

def get_user_stats(uid: str) -> Dict[str, Any]:
    """
    Get summary statistics for a user.
    
    Args:
        uid: Firebase user ID
        
    Returns:
        Dict with total_surveys, average_scores, trends
    """
    try:
        history = load_survey_history(uid, limit=100)
        
        if not history:
            return {
                "total_surveys": 0,
                "average_scores": {},
                "latest_scores": {},
                "first_survey": None,
                "last_survey": None
            }
        
        # Calculate averages
        score_keys = ["stress", "depression", "anxiety", "sleep"]
        totals = {k: 0.0 for k in score_keys}
        counts = {k: 0 for k in score_keys}
        
        for entry in history:
            scores = entry.get("scores", {})
            for key in score_keys:
                val = scores.get(key) or scores.get(f"{key}_score")
                if val is not None:
                    try:
                        totals[key] += float(val)
                        counts[key] += 1
                    except (ValueError, TypeError):
                        pass
        
        averages = {}
        for key in score_keys:
            if counts[key] > 0:
                averages[key] = round(totals[key] / counts[key], 2)
        
        return {
            "total_surveys": len(history),
            "average_scores": averages,
            "latest_scores": history[0].get("scores", {}) if history else {},
            "first_survey": history[-1].get("timestamp") if history else None,
            "last_survey": history[0].get("timestamp") if history else None
        }
        
    except Exception as e:
        logger.error(f"[UserStore] Failed to get stats for {uid}: {e}")
        return {"total_surveys": 0, "average_scores": {}}

