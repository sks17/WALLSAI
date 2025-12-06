"""
Application entrypoint.

Creates the Flask app, registers API and legacy blueprints, and runs the server.

Authentication:
- /auth/login     - POST - Validate Firebase ID token
- /auth/logout    - POST - Clear session
- /auth/status    - GET  - Check authentication status
- /auth/register  - POST - Create new user (admin)

API Endpoints:
- /api/v2/predict     - POST - Run inference on user input
- /api/v2/history     - GET  - Get evaluation history
- /api/v2/metrics     - GET  - Get computed metrics and trends
- /api/v2/status      - GET  - Check API and model status
- /api/v2/thresholds  - GET  - Get clinical thresholds

KERNEL API Endpoints (Enhanced):
- /api/kernel/predict   - POST - Run KERNEL inference with uncertainty
- /api/kernel/schema    - GET  - Get assessment schema
- /api/kernel/status    - GET  - Check KERNEL model status
- /api/kernel/history   - GET  - Get KERNEL evaluation history
- /api/kernel/thresholds - GET - Get clinical thresholds

Notes API Endpoints:
- /api/notes/create   - POST - Create a new note
- /api/notes/list     - GET  - List notes
- /api/notes/<id>     - GET/PUT/DELETE - CRUD for single note
- /api/notes/search   - GET  - Search notes
- /api/notes/export   - GET  - Export notes
- /api/notes/tags     - GET  - Get available tags

Resources API Endpoints:
- /api/resources/mindfulness - GET - Get mindfulness resources
- /api/resources/breathing   - GET - Get breathing exercises
- /api/resources/learn       - GET - Get educational topics
- /api/resources/tips        - GET - Get quick tips
- /api/resources/search/therapist - GET - Search for therapists

Legacy endpoints are preserved at /api/* for backward compatibility.
"""
from __future__ import annotations

import logging
import os

from flask import Flask
from flask_cors import CORS

# Configure logging early
logging.basicConfig(
    level=logging.DEBUG if os.environ.get('FLASK_DEBUG') else logging.INFO,
    format='%(asctime)s | %(name)s | %(levelname)s | %(message)s'
)
logger = logging.getLogger(__name__)

# Import blueprints
from api import api_bp
from frontend import frontend_bp
from legacy.web import legacy_bp
from src.api import api_v2_bp

# Import Firebase services
try:
    from services import init_firebase, FIREBASE_AVAILABLE, auth_bp, evaluations_bp
    SERVICES_AVAILABLE = True
except ImportError as e:
    logger.warning(f"[Services] Services module not available: {e}")
    SERVICES_AVAILABLE = False
    auth_bp = None
    evaluations_bp = None

# Import KERNEL API (optional - graceful fallback if not available)
try:
    from src.kernel.api import kernel_bp
    KERNEL_AVAILABLE = True
except ImportError as e:
    logger.warning(f"[KERNEL] KERNEL module not available: {e}")
    KERNEL_AVAILABLE = False
    kernel_bp = None

# Import Notes API
try:
    from src.notes.api import notes_bp
    NOTES_AVAILABLE = True
except ImportError as e:
    logger.warning(f"[Notes] Notes module not available: {e}")
    NOTES_AVAILABLE = False
    notes_bp = None

# Import Resources API
try:
    from src.resources.api import resources_bp
    RESOURCES_AVAILABLE = True
except ImportError as e:
    logger.warning(f"[Resources] Resources module not available: {e}")
    RESOURCES_AVAILABLE = False
    resources_bp = None

# Import Backend User API (Firebase + Firestore)
try:
    from backend.user_routes import user_bp
    BACKEND_USER_AVAILABLE = True
except ImportError as e:
    logger.warning(f"[Backend] Backend user module not available: {e}")
    BACKEND_USER_AVAILABLE = False
    user_bp = None


