# services/session_utils.py
"""
Session Management Utilities

Provides:
- Flask session helpers for authentication
- Auth decorators for protected routes
- User ID extraction from session/token
"""
from __future__ import annotations

import functools
import logging
from typing import Any, Callable, Dict, Optional, Tuple, Union

from flask import redirect, request, session, url_for, jsonify, g

from .firebase_client import verify_id_token, FIREBASE_AVAILABLE

logger = logging.getLogger(__name__)


def get_current_user_id() -> Optional[str]:
    """
    Get the current user ID from session or request headers.
    
    Checks in order:
    1. Flask session['user_id']
    2. Authorization header (Bearer token)
    3. X-User-ID header (for API calls)
    
    Returns:
        User ID string if authenticated, None otherwise.
    """
    # Check Flask session first
    if 'user_id' in session:
        return session['user_id']
    
    # Check Authorization header for Firebase ID token
    auth_header = request.headers.get('Authorization', '')
    if auth_header.startswith('Bearer '):
        token = auth_header[7:]
        claims = verify_id_token(token)
        if claims:
            return claims.get('uid')
    
    # Check X-User-ID header (for simple API calls)
    user_id = request.headers.get('X-User-ID')
    if user_id:
        return user_id
    
    return None


def get_current_user_email() -> Optional[str]:
    """Get the current user's email from session."""
    return session.get('user_email')


def get_user_claims() -> Dict[str, Any]:
    """
    Get all user claims from the current session.
    
    Returns:
        Dict with user claims (uid, email, etc.)
    """
    return {
        'uid': session.get('user_id'),
        'email': session.get('user_email'),
        'display_name': session.get('user_display_name'),
        'email_verified': session.get('email_verified', False),
        'is_authenticated': 'user_id' in session
    }


def create_session(
    user_id: str,
    email: str,
    display_name: Optional[str] = None,
    email_verified: bool = False,
    additional_data: Optional[Dict[str, Any]] = None
) -> None:
    """
    Create a Flask session for an authenticated user.
    
    Args:
        user_id: Firebase UID or other user identifier
        email: User's email address
        display_name: Optional display name
        email_verified: Whether email is verified
        additional_data: Any additional data to store in session
    """
    session['user_id'] = user_id
    session['user_email'] = email
    session['user_display_name'] = display_name
    session['email_verified'] = email_verified
    session['is_authenticated'] = True
    
    if additional_data:
        for key, value in additional_data.items():
            session[key] = value
    
    logger.info(f"[Session] Created session for user: {user_id}")


def clear_session() -> None:
    """Clear all session data (logout)."""
    user_id = session.get('user_id', 'unknown')
    session.clear()
    logger.info(f"[Session] Cleared session for user: {user_id}")


def require_auth(redirect_to: str = 'frontend.login'):
    """
    Decorator to require authentication for a route.
    
    For web routes, redirects to login page if not authenticated.
    For API routes (if Accept header contains 'application/json'),
    returns 401 JSON response.
    
    Args:
        redirect_to: Route name to redirect to if not authenticated
    
    Usage:
        @app.route('/protected')
        @require_auth()
        def protected_route():
            ...
    """
    def decorator(f: Callable) -> Callable:
        @functools.wraps(f)
        def decorated_function(*args, **kwargs):
            user_id = get_current_user_id()
            
            if not user_id:
                # Check if this is an API request
                if request.headers.get('Accept', '').startswith('application/json') or \
                   request.path.startswith('/api/'):
                    return jsonify({
                        'error': 'Authentication required',
                        'code': 'UNAUTHORIZED'
                    }), 401
                
                # Web request - redirect to login
                return redirect(url_for(redirect_to))
            
            # Store user_id in g for easy access in route
            g.user_id = user_id
            g.user_email = session.get('user_email')
            
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator


def require_auth_api():
    """
    Decorator specifically for API routes.
    Always returns JSON 401 if not authenticated.
    
    Usage:
        @api_bp.route('/protected')
        @require_auth_api()
        def protected_api():
            ...
    """
    def decorator(f: Callable) -> Callable:
        @functools.wraps(f)
        def decorated_function(*args, **kwargs):
            user_id = get_current_user_id()
            
            if not user_id:
                return jsonify({
                    'error': 'Authentication required',
                    'code': 'UNAUTHORIZED',
                    'message': 'Please login to access this resource'
                }), 401
            
            g.user_id = user_id
            g.user_email = session.get('user_email')
            
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator


def optional_auth():
    """
    Decorator that populates user info if available but doesn't require it.
    
    Usage:
        @app.route('/public-or-private')
        @optional_auth()
        def mixed_route():
            if g.user_id:
                # Authenticated user
            else:
                # Anonymous user
    """
    def decorator(f: Callable) -> Callable:
        @functools.wraps(f)
        def decorated_function(*args, **kwargs):
            user_id = get_current_user_id()
            g.user_id = user_id
            g.user_email = session.get('user_email') if user_id else None
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator


def validate_firebase_token(id_token: str) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
    """
    Validate a Firebase ID token and return user claims.
    
    Args:
        id_token: Firebase ID token from client
    
    Returns:
        Tuple of (success, claims_dict, error_message)
    """
    if not FIREBASE_AVAILABLE:
        # In development without Firebase, accept any token
        logger.warning("[Session] Firebase not available, using mock validation")
        return True, {
            'uid': 'mock_' + id_token[:8] if id_token else 'mock_user',
            'email': 'mock@example.com',
            'email_verified': True
        }, None
    
    claims = verify_id_token(id_token)
    
    if claims:
        return True, claims, None
    else:
        return False, None, "Invalid or expired token"


def is_authenticated() -> bool:
    """Check if current request is authenticated."""
    return get_current_user_id() is not None

