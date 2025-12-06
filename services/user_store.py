# services/user_store.py
"""
User Data Store

Abstraction layer for Firestore user data operations.
Handles:
- User profiles
- Evaluations (survey results)
- Notes and reflections
- Accessibility preferences

Firestore Structure:
    users/
        {user_id}/
            profile: { email, created_at, last_login, accessibility_prefs }
            
    users/{user_id}/evaluations/
        {eval_id}/
            timestamp, inputs, scores, flags, text_features, intensity_values
            
    users/{user_id}/notes/
        {note_id}/
            text, tags, timestamp, updated_at
"""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any, Dict, List, Optional

from .firebase_client import get_store, FIREBASE_AVAILABLE

logger = logging.getLogger(__name__)

# Global store instance
_user_store: Optional['UserStore'] = None


@dataclass
class UserProfile:
    """User profile data model."""
    user_id: str
    email: str
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    last_login: str = field(default_factory=lambda: datetime.now().isoformat())
    display_name: Optional[str] = None
    accessibility_prefs: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UserProfile':
        return cls(
            user_id=data.get('user_id', ''),
            email=data.get('email', ''),
            created_at=data.get('created_at', datetime.now().isoformat()),
            last_login=data.get('last_login', datetime.now().isoformat()),
            display_name=data.get('display_name'),
            accessibility_prefs=data.get('accessibility_prefs', {})
        )


