"""
Notes API Module

Flask API endpoints for notes and reflections.

Endpoints:
- POST /api/notes/create - Create a new note
- GET /api/notes/list - List notes
- GET /api/notes/<id> - Get single note
- PUT /api/notes/<id> - Update note
- DELETE /api/notes/<id> - Delete note
- GET /api/notes/search - Search notes
- GET /api/notes/export - Export notes
- GET /api/notes/stats - Get note statistics
"""
from __future__ import annotations

import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from flask import Blueprint, jsonify, request, Response

# Ensure project root is in path
ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.notes.storage import get_storage, Note

logger = logging.getLogger("walls.notes.api")

# ---------------------------------------------------------------------------
# Blueprint
# ---------------------------------------------------------------------------

notes_bp = Blueprint("notes", __name__)


# ---------------------------------------------------------------------------
# Utility Functions
# ---------------------------------------------------------------------------

def get_user_id() -> str:
    """Get user ID from request (header or query param)."""
    user_id = request.headers.get("X-User-ID")
    if not user_id:
        user_id = request.args.get("user_id", "anonymous")
    return user_id


# ---------------------------------------------------------------------------
# API Endpoints
# ---------------------------------------------------------------------------

@notes_bp.route("/create", methods=["POST"])
def create_note():
    """
    Create a new note.
    
    Request Body:
    {
        "content": "My reflection...",
        "tags": ["stress", "sleep"],
        "title": "Optional title",
        "mood_score": 7
    }
    """
    user_id = get_user_id()
    payload = request.get_json(force=True, silent=True) or {}
    
    content = payload.get("content", "").strip()
    if not content:
        return jsonify({"error": "Content is required"}), 400
    
    tags = payload.get("tags", [])
    title = payload.get("title")
    mood_score = payload.get("mood_score")
    
    # Validate mood_score
    if mood_score is not None:
        try:
            mood_score = int(mood_score)
            if not 1 <= mood_score <= 10:
                mood_score = None
        except (TypeError, ValueError):
            mood_score = None
    
    storage = get_storage()
    note = storage.create(
        user_id=user_id,
        content=content,
        tags=tags,
        title=title,
        mood_score=mood_score
    )
    
    logger.info(f"Created note {note.id} for user {user_id}")
    
    return jsonify({
        "success": True,
        "note": note.to_dict()
    }), 201


@notes_bp.route("/list", methods=["GET"])
def list_notes():
    """
    List notes for the current user.
    
    Query Params:
    - tags: Comma-separated tags to filter by
    - limit: Max notes to return (default: 50)
    - offset: Pagination offset (default: 0)
    """
    user_id = get_user_id()
    
    tags_param = request.args.get("tags", "")
    tags = [t.strip() for t in tags_param.split(",") if t.strip()] if tags_param else None
    
    limit = request.args.get("limit", 50, type=int)
    offset = request.args.get("offset", 0, type=int)
    
    storage = get_storage()
    notes = storage.list(user_id, tags=tags, limit=limit, offset=offset)
    
    return jsonify({
        "notes": [n.to_dict() for n in notes],
        "total": len(notes),
        "limit": limit,
        "offset": offset
    }), 200


@notes_bp.route("/<note_id>", methods=["GET"])
def get_note(note_id: str):
    """Get a single note."""
    user_id = get_user_id()
    
    storage = get_storage()
    note = storage.get(user_id, note_id)
    
    if not note:
        return jsonify({"error": "Note not found"}), 404
    
    return jsonify({"note": note.to_dict()}), 200


@notes_bp.route("/<note_id>", methods=["PUT"])
def update_note(note_id: str):
    """
    Update an existing note.
    
    Request Body (all fields optional):
    {
        "content": "Updated content...",
        "tags": ["new", "tags"],
        "title": "New title",
        "mood_score": 8,
        "is_pinned": true
    }
    """
    user_id = get_user_id()
    payload = request.get_json(force=True, silent=True) or {}
    
    storage = get_storage()
    note = storage.update(
        user_id=user_id,
        note_id=note_id,
        content=payload.get("content"),
        tags=payload.get("tags"),
        title=payload.get("title"),
        mood_score=payload.get("mood_score"),
        is_pinned=payload.get("is_pinned")
    )
    
    if not note:
        return jsonify({"error": "Note not found"}), 404
    
    logger.info(f"Updated note {note_id} for user {user_id}")
    
    return jsonify({
        "success": True,
        "note": note.to_dict()
    }), 200


@notes_bp.route("/<note_id>", methods=["DELETE"])
def delete_note(note_id: str):
    """Delete a note."""
    user_id = get_user_id()
    
    storage = get_storage()
    deleted = storage.delete(user_id, note_id)
    
    if not deleted:
        return jsonify({"error": "Note not found"}), 404
    
    logger.info(f"Deleted note {note_id} for user {user_id}")
    
    return jsonify({"success": True}), 200


@notes_bp.route("/search", methods=["GET"])
def search_notes():
    """
    Search notes by content.
    
    Query Params:
    - q: Search query (required)
    """
    user_id = get_user_id()
    query = request.args.get("q", "").strip()
    
    if not query:
        return jsonify({"error": "Search query is required"}), 400
    
    storage = get_storage()
    results = storage.search(user_id, query)
    
    return jsonify({
        "query": query,
        "results": [n.to_dict() for n in results],
        "total": len(results)
    }), 200


@notes_bp.route("/export", methods=["GET"])
def export_notes():
    """
    Export all notes.
    
    Query Params:
    - format: "json", "markdown", or "text" (default: "json")
    """
    user_id = get_user_id()
    format = request.args.get("format", "json")
    
    if format not in ["json", "markdown", "text"]:
        return jsonify({"error": "Invalid format. Use: json, markdown, text"}), 400
    
    storage = get_storage()
    export_data = storage.export(user_id, format)
    
    # Set appropriate content type and filename
    if format == "json":
        mimetype = "application/json"
        filename = "notes_export.json"
    elif format == "markdown":
        mimetype = "text/markdown"
        filename = "notes_export.md"
    else:
        mimetype = "text/plain"
        filename = "notes_export.txt"
    
    return Response(
        export_data,
        mimetype=mimetype,
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@notes_bp.route("/stats", methods=["GET"])
def get_stats():
    """Get statistics about user's notes."""
    user_id = get_user_id()
    
    storage = get_storage()
    stats = storage.get_stats(user_id)
    
    return jsonify(stats), 200


# ---------------------------------------------------------------------------
# Available Tags
# ---------------------------------------------------------------------------

AVAILABLE_TAGS = [
    {"id": "stress", "label": "Stress", "color": "#ff6b6b"},
    {"id": "anxiety", "label": "Anxiety", "color": "#00d4aa"},
    {"id": "depression", "label": "Depression", "color": "#8b5cf6"},
    {"id": "sleep", "label": "Sleep", "color": "#3b82f6"},
    {"id": "goals", "label": "Goals", "color": "#fbbf24"},
    {"id": "gratitude", "label": "Gratitude", "color": "#10b981"},
    {"id": "exercise", "label": "Exercise", "color": "#f97316"},
    {"id": "therapy", "label": "Therapy", "color": "#ec4899"},
    {"id": "medication", "label": "Medication", "color": "#6366f1"},
    {"id": "positive", "label": "Positive", "color": "#22c55e"},
]


@notes_bp.route("/tags", methods=["GET"])
def get_available_tags():
    """Get list of available tags."""
    return jsonify({"tags": AVAILABLE_TAGS}), 200

