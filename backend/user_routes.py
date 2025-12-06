# backend/user_routes.py
"""
User API Routes Blueprint

Provides REST API endpoints for user data management:
- POST /api/user/save - Save user profile
- GET /api/user/load/<uid> - Load user profile
- POST /api/user/save-survey - Save survey entry
- GET /api/user/history/<uid> - Get survey history
- GET /api/user/stats/<uid> - Get user statistics
- DELETE /api/user/survey/<uid>/<entry_id> - Delete survey entry
"""

import logging
from datetime import datetime, timezone
from flask import Blueprint, request, jsonify, session

from .firebase_client import verify_token, get_user_info
from .user_store import (
    save_user_json,
    load_user_json,
    add_survey_entry,
    load_survey_history,
    delete_survey_entry,
    get_user_stats,
    create_user_profile,
    update_user_profile
)

logger = logging.getLogger(__name__)

user_bp = Blueprint("user", __name__, url_prefix="/api/user")


def _get_uid_from_request() -> str | None:
    """
    Get user ID from request (JSON body, session, or header).
    
    Returns:
        User ID string or None
    """
    # Try JSON body
    if request.is_json:
        uid = request.json.get("uid")
        if uid:
            return uid
    
    # Try session
    uid = session.get("user_id")
    if uid:
        return uid
    
    # Try Authorization header (Bearer token)
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
        uid = verify_token(token)
        if uid:
            return uid
    
    return None


def _require_uid():
    """Get UID or return error response."""
    uid = _get_uid_from_request()
    if not uid:
        return None, (jsonify({"error": "Missing or invalid user ID"}), 401)
    return uid, None


# =============================================================================
# User Profile Endpoints
# =============================================================================

@user_bp.route("/save", methods=["POST"])
def api_user_save():
    """
    Save user profile data.
    
    Request JSON:
        {
            "uid": "user_id",
            "data": { ... profile data ... }
        }
    
    Response:
        { "status": "ok" }
    """
    try:
        data = request.get_json(force=True)
        uid = data.get("uid") or session.get("user_id")
        user_data = data.get("data", {})
        
        if not uid:
            return jsonify({"error": "Missing uid"}), 400
        
        success = save_user_json(uid, user_data)
        
        if success:
            return jsonify({"status": "ok"})
        else:
            return jsonify({"error": "Failed to save"}), 500
            
    except Exception as e:
        logger.error(f"[UserAPI] Save error: {e}")
        return jsonify({"error": str(e)}), 500


@user_bp.route("/load/<uid>", methods=["GET"])
def api_user_load(uid: str):
    """
    Load user profile data.
    
    Response:
        { "data": { ... profile data ... } }
    """
    try:
        data = load_user_json(uid)
        return jsonify({"data": data or {}})
        
    except Exception as e:
        logger.error(f"[UserAPI] Load error: {e}")
        return jsonify({"error": str(e)}), 500


@user_bp.route("/profile", methods=["GET"])
def api_get_profile():
    """Get current user's profile."""
    uid, error = _require_uid()
    if error:
        return error
    
    data = load_user_json(uid)
    return jsonify({"data": data or {}})


@user_bp.route("/profile", methods=["POST", "PUT"])
def api_update_profile():
    """Update current user's profile."""
    uid, error = _require_uid()
    if error:
        return error
    
    data = request.get_json(force=True)
    success = save_user_json(uid, data)
    
    return jsonify({"status": "ok" if success else "error"})


# =============================================================================
# Survey Endpoints
# =============================================================================

@user_bp.route("/save-survey", methods=["POST"])
def api_user_save_survey():
    """
    Save a survey entry.
    
    Request JSON:
        {
            "uid": "user_id",
            "entry": {
                "timestamp": "2025-01-01T00:00:00Z",
                "scores": { "stress": 5, "depression": 3, ... },
                "text": "free form response",
                "raw_responses": { "q1": "yes", ... }
            }
        }
    
    Response:
        { "status": "ok", "timestamp": "..." }
    """
    try:
        data = request.get_json(force=True)
        uid = data.get("uid") or session.get("user_id")
        entry = data.get("entry", {})
        
        if not uid:
            return jsonify({"error": "Missing uid"}), 400
        
        if not entry:
            return jsonify({"error": "Missing entry data"}), 400
        
        timestamp = add_survey_entry(uid, entry)
        
        return jsonify({
            "status": "ok",
            "timestamp": timestamp
        })
        
    except Exception as e:
        logger.error(f"[UserAPI] Save survey error: {e}")
        return jsonify({"error": str(e)}), 500


