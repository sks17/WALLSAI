"""
Frontend blueprint for login, dashboard, survey, notes, and mindfulness flows.

Authentication:
- Firebase Auth with ID token validation
- Fallback: Mock auth for development without Firebase

Data Storage:
- Account-based persistence via Firestore
- New users start with empty history (all values at 0)
- No local file storage - data tied to user accounts

The dashboard integrates with /api/v2/* and /api/evaluations/* endpoints.
"""
from __future__ import annotations

import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from flask import (
    Blueprint,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

# Ensure project root is in path
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

logger = logging.getLogger(__name__)

# Try to import services
try:
    from services import get_user_store, is_authenticated, get_current_user_id
    from services.user_store import UserProfile, Evaluation
    SERVICES_AVAILABLE = True
except ImportError:
    SERVICES_AVAILABLE = False
    logger.warning("[Frontend] Services module not available")

# Try to import schema loader
try:
    from data import load_schema
except ImportError:
    def load_schema():
        return {"features": [f"question_{i}" for i in range(24)]}

frontend_bp = Blueprint("frontend", __name__)

# Note: Local file storage removed in favor of account-based Firestore persistence
# New users start with empty history (all values at 0)


def _require_user():
    """Redirect to login if user not in session."""
    if "user_email" not in session and "user_id" not in session:
        return redirect(url_for("frontend.login"))
    return None


def _get_user_id() -> str:
    """Get user ID from session (Firebase UID)."""
    # Firebase UID is the primary identifier
    if "user_id" in session:
        return session["user_id"]
    
    # Fallback to email-based ID (for compatibility)
    email = session.get("user_email", "anonymous")
    return email.replace("@", "_").replace(".", "_")


def _load_user_history(user_id: str) -> List[Dict]:
    """
    Load evaluation history for a user from Firestore.
    
    Account-based persistence: New users start with empty history.
    """
    # Try services module (Firestore)
    if SERVICES_AVAILABLE:
        try:
            store = get_user_store()
            evaluations = store.get_evaluations(user_id, limit=50)
            return [e.to_dict() for e in evaluations]
        except Exception as e:
            logger.warning(f"[Frontend] Firestore read failed: {e}")
    
    # Try backend module (Firestore)
    try:
        from backend.user_store import load_survey_history
        history = load_survey_history(user_id, limit=50)
        if history:
            return history
    except ImportError:
        pass
    except Exception as e:
        logger.warning(f"[Frontend] Backend read failed: {e}")
    
    # New user or no data - return empty list
    logger.debug(f"[Frontend] No history for user: {user_id} (new account)")
    return []


def _deprecated_load_local_history(user_id: str) -> List[Dict]:
    """
    Deprecated: Local file loading removed.
    
    This function is kept for reference but returns empty.
    All data is now stored in Firestore (account-based).
    """
    return []


def _load_local_file_history(user_id: str) -> List[Dict]:
    """
    Deprecated - local file storage is disabled.
    Always returns empty list; use Firestore instead.
    """
    return []



@frontend_bp.route("/login", methods=["GET", "POST"])
def login():
    """
    Handle login page and form submission.
    
    Primary: Firebase Auth (handled by frontend JS → /auth/login API)
    Fallback: Form POST for noscript/development
    """
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "").strip()
        
        if not email:
            flash("Email is required.", "error")
            return redirect(url_for("frontend.login"))

        # Mock auth for development/fallback
        # In production, login happens via Firebase JS SDK → /auth/login API
        user_id = f"mock_{email.replace('@', '_').replace('.', '_')}"
        
        session["user_email"] = email
        session["user_id"] = user_id
        session["last_login"] = datetime.now(timezone.utc).isoformat()
        session["is_authenticated"] = True
        
        # Create profile in Firestore if available
        if SERVICES_AVAILABLE:
            try:
                store = get_user_store()
                profile = UserProfile(
                    user_id=user_id,
                    email=email,
                    created_at=datetime.now().isoformat(),
                    last_login=datetime.now().isoformat()
                )
                store.create_profile(profile)
            except Exception as e:
                logger.warning(f"[Frontend] Could not create profile: {e}")
        
        flash("Logged in successfully.", "success")
        return redirect(url_for("frontend.dashboard"))

    # Already logged in? Redirect to dashboard
    if "user_email" in session or "user_id" in session:
        return redirect(url_for("frontend.dashboard"))
    
    return render_template("login.html")


@frontend_bp.route("/signup", methods=["GET", "POST"])
def signup():
    """
    Handle signup page.
    
    Primary: Firebase Auth (handled by frontend JS → /auth/login API)
    Fallback: Redirects to login for noscript
    """
    # Already logged in? Go to dashboard
    if "user_id" in session:
        return redirect(url_for("frontend.dashboard"))
    
    if request.method == "POST":
        # For noscript fallback, redirect to login
        # Real signup happens via Firebase JS SDK
        flash("Please enable JavaScript for account creation.", "info")
        return redirect(url_for("frontend.login"))
    
    return render_template("signup.html")


@frontend_bp.get("/logout")
def logout():
    """
    Log out the current user.
    
    Clears Flask session. Firebase signOut happens on client side.
    """
    user_id = session.get("user_id", "unknown")
    logger.info(f"[Frontend] User logged out: {user_id}")
    
    session.clear()
    flash("Logged out successfully.", "success")
    return redirect(url_for("frontend.login"))