def create_app() -> Flask:
    """
    Build the Flask application and attach blueprints.

    Returns
    -------
    Flask
        Configured Flask application.
    """
    app = Flask(__name__, static_folder="Static", template_folder="templates")
    
    # Configuration
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY") or "dev-secret-key-change-in-production"
    app.config["SESSION_COOKIE_SECURE"] = os.environ.get("FLASK_ENV") == "production"
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    
    # Enable CORS for API access from frontend
    CORS(app, resources={
        r"/api/*": {"origins": "*"},
        r"/auth/*": {"origins": "*"},
    }, supports_credentials=True)
    
    # Inject Firebase environment variables into all templates
    @app.context_processor
    def inject_firebase_config():
        return {
            "FIREBASE_API_KEY": os.environ.get("FIREBASE_API_KEY", ""),
            "FIREBASE_AUTH_DOMAIN": os.environ.get("FIREBASE_AUTH_DOMAIN", ""),
            "FIREBASE_PROJECT_ID": os.environ.get("FIREBASE_PROJECT_ID", ""),
            "FIREBASE_APP_ID": os.environ.get("FIREBASE_APP_ID", ""),
            "FIREBASE_STORAGE_BUCKET": os.environ.get("FIREBASE_STORAGE_BUCKET", ""),
            "FIREBASE_MESSAGING_SENDER_ID": os.environ.get("FIREBASE_MESSAGING_SENDER_ID", ""),
        }
    
    # Initialize Firebase
    if SERVICES_AVAILABLE:
        firebase_initialized = init_firebase()
        if firebase_initialized:
            logger.info("[Firebase] Successfully initialized")
        else:
            logger.warning("[Firebase] Using fallback storage (no Firebase credentials)")
    
    # Register blueprints
    app.register_blueprint(frontend_bp)
    app.register_blueprint(api_bp, url_prefix="/api")          # Legacy API
    app.register_blueprint(api_v2_bp, url_prefix="/api/v2")    # New API
    app.register_blueprint(legacy_bp)
    
    # Register Auth routes
    if SERVICES_AVAILABLE and auth_bp:
        app.register_blueprint(auth_bp, url_prefix="/auth")
        logger.info("[Auth] Authentication routes registered at /auth")
    
    # Register Evaluations API
    if SERVICES_AVAILABLE and evaluations_bp:
        app.register_blueprint(evaluations_bp, url_prefix="/api/evaluations")
        logger.info("[Evaluations] Evaluations API registered at /api/evaluations")
    
    # Register KERNEL API if available
    if KERNEL_AVAILABLE and kernel_bp:
        app.register_blueprint(kernel_bp, url_prefix="/api/kernel")
        logger.info("[KERNEL] Enhanced AI API registered at /api/kernel")
    
    # Register Notes API if available
    if NOTES_AVAILABLE and notes_bp:
        app.register_blueprint(notes_bp, url_prefix="/api/notes")
        logger.info("[Notes] Notes API registered at /api/notes")
    
    # Register Resources API if available
    if RESOURCES_AVAILABLE and resources_bp:
        app.register_blueprint(resources_bp, url_prefix="/api/resources")
        logger.info("[Resources] Resources API registered at /api/resources")
    
    # Register Backend User API if available
    if BACKEND_USER_AVAILABLE and user_bp:
        app.register_blueprint(user_bp)
        logger.info("[Backend] User API registered at /api/user")

    # Health endpoint for monitoring
    @app.get("/api/health")
    def health():
        return {"status": "ok"}
    
    # Log startup info
    logger.info("=" * 60)
    logger.info("WALLS Mental Health Application")
    logger.info("=" * 60)
    logger.info(f"Firebase Available: {FIREBASE_AVAILABLE if SERVICES_AVAILABLE else 'N/A'}")
    logger.info(f"KERNEL Available: {KERNEL_AVAILABLE}")
    logger.info(f"Notes Available: {NOTES_AVAILABLE}")
    logger.info(f"Resources Available: {RESOURCES_AVAILABLE}")
    logger.info(f"User API Available: {BACKEND_USER_AVAILABLE}")
    logger.info("=" * 60)
    
    return app


app = create_app()


if __name__ != "vercel":
    if __name__ == "__main__":
        debug = os.environ.get('FLASK_DEBUG', 'true').lower() == 'true'
        port = int(os.environ.get('PORT', 5000))
        app.run(debug=debug, host='0.0.0.0', port=port)
