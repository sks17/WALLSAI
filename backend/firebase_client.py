# backend/firebase_client.py
"""
Firebase Admin SDK Client

Initializes Firebase Admin SDK using service account credentials
from environment variables. Provides Firestore database access.

Environment Variables:
    FIREBASE_SERVICE_ACCOUNT_JSON: Full JSON string of service account credentials
"""

import firebase_admin
from firebase_admin import credentials, firestore, auth
import os
import json
import logging

logger = logging.getLogger(__name__)

# Module-level database client
db = None
_initialized = False


def init_firebase():
    """
    Initialize Firebase Admin SDK.
    
    Loads credentials exclusively from FIREBASE_SERVICE_ACCOUNT_JSON.
    File-based loading is disabled for security and Vercel compatibility.
    Returns:
        firebase_admin.App: The initialized Firebase app
        
    Raises:
        RuntimeError: If no valid credentials are found
    """
    global db, _initialized
    
    # Return existing app if already initialized
    if firebase_admin._apps:
        logger.info("[Firebase] Already initialized, returning existing app")
        if db is None:
            db = firestore.client()
        _initialized = True
        return firebase_admin.get_app()
    
    service_account_json = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON")
    if not service_account_json:
        raise RuntimeError("Missing FIREBASE_SERVICE_ACCOUNT_JSON environment variable.")
    try:
        firebase_creds = json.loads(service_account_json)
        cred = credentials.Certificate(firebase_creds)
        logger.info("[Firebase] Using FIREBASE_SERVICE_ACCOUNT_JSON credentials")
    except (json.JSONDecodeError, ValueError) as e:
        raise RuntimeError(f"Invalid FIREBASE_SERVICE_ACCOUNT_JSON: {e}")
    
    # Initialize the app
    firebase_admin.initialize_app(cred)
    db = firestore.client()
    _initialized = True
    
    logger.info("[Firebase] Successfully initialized")
    return firebase_admin.get_app()


def get_db():
    """
    Get the Firestore database client.
    
    Initializes Firebase if not already done.
    
    Returns:
        google.cloud.firestore.Client: Firestore client
    """
    global db
    if db is None:
        init_firebase()
    return db


def verify_token(id_token: str) -> str | None:
    """
    Verify a Firebase ID token.
    
    Args:
        id_token: The ID token from the client
        
    Returns:
        User UID if valid, None otherwise
    """
    try:
        if not _initialized:
            init_firebase()
        decoded = auth.verify_id_token(id_token)
        return decoded.get("uid")
    except Exception as e:
        logger.warning(f"[Firebase] Token verification failed: {e}")
        return None


def get_user_info(id_token: str) -> dict | None:
    """
    Get full user info from ID token.
    
    Args:
        id_token: The ID token from the client
        
    Returns:
        Dict with uid, email, email_verified, name (if available)
    """
    try:
        if not _initialized:
            init_firebase()
        decoded = auth.verify_id_token(id_token)
        return {
            "uid": decoded.get("uid"),
            "email": decoded.get("email"),
            "email_verified": decoded.get("email_verified", False),
            "name": decoded.get("name"),
            "picture": decoded.get("picture")
        }
    except Exception as e:
        logger.warning(f"[Firebase] Failed to get user info: {e}")
        return None


# Auto-initialize on import (with graceful fallback)
try:
    init_firebase()
except RuntimeError as e:
    logger.warning(f"[Firebase] Auto-init failed (will retry on first use): {e}")
except Exception as e:
    logger.error(f"[Firebase] Unexpected error during init: {e}")

