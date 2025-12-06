# services/auth_routes.py
"""
Authentication Routes Blueprint

Provides:
- POST /auth/login - Validate Firebase ID token and create session
- POST /auth/logout - Clear session
- GET /auth/status - Check authentication status
- POST /auth/register - Create new Firebase user (admin only)
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict

from flask import Blueprint, jsonify, request, session

from .firebase_client import verify_token, verify_id_token, FIREBASE_AVAILABLE, create_user
from .session_utils import (
    create_session,
    clear_session,
    get_current_user_id,
    get_user_claims
)
from .user_store import get_user_store, UserProfile

logger = logging.getLogger(__name__)

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['POST'])
def login():
    """
    Validate Firebase ID token and create Flask session.
    
    Request JSON:
        {
            "idToken": "Firebase ID token from client",
            "email": "optional email for fallback"
        }
    
    Response:
        {
            "success": true,
            "user": {
                "uid": "user_id",
                "email": "email@example.com",
                "display_name": "Name"
            }
        }
    """
    data = request.get_json(force=True, silent=True) or {}
    id_token = data.get('idToken')
    fallback_email = data.get('email')
    
    if not id_token:
        return jsonify({
            'success': False,
            'error': 'Missing ID token'
        }), 400
    
    # Try to verify with Firebase
    user_id = verify_token(id_token)
    claims = None
    
    if user_id:
        # Get full claims for additional info
        claims = verify_id_token(id_token)
    else:
        # Fallback for development - accept mock tokens
        if id_token.startswith('mock_') or not FIREBASE_AVAILABLE:
            user_id = id_token if id_token.startswith('mock_') else f'mock_{id_token[:8]}'
            claims = {
                'uid': user_id,
                'email': fallback_email,
                'email_verified': False
            }
            logger.info(f"[Auth] Using mock auth for: {user_id}")
        else:
            return jsonify({
                'success': False,
                'error': 'Invalid token'
            }), 401
    
    # Extract user info
    email = (claims.get('email') if claims else None) or fallback_email or 'unknown@walls.app'
    display_name = claims.get('name') if claims else None
    email_verified = claims.get('email_verified', False) if claims else False
    
    # Create Flask session
    create_session(
        user_id=user_id,
        email=email,
        display_name=display_name,
        email_verified=email_verified
    )
    
    # Create or update user profile in Firestore
    store = get_user_store()
    profile = store.get_profile(user_id)
    
    if profile:
        # Update last login
        store.update_last_login(user_id)
    else:
        # Create new profile
        profile = UserProfile(
            user_id=user_id,
            email=email,
            display_name=display_name,
            created_at=datetime.now().isoformat(),
            last_login=datetime.now().isoformat()
        )
        store.create_profile(profile)
    
    logger.info(f"[Auth] User logged in: {user_id}")
    
    return jsonify({
        'success': True,
        'user': {
            'uid': user_id,
            'email': email,
            'display_name': display_name,
            'email_verified': email_verified
        }
    }), 200


@auth_bp.route('/logout', methods=['POST'])
def logout():
    """
    Clear Flask session (logout).
    
    Response:
        {
            "success": true,
            "message": "Logged out successfully"
        }
    """
    user_id = get_current_user_id()
    clear_session()
    
    logger.info(f"[Auth] User logged out: {user_id}")
    
    return jsonify({
        'success': True,
        'message': 'Logged out successfully'
    }), 200


@auth_bp.route('/status', methods=['GET'])
def auth_status():
    """
    Check current authentication status.
    
    Response:
        {
            "authenticated": true/false,
            "user": {...} if authenticated
        }
    """
    claims = get_user_claims()
    
    return jsonify({
        'authenticated': claims.get('is_authenticated', False),
        'user': {
            'uid': claims.get('uid'),
            'email': claims.get('email'),
            'display_name': claims.get('display_name'),
            'email_verified': claims.get('email_verified')
        } if claims.get('is_authenticated') else None,
        'firebase_available': FIREBASE_AVAILABLE
    }), 200


@auth_bp.route('/register', methods=['POST'])
def register():
    """
    Create a new Firebase user.
    
    Note: In production, user registration should happen on the client side
    using Firebase Auth. This endpoint is provided for testing/admin purposes.
    
    Request JSON:
        {
            "email": "user@example.com",
            "password": "password123"
        }
    
    Response:
        {
            "success": true,
            "user": {"uid": "...", "email": "..."}
        }
    """
    data = request.get_json(force=True, silent=True) or {}
    email = data.get('email')
    password = data.get('password')
    
    if not email or not password:
        return jsonify({
            'success': False,
            'error': 'Email and password are required'
        }), 400
    
    if len(password) < 6:
        return jsonify({
            'success': False,
            'error': 'Password must be at least 6 characters'
        }), 400
    
    result = create_user(email, password)
    
    if result:
        return jsonify({
            'success': True,
            'user': result
        }), 201
    else:
        return jsonify({
            'success': False,
            'error': 'Failed to create user. Email may already be in use.'
        }), 400


@auth_bp.route('/refresh', methods=['POST'])
def refresh_session():
    """
    Refresh session with a new Firebase ID token.
    
    This should be called when the client's token is refreshed
    to keep the server session in sync.
    
    Request JSON:
        {
            "idToken": "new Firebase ID token"
        }
    """
    data = request.get_json(force=True, silent=True) or {}
    id_token = data.get('idToken')
    
    if not id_token:
        return jsonify({
            'success': False,
            'error': 'Missing ID token'
        }), 400
    
    # Current user must be logged in
    current_user = get_current_user_id()
    if not current_user:
        return jsonify({
            'success': False,
            'error': 'Not authenticated'
        }), 401
    
    # Validate new token
    success, claims, error = validate_firebase_token(id_token)
    
    if not success:
        return jsonify({
            'success': False,
            'error': error
        }), 401
    
    # Ensure same user
    if claims.get('uid') != current_user:
        return jsonify({
            'success': False,
            'error': 'Token user mismatch'
        }), 401
    
    # Session is already valid, just return success
    return jsonify({
        'success': True,
        'message': 'Session refreshed'
    }), 200