@dataclass
class Evaluation:
    """Evaluation/survey result data model."""
    eval_id: str
    user_id: str
    timestamp: str
    inputs: Dict[str, Any]
    scores: Dict[str, float]
    prediction: Optional[str] = None
    confidence: Optional[float] = None
    probabilities: Optional[Dict[str, float]] = None
    classifications: Optional[Dict[str, str]] = None
    flags: Dict[str, Any] = field(default_factory=dict)
    text_features: Optional[str] = None
    intensity_values: Optional[Dict[str, float]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        # Remove None values for cleaner storage
        return {k: v for k, v in data.items() if v is not None}
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Evaluation':
        return cls(
            eval_id=data.get('eval_id', ''),
            user_id=data.get('user_id', ''),
            timestamp=data.get('timestamp', datetime.now().isoformat()),
            inputs=data.get('inputs', {}),
            scores=data.get('scores', {}),
            prediction=data.get('prediction'),
            confidence=data.get('confidence'),
            probabilities=data.get('probabilities'),
            classifications=data.get('classifications'),
            flags=data.get('flags', {}),
            text_features=data.get('text_features'),
            intensity_values=data.get('intensity_values')
        )


@dataclass
class Note:
    """User note/reflection data model."""
    note_id: str
    user_id: str
    text: str
    tags: List[str] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        return {k: v for k, v in data.items() if v is not None}
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Note':
        return cls(
            note_id=data.get('note_id', ''),
            user_id=data.get('user_id', ''),
            text=data.get('text', ''),
            tags=data.get('tags', []),
            timestamp=data.get('timestamp', datetime.now().isoformat()),
            updated_at=data.get('updated_at')
        )


class UserStore:
    """
    User data store abstraction.
    
    Uses Firestore exclusively. No local or in-memory persistence.
    """
    
    def __init__(self):
        self._store = get_store()
        self._is_firestore = FIREBASE_AVAILABLE
        if not self._store:
            raise RuntimeError("[UserStore] Firestore client not available. Set FIREBASE_SERVICE_ACCOUNT_JSON.")
        logger.info("[UserStore] Initialized with Firestore")
    
    # =========================================================================
    # Profile Operations
    # =========================================================================
    
    def get_profile(self, user_id: str) -> Optional[UserProfile]:
        """
        Get user profile by ID.
        
        Args:
            user_id: Firebase UID or session ID
        
        Returns:
            UserProfile if found, None otherwise
        """
        try:
            doc = self._store.collection('users').document(user_id).get()
            if doc.exists:
                data = doc.to_dict()
                data['user_id'] = user_id
                return UserProfile.from_dict(data)
            return None
        except Exception as e:
            logger.error(f"[UserStore] Error getting profile: {e}")
            return None
    
    def create_profile(self, profile: UserProfile) -> bool:
        """
        Create or update user profile.
        
        Args:
            profile: UserProfile to save
        
        Returns:
            True if successful
        """
        try:
            data = profile.to_dict()
            user_id = data.pop('user_id')
            self._store.collection('users').document(user_id).set(data, merge=True)
            logger.info(f"[UserStore] Profile saved for user: {user_id}")
            return True
        except Exception as e:
            logger.error(f"[UserStore] Error saving profile: {e}")
            return False
    
    def update_last_login(self, user_id: str) -> bool:
        """Update user's last login timestamp."""
        try:
            self._store.collection('users').document(user_id).update({
                'last_login': datetime.now().isoformat()
            })
            return True
        except Exception as e:
            logger.error(f"[UserStore] Error updating last login: {e}")
            return False
    
    def update_accessibility_prefs(self, user_id: str, prefs: Dict[str, Any]) -> bool:
        """Update user's accessibility preferences."""
        try:
            self._store.collection('users').document(user_id).update({
                'accessibility_prefs': prefs
            })
            return True
        except Exception as e:
            logger.error(f"[UserStore] Error updating prefs: {e}")
            return False
    
    # =========================================================================
    # Evaluation Operations
    # =========================================================================
    
    def save_evaluation(self, evaluation: Evaluation) -> str:
        """
        Save a new evaluation.
        
        Args:
            evaluation: Evaluation to save
        
        Returns:
            Evaluation ID
        """
        try:
            if not evaluation.eval_id:
                evaluation.eval_id = str(uuid.uuid4())[:8]
            
            data = evaluation.to_dict()
            eval_id = data.pop('eval_id')
            
            # Save to subcollection
            self._store.collection('users').document(evaluation.user_id) \
                .collection('evaluations').document(eval_id).set(data)
            
            logger.info(f"[UserStore] Evaluation saved: {eval_id} for user: {evaluation.user_id}")
            return eval_id
            
        except Exception as e:
            logger.error(f"[UserStore] Error saving evaluation: {e}")
            return ""
    
    def get_evaluation(self, user_id: str, eval_id: str) -> Optional[Evaluation]:
        """Get a specific evaluation."""
        try:
            doc = self._store.collection('users').document(user_id) \
                .collection('evaluations').document(eval_id).get()
            
            if doc.exists:
                data = doc.to_dict()
                data['eval_id'] = eval_id
                data['user_id'] = user_id
                return Evaluation.from_dict(data)
            return None
            
        except Exception as e:
            logger.error(f"[UserStore] Error getting evaluation: {e}")
            return None
    
    def get_evaluations(self, user_id: str, limit: int = 50) -> List[Evaluation]:
        """
        Get all evaluations for a user.
        
        Args:
            user_id: User ID
            limit: Maximum number of evaluations to return
        
        Returns:
            List of Evaluation objects, sorted by timestamp (newest first)
        """
        try:
            docs = self._store.collection('users').document(user_id) \
                .collection('evaluations') \
                .order_by('timestamp', direction='DESCENDING') \
                .limit(limit) \
                .stream()
            
            evaluations = []
            for doc in docs:
                data = doc.to_dict()
                data['eval_id'] = doc.id
                data['user_id'] = user_id
                evaluations.append(Evaluation.from_dict(data))
            
            return evaluations
            
        except Exception as e:
            logger.error(f"[UserStore] Error getting evaluations: {e}")
            return []
    
    def delete_evaluation(self, user_id: str, eval_id: str) -> bool:
        """Delete an evaluation."""
        try:
            self._store.collection('users').document(user_id) \
                .collection('evaluations').document(eval_id).delete()
            return True
        except Exception as e:
            logger.error(f"[UserStore] Error deleting evaluation: {e}")
            return False
    
    # =========================================================================
    # Notes Operations
    # =========================================================================
    
    def save_note(self, note: Note) -> str:
        """
        Save a new note.
        
        Args:
            note: Note to save
        
        Returns:
            Note ID
        """
        try:
            if not note.note_id:
                note.note_id = str(uuid.uuid4())[:8]
            
            data = note.to_dict()
            note_id = data.pop('note_id')
            
            self._store.collection('users').document(note.user_id) \
                .collection('notes').document(note_id).set(data)
            
            logger.info(f"[UserStore] Note saved: {note_id} for user: {note.user_id}")
            return note_id
            
        except Exception as e:
            logger.error(f"[UserStore] Error saving note: {e}")
            return ""
    
    def get_note(self, user_id: str, note_id: str) -> Optional[Note]:
        """Get a specific note."""
        try:
            doc = self._store.collection('users').document(user_id) \
                .collection('notes').document(note_id).get()
            
            if doc.exists:
                data = doc.to_dict()
                data['note_id'] = note_id
                data['user_id'] = user_id
                return Note.from_dict(data)
            return None
            
        except Exception as e:
            logger.error(f"[UserStore] Error getting note: {e}")
            return None
    
    def get_notes(self, user_id: str, limit: int = 100, tag: Optional[str] = None) -> List[Note]:
        """
        Get all notes for a user.
        
        Args:
            user_id: User ID
            limit: Maximum number of notes
            tag: Optional tag to filter by
        
        Returns:
            List of Note objects
        """
        try:
            query = self._store.collection('users').document(user_id) \
                .collection('notes') \
                .order_by('timestamp', direction='DESCENDING') \
                .limit(limit)
            
            docs = query.stream()
            
            notes = []
            for doc in docs:
                data = doc.to_dict()
                data['note_id'] = doc.id
                data['user_id'] = user_id
                note = Note.from_dict(data)
                
                # Filter by tag if specified
                if tag and tag not in note.tags:
                    continue
                    
                notes.append(note)
            
            return notes
            
        except Exception as e:
            logger.error(f"[UserStore] Error getting notes: {e}")
            return []
    
    def update_note(self, user_id: str, note_id: str, text: str, 
                    tags: Optional[List[str]] = None) -> bool:
        """Update an existing note."""
        try:
            update_data = {
                'text': text,
                'updated_at': datetime.now().isoformat()
            }
            if tags is not None:
                update_data['tags'] = tags
            
            self._store.collection('users').document(user_id) \
                .collection('notes').document(note_id).update(update_data)
            return True
            
        except Exception as e:
            logger.error(f"[UserStore] Error updating note: {e}")
            return False
    
    def delete_note(self, user_id: str, note_id: str) -> bool:
        """Delete a note."""
        try:
            self._store.collection('users').document(user_id) \
                .collection('notes').document(note_id).delete()
            return True
        except Exception as e:
            logger.error(f"[UserStore] Error deleting note: {e}")
            return False
    
    # =========================================================================
    # Aggregate Queries
    # =========================================================================
    
    def get_latest_evaluation(self, user_id: str) -> Optional[Evaluation]:
        """Get the most recent evaluation for a user."""
        evals = self.get_evaluations(user_id, limit=1)
        return evals[0] if evals else None
    
    def get_evaluation_count(self, user_id: str) -> int:
        """Get total number of evaluations for a user."""
        try:
            docs = self._store.collection('users').document(user_id) \
                .collection('evaluations').stream()
            return sum(1 for _ in docs)
        except Exception:
            return 0
    
    def compute_metrics(self, user_id: str) -> Dict[str, Any]:
        """
        Compute aggregate metrics for a user.
        
        Returns:
            Dict with average scores, trends, etc.
        """
        evals = self.get_evaluations(user_id, limit=100)
        
        if not evals:
            return {
                'total_evaluations': 0,
                'latest_scores': None,
                'trends': {}
            }
        
        # Latest scores
        latest = evals[0]
        
        # Average scores
        score_keys = ['stress_score', 'depression_score', 'anxiety_score', 'sleep_quality']
        averages = {}
        for key in score_keys:
            values = [e.scores.get(key, 0) for e in evals if e.scores.get(key) is not None]
            averages[key] = sum(values) / len(values) if values else 0
        
        # Simple trend (compare last 5 to previous 5)
        trends = {}
        if len(evals) >= 10:
            recent = evals[:5]
            previous = evals[5:10]
            
            for key in score_keys:
                recent_avg = sum(e.scores.get(key, 0) for e in recent) / 5
                previous_avg = sum(e.scores.get(key, 0) for e in previous) / 5
                diff = recent_avg - previous_avg
                
                if diff > 2:
                    trends[key] = 'increasing'
                elif diff < -2:
                    trends[key] = 'decreasing'
                else:
                    trends[key] = 'stable'
        
        return {
            'total_evaluations': len(evals),
            'latest_scores': latest.scores,
            'average_scores': averages,
            'trends': trends,
            'first_evaluation': evals[-1].timestamp if evals else None,
            'last_evaluation': latest.timestamp
        }


def get_user_store() -> UserStore:
    """Get the global UserStore instance."""
    global _user_store
    
    if _user_store is None:
        _user_store = UserStore()
    
    return _user_store


# ===========================================================================
# Standalone Helper Functions (for direct import)
# ===========================================================================

def save_evaluation(user_id: str, eval_id: str, data: Dict[str, Any]) -> str:
    """
    Save an evaluation to Firestore.
    
    Standalone function for direct use in prediction endpoints.
    
    Args:
        user_id: User's Firebase UID
        eval_id: Evaluation ID (or empty to generate)
        data: Evaluation data dict with keys:
            - inputs: Survey answers
            - scores: ML predictions
            - prediction: Primary prediction label
            - confidence: Prediction confidence
            - probabilities: All class probabilities
            - classifications: Score classifications
            - text_features: Free text input
            - intensity_values: Slider values
    
    Returns:
        Evaluation ID
    """
    store = get_user_store()
    
    evaluation = Evaluation(
        eval_id=eval_id or '',
        user_id=user_id,
        timestamp=data.get('timestamp', datetime.now().isoformat()),
        inputs=data.get('inputs', {}),
        scores=data.get('scores', {}),
        prediction=data.get('prediction'),
        confidence=data.get('confidence'),
        probabilities=data.get('probabilities'),
        classifications=data.get('classifications'),
        flags=data.get('flags', {}),
        text_features=data.get('text_features') or data.get('free_text'),
        intensity_values=data.get('intensity_values')
    )
    
    return store.save_evaluation(evaluation)


def get_evaluations(user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
    """
    Get evaluations for a user from Firestore.
    
    Standalone function for direct use.
    
    Args:
        user_id: User's Firebase UID
        limit: Maximum number of evaluations
    
    Returns:
        List of evaluation dicts
    """
    store = get_user_store()
    evaluations = store.get_evaluations(user_id, limit=limit)
    return [e.to_dict() for e in evaluations]


def get_latest_evaluation(user_id: str) -> Optional[Dict[str, Any]]:
    """
    Get the most recent evaluation for a user.
    
    Args:
        user_id: User's Firebase UID
    
    Returns:
        Evaluation dict or None
    """
    store = get_user_store()
    evaluation = store.get_latest_evaluation(user_id)
    return evaluation.to_dict() if evaluation else None