@frontend_bp.get("/dashboard")
def dashboard():
    """Display user dashboard with history and visualizations."""
    # Require authentication
    if "user_id" not in session:
        return redirect(url_for("frontend.login"))
    
    email = session.get("user_email", "User")
    user_id = session.get("user_id")
    
    # Load history from Firestore/disk
    history = _load_user_history(user_id)
    
    return render_template(
        "dashboard.html",
        user_email=email,
        user_id=user_id,
        history=history,
    )


@frontend_bp.get("/survey")
def survey():
    """Display the survey form."""
    # Require authentication
    if "user_id" not in session:
        return redirect(url_for("frontend.login"))
    
    # Load schema for fallback/noscript form
    try:
        schema = load_schema()
        features = schema.get("features", [])
    except Exception:
        features = [f"question_{i}" for i in range(24)]
    
    return render_template("survey.html", features=features)


@frontend_bp.post("/survey-submit")
def survey_submit():
    """Handle legacy survey form submission (for noscript fallback)."""
    # Require authentication
    if "user_id" not in session:
        return redirect(url_for("frontend.login"))

    user_id = session.get("user_id")

    # Collect answers from form (for noscript fallback)
    answers = {}
    for i in range(24):
        value = request.form.get(f"q_{i}", "").strip()
        if value:
            answers[f"question_{i}"] = value

    if len(answers) < 20:  # Allow some flexibility
        flash("Please answer most questions.", "error")
        return redirect(url_for("frontend.survey"))

    # Try to run inference and save to Firestore
    try:
        from src.inference import run_inference
        scores = run_inference(answers, "")
        
        # Save to Firestore
        if SERVICES_AVAILABLE:
            from services import save_evaluation
            save_evaluation(user_id, "", {
                "inputs": answers,
                "scores": scores
            })
        
        flash(f"Analysis complete. Stress: {scores.get('stress_score', 0):.1f}", "success")
    except Exception as e:
        logger.warning(f"[Survey] Inference error: {e}")
        flash("Analysis complete (limited mode).", "info")

    return redirect(url_for("frontend.dashboard"))


# ---------------------------------------------------------------------------
# Notes & Reflections
# ---------------------------------------------------------------------------

@frontend_bp.get("/notes")
def notes():
    """Display the notes & reflections page."""
    # Require authentication
    if "user_id" not in session:
        return redirect(url_for("frontend.login"))
    
    return render_template(
        "notes.html",
        user_email=session.get("user_email"),
        user_id=session.get("user_id")
    )


# ---------------------------------------------------------------------------
# Mindfulness Resources
# ---------------------------------------------------------------------------

@frontend_bp.get("/mindfulness")
def mindfulness():
    """Display the mindfulness resources page."""
    # No login required for resources
    return render_template(
        "mindfulness.html",
        user_email=session.get("user_email")
    )


@frontend_bp.get("/learn/<topic_id>")
def learn_topic(topic_id: str):
    """Display a specific educational topic."""
    try:
        from src.resources.data import LEARN_TOPICS
        
        topic = next((t for t in LEARN_TOPICS if t["id"] == topic_id), None)
        
        if not topic:
            flash("Topic not found.", "error")
            return redirect(url_for("frontend.mindfulness"))
        
        # Convert markdown content to HTML (basic)
        import re
        content = topic["content"]
        
        # Convert headers
        content = re.sub(r'^### (.+)$', r'<h3>\1</h3>', content, flags=re.MULTILINE)
        content = re.sub(r'^## (.+)$', r'<h2>\1</h2>', content, flags=re.MULTILINE)
        
        # Convert bold
        content = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', content)
        
        # Convert lists
        content = re.sub(r'^- (.+)$', r'<li>\1</li>', content, flags=re.MULTILINE)
        content = re.sub(r'(<li>.+</li>\n)+', r'<ul>\g<0></ul>', content)
        
        # Convert numbered lists
        content = re.sub(r'^\d+\. (.+)$', r'<li>\1</li>', content, flags=re.MULTILINE)
        
        # Convert paragraphs
        content = re.sub(r'\n\n+', r'</p><p>', content)
        content = f"<p>{content}</p>"
        content = content.replace('<p></p>', '')
        content = content.replace('<p><h', '<h').replace('</h2></p>', '</h2>')
        content = content.replace('</h3></p>', '</h3>')
        content = content.replace('<p><ul>', '<ul>').replace('</ul></p>', '</ul>')
        
        topic_with_html = {**topic, "content": content}
        
        return render_template(
            "learn.html",
            topic=topic_with_html,
            user_email=session.get("user_email")
        )
        
    except Exception as e:
        flash(f"Error loading topic: {str(e)}", "error")
        return redirect(url_for("frontend.mindfulness"))


# ---------------------------------------------------------------------------
# Toolkit (Quick access to all features)
# ---------------------------------------------------------------------------

@frontend_bp.get("/toolkit")
def toolkit():
    """Display the WALLS toolkit page."""
    # Require authentication
    if "user_id" not in session:
        return redirect(url_for("frontend.login"))
    
    return render_template(
        "toolkit.html",
        user_email=session.get("user_email"),
        user_id=session.get("user_id")
    )


