"""
API package initializer.

Exposes the API blueprint for registration in the Flask app.
"""
from api.routes import api_bp

__all__ = ["api_bp"]


