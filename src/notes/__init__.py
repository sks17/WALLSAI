"""
WALLS Notes Module

Provides note-taking functionality for mental health reflections.
Uses a pluggable storage backend (JSON by default, Firestore-ready).
"""
from .storage import NoteStorage, get_storage
from .api import notes_bp

__all__ = ["NoteStorage", "get_storage", "notes_bp"]

