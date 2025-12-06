# services/__init__.py
"""
WALLS Services Module

Provides abstraction layers for:
- Firebase Admin SDK integration
- Firestore user data persistence
- Session management utilities
- Authentication routes
- Evaluations API
"""

from .firebase_client import (
    init_firebase,
    get_firestore_client,
    verify_id_token,
    FirebaseConfig,
    FIREBASE_AVAILABLE
)

from .user_store import (
    UserStore,
    get_user_store,
    UserProfile,
    Evaluation,
    Note,
    # Standalone helper functions
    save_evaluation,
    get_evaluations,
    get_latest_evaluation
)

from .session_utils import (
    require_auth,
    require_auth_api,
    get_current_user_id,
    create_session,
    clear_session,
    is_authenticated
)

from .auth_routes import auth_bp
from .evaluations_api import evaluations_bp, save_prediction_to_firestore

__all__ = [
    # Firebase
    'init_firebase',
    'get_firestore_client', 
    'verify_id_token',
    'FirebaseConfig',
    'FIREBASE_AVAILABLE',
    
    # User Store
    'UserStore',
    'get_user_store',
    'UserProfile',
    'Evaluation',
    'Note',
    'save_evaluation',
    'get_evaluations',
    'get_latest_evaluation',
    
    # Session
    'require_auth',
    'require_auth_api',
    'get_current_user_id',
    'create_session',
    'clear_session',
    'is_authenticated',
    
    # Blueprints
    'auth_bp',
    'evaluations_bp',
    
    # Helpers
    'save_prediction_to_firestore'
]

