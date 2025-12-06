# services/firebase_client.py
"""
Firebase Admin SDK Wrapper

Provides:
- Firebase Admin SDK initialization
- Firestore client access
- ID token verification for authentication

Configuration:
- FIREBASE_SERVICE_ACCOUNT_JSON (full JSON string)
  File-based loading is disabled for security/Vercel compatibility.
"""
from __future__ import annotations

import json
import logging
import os
from typing import Any, Optional, Tuple

logger = logging.getLogger(__name__)

# Track Firebase availability
FIREBASE_AVAILABLE = False
_firestore_client = None
_firebase_auth = None

def init_firebase(config: Optional[Any] = None) -> Tuple[Any, Any]:
    """
    Initialize Firebase Admin SDK.
    
    Args:
        config: Unused; kept for backward compatibility.
    
    Returns:
        Tuple of (firestore_client, auth_module) or (None, None) if failed.
    """
    global FIREBASE_AVAILABLE, _firestore_client, _firebase_auth
    
    try:
        import firebase_admin
        from firebase_admin import credentials, firestore, auth
    except ImportError:
        logger.warning("[Firebase] firebase-admin package not installed. Using fallback storage.")
        FIREBASE_AVAILABLE = False
        return None, None
    
    # Avoid reinitialization
    if firebase_admin._apps:
        logger.info("[Firebase] Already initialized")
        _firestore_client = firestore.client()
        _firebase_auth = auth
        FIREBASE_AVAILABLE = True
        return _firestore_client, _firebase_auth
    
    # Load credentials strictly from FIREBASE_SERVICE_ACCOUNT_JSON
    service_account_json = os.environ.get("FIREBASE_SERVICE_ACCOUNT_JSON")
    if not service_account_json:
        logger.error("[Firebase] Missing FIREBASE_SERVICE_ACCOUNT_JSON")
        FIREBASE_AVAILABLE = False
        return None, None
    try:
        firebase_creds = json.loads(service_account_json)
        cred = credentials.Certificate(firebase_creds)
        logger.info("[Firebase] Using FIREBASE_SERVICE_ACCOUNT_JSON credentials")
    except (json.JSONDecodeError, ValueError) as e:
        logger.error(f"[Firebase] Invalid FIREBASE_SERVICE_ACCOUNT_JSON: {e}")
        FIREBASE_AVAILABLE = False
        return None, None
    
    try:
        firebase_admin.initialize_app(cred)
        _firestore_client = firestore.client()
        _firebase_auth = auth
        
        FIREBASE_AVAILABLE = True
        logger.info("[Firebase] Initialization successful")
        return _firestore_client, _firebase_auth
        
    except Exception as e:
        logger.error(f"[Firebase] Initialization failed: {e}")
        FIREBASE_AVAILABLE = False
        return None, None


def get_firestore_client():
    """
    Get Firestore client instance.
    
    Returns:
        Firestore client or None if not initialized.
    """
    global _firestore_client
    
    if _firestore_client is None and not FIREBASE_AVAILABLE:
        # Try to initialize
        db, _ = init_firebase()
        return db
    
    return _firestore_client


def get_firebase_auth():
    """
    Get Firebase Auth module.
    
    Returns:
        Firebase auth module or None if not initialized.
    """
    global _firebase_auth
    
    if _firebase_auth is None and not FIREBASE_AVAILABLE:
        _, auth = init_firebase()
        return auth
    
    return _firebase_auth


def verify_token(id_token: str) -> Optional[str]:
    """
    Verify a Firebase ID token and return the user ID.
    
    Args:
        id_token: The Firebase ID token from the client.
    
    Returns:
        User UID if valid, None otherwise.
    """
    firebase_auth = get_firebase_auth()
    
    if firebase_auth is None:
        logger.warning("[Firebase] Cannot verify token - Firebase not available")
        return None
    
    try:
        decoded = firebase_auth.verify_id_token(id_token)
        uid = decoded.get("uid")
        logger.info(f"[Firebase] Token verified for user: {uid}")
        return uid
    except Exception as e:
        logger.warning(f"[Firebase] Token verification failed: {e}")
        return None


def verify_id_token(id_token: str) -> Optional[Dict[str, Any]]:
    """
    Verify a Firebase ID token and return full claims.
    
    Args:
        id_token: The Firebase ID token from the client.
    
    Returns:
        Decoded token claims if valid, None otherwise.
        
    Claims include:
        - uid: User's Firebase UID
        - email: User's email (if available)
        - email_verified: Whether email is verified
        - name: User's display name (if available)
    """
    firebase_auth = get_firebase_auth()
    
    if firebase_auth is None:
        logger.warning("[Firebase] Cannot verify token - Firebase not available")
        return None
    
    try:
        decoded_token = firebase_auth.verify_id_token(id_token)
        logger.info(f"[Firebase] Token verified for user: {decoded_token.get('uid')}")
        return decoded_token
    except Exception as e:
        logger.warning(f"[Firebase] Token verification failed: {e}")
        return None