@user_bp.route("/history/<uid>", methods=["GET"])
def api_user_history(uid: str):
    """
    Get survey history for a user.
    
    Query params:
        limit: Maximum entries (default 50)
    
    Response:
        { "history": [ ... entries ... ] }
    """
    try:
        limit = request.args.get("limit", 50, type=int)
        history = load_survey_history(uid, limit=limit)
        
        return jsonify({"history": history})
        
    except Exception as e:
        logger.error(f"[UserAPI] History error: {e}")
        return jsonify({"error": str(e)}), 500


@user_bp.route("/history", methods=["GET"])
def api_current_user_history():
    """Get current user's survey history."""
    uid, error = _require_uid()
    if error:
        return error
    
    limit = request.args.get("limit", 50, type=int)
    history = load_survey_history(uid, limit=limit)
    
    return jsonify({"history": history})


@user_bp.route("/survey/<uid>/<entry_id>", methods=["DELETE"])
def api_delete_survey(uid: str, entry_id: str):
    """
    Delete a survey entry.
    
    Response:
        { "status": "ok" }
    """
    try:
        success = delete_survey_entry(uid, entry_id)
        
        if success:
            return jsonify({"status": "ok"})
        else:
            return jsonify({"error": "Failed to delete"}), 500
            
    except Exception as e:
        logger.error(f"[UserAPI] Delete survey error: {e}")
        return jsonify({"error": str(e)}), 500


# =============================================================================
# Statistics Endpoints
# =============================================================================

@user_bp.route("/stats/<uid>", methods=["GET"])
def api_user_stats(uid: str):
    """
    Get user statistics.
    
    Response:
        {
            "total_surveys": 10,
            "average_scores": { ... },
            "latest_scores": { ... },
            "first_survey": "...",
            "last_survey": "..."
        }
    """
    try:
        stats = get_user_stats(uid)
        return jsonify(stats)
        
    except Exception as e:
        logger.error(f"[UserAPI] Stats error: {e}")
        return jsonify({"error": str(e)}), 500


@user_bp.route("/stats", methods=["GET"])
def api_current_user_stats():
    """Get current user's statistics."""
    uid, error = _require_uid()
    if error:
        return error
    
    stats = get_user_stats(uid)
    return jsonify(stats)


# =============================================================================
# Auth Integration
# =============================================================================

@user_bp.route("/verify", methods=["POST"])
def api_verify_token():
    """
    Verify a Firebase ID token.
    
    Request JSON:
        { "idToken": "..." }
    
    Response:
        { "valid": true, "uid": "...", "user": { ... } }
    """
    try:
        data = request.get_json(force=True)
        id_token = data.get("idToken")
        
        if not id_token:
            return jsonify({"valid": False, "error": "Missing token"}), 400
        
        user_info = get_user_info(id_token)
        
        if user_info:
            return jsonify({
                "valid": True,
                "uid": user_info["uid"],
                "user": user_info
            })
        else:
            return jsonify({"valid": False, "error": "Invalid token"}), 401
            
    except Exception as e:
        logger.error(f"[UserAPI] Verify error: {e}")
        return jsonify({"valid": False, "error": str(e)}), 500


@user_bp.route("/init", methods=["POST"])
def api_init_user():
    """
    Initialize user profile after first login.
    
    Request JSON:
        { "uid": "...", "email": "...", "displayName": "..." }
    
    Response:
        { "status": "ok", "profile": { ... } }
    """
    try:
        data = request.get_json(force=True)
        uid = data.get("uid")
        email = data.get("email")
        display_name = data.get("displayName")
        
        if not uid or not email:
            return jsonify({"error": "Missing uid or email"}), 400
        
        # Check if user already exists
        existing = load_user_json(uid)
        if existing:
            # Update last login
            update_user_profile(uid, {
                "lastLogin": datetime.now(timezone.utc).isoformat()
            })
            return jsonify({"status": "ok", "profile": existing, "new": False})
        
        # Create new profile
        success = create_user_profile(uid, email, display_name)
        profile = load_user_json(uid) if success else None
        
        return jsonify({
            "status": "ok" if success else "error",
            "profile": profile,
            "new": True
        })
        
    except Exception as e:
        logger.error(f"[UserAPI] Init error: {e}")
        return jsonify({"error": str(e)}), 500

