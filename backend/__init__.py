# backend/__init__.py
"""
Backend module for Firebase integration and user data management.

This module provides:
- Firebase Admin SDK initialization
- Firestore database access
- User data persistence
- Survey history management
"""

from .firebase_client import init_firebase, get_db, db
from .user_store import (
    save_user_json,
    load_user_json,
    add_survey_entry,
    load_survey_history,
    delete_survey_entry,
    update_user_profile
)

__all__ = [
    'init_firebase',
    'get_db',
    'db',
    'save_user_json',
    'load_user_json',
    'add_survey_entry',
    'load_survey_history',
    'delete_survey_entry',
    'update_user_profile'
]