def create_user(email: str, password: str) -> Optional[Dict[str, Any]]:
    """
    Create a new Firebase user.
    
    Args:
        email: User's email address
        password: User's password
    
    Returns:
        User record dict if successful, None otherwise.
    """
    if not FIREBASE_AVAILABLE:
        return None
    
    try:
        from firebase_admin import auth
        
        user = auth.create_user(
            email=email,
            password=password,
            email_verified=False
        )
        
        logger.info(f"[Firebase] Created user: {user.uid}")
        return {
            'uid': user.uid,
            'email': user.email,
            'created': True
        }
        
    except Exception as e:
        logger.error(f"[Firebase] User creation failed: {e}")
        return None


def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    """
    Get a Firebase user by email.
    
    Args:
        email: User's email address
    
    Returns:
        User record dict if found, None otherwise.
    """
    if not FIREBASE_AVAILABLE:
        return None
    
    try:
        from firebase_admin import auth
        
        user = auth.get_user_by_email(email)
        return {
            'uid': user.uid,
            'email': user.email,
            'email_verified': user.email_verified,
            'display_name': user.display_name
        }
        
    except Exception as e:
        logger.debug(f"[Firebase] User not found: {email}")
        return None


# Fallback in-memory store for when Firebase is unavailable
class FallbackStore:
    """
    In-memory fallback when Firebase is unavailable.
    
    Note: This store does NOT persist data across sessions.
    New users/sessions will start with empty data (all values at 0).
    This is the intended behavior for account-based persistence.
    """
    
    def __init__(self):
        self._data: Dict[str, Dict] = {}
        logger.warning("[FallbackStore] Using in-memory storage - data will NOT persist")
    
    def collection(self, name: str):
        """Mimic Firestore collection interface."""
        return FallbackCollection(self._data, name)


class FallbackCollection:
    """Mimics Firestore collection for fallback."""
    
    def __init__(self, data: Dict, name: str):
        self._data = data
        self._name = name
        if name not in self._data:
            self._data[name] = {}
    
    def document(self, doc_id: str):
        return FallbackDocument(self._data[self._name], doc_id)
    
    def add(self, data: Dict):
        import uuid
        doc_id = str(uuid.uuid4())[:8]
        self._data[self._name][doc_id] = data
        return (None, FallbackDocument(self._data[self._name], doc_id))
    
    def where(self, field: str, op: str, value: Any):
        return FallbackQuery(self._data[self._name], field, op, value)
    
    def order_by(self, field: str, direction: str = 'ASCENDING'):
        return FallbackQuery(self._data[self._name], None, None, None)
    
    def limit(self, count: int):
        return FallbackQuery(self._data[self._name], None, None, None, limit=count)
    
    def stream(self):
        for doc_id, data in self._data[self._name].items():
            yield FallbackDocSnapshot(doc_id, data)


class FallbackDocument:
    """Mimics Firestore document for fallback."""
    
    def __init__(self, collection_data: Dict, doc_id: str):
        self._collection = collection_data
        self._id = doc_id
    
    @property
    def id(self):
        return self._id
    
    def get(self):
        data = self._collection.get(self._id)
        return FallbackDocSnapshot(self._id, data) if data else FallbackDocSnapshot(self._id, None)
    
    def set(self, data: Dict, merge: bool = False):
        if merge and self._id in self._collection:
            self._collection[self._id].update(data)
        else:
            self._collection[self._id] = data
    
    def update(self, data: Dict):
        if self._id in self._collection:
            self._collection[self._id].update(data)
    
    def delete(self):
        if self._id in self._collection:
            del self._collection[self._id]
    
    def collection(self, name: str):
        # Subcollection support
        if self._id not in self._collection:
            self._collection[self._id] = {}
        if '_subcollections' not in self._collection[self._id]:
            self._collection[self._id]['_subcollections'] = {}
        if name not in self._collection[self._id]['_subcollections']:
            self._collection[self._id]['_subcollections'][name] = {}
        return FallbackCollection(
            {name: self._collection[self._id]['_subcollections'][name]},
            name
        )


class FallbackDocSnapshot:
    """Mimics Firestore document snapshot."""
    
    def __init__(self, doc_id: str, data: Optional[Dict]):
        self._id = doc_id
        self._data = data
    
    @property
    def id(self):
        return self._id
    
    @property
    def exists(self):
        return self._data is not None
    
    def to_dict(self):
        return self._data if self._data else {}


class FallbackQuery:
    """Mimics Firestore query for fallback."""
    
    def __init__(self, data: Dict, field: Optional[str], op: Optional[str], 
                 value: Any, limit: Optional[int] = None):
        self._data = data
        self._field = field
        self._op = op
        self._value = value
        self._limit = limit
    
    def stream(self):
        results = []
        for doc_id, data in self._data.items():
            if self._field and self._op == '==':
                if data.get(self._field) == self._value:
                    results.append(FallbackDocSnapshot(doc_id, data))
            else:
                results.append(FallbackDocSnapshot(doc_id, data))
        
        if self._limit:
            results = results[:self._limit]
        
        return iter(results)
    
    def limit(self, count: int):
        self._limit = count
        return self
    
    def order_by(self, field: str, direction: str = 'ASCENDING'):
        return self


# Global fallback store instance
_fallback_store = None


def get_store():
    """
    Get storage client.

    Returns:
        Firestore client, or None if not available.
    """
    global _fallback_store
    
    client = get_firestore_client()
    if client:
        return client
    
    # Disable in-memory persistence for security/compliance
    logger.error("[Firebase] Firestore client not available and fallback storage is disabled.")
    return None

