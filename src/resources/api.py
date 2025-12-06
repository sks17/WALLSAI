"""
Resources API Module

Flask API endpoints for mindfulness resources and external search.

Endpoints:
- GET /api/resources/mindfulness - Get curated mindfulness resources
- GET /api/resources/breathing - Get breathing exercises
- GET /api/resources/learn - Get educational topics
- GET /api/resources/learn/<topic_id> - Get specific topic content
- GET /api/external/search - Search for therapists (DuckDuckGo)
"""
from __future__ import annotations

import logging
import sys
import urllib.parse
from pathlib import Path
from typing import Any, Dict, List, Optional

from flask import Blueprint, jsonify, request

# Ensure project root is in path
ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.resources.data import (
    MINDFULNESS_RESOURCES,
    BREATHING_EXERCISES,
    LEARN_TOPICS,
    DISCLAIMER
)

logger = logging.getLogger("walls.resources.api")

# ---------------------------------------------------------------------------
# Blueprint
# ---------------------------------------------------------------------------

resources_bp = Blueprint("resources", __name__)


# ---------------------------------------------------------------------------
# Mindfulness Resources Endpoints
# ---------------------------------------------------------------------------

@resources_bp.route("/mindfulness", methods=["GET"])
def get_mindfulness_resources():
    """
    Get curated mindfulness resources.
    
    Query Params:
    - category: Filter by category (meditation_apps, youtube_channels, etc.)
    """
    category = request.args.get("category")
    
    if category:
        if category in MINDFULNESS_RESOURCES:
            resources = {category: MINDFULNESS_RESOURCES[category]}
        else:
            return jsonify({"error": f"Unknown category: {category}"}), 400
    else:
        resources = MINDFULNESS_RESOURCES
    
    return jsonify({
        "resources": resources,
        "disclaimer": DISCLAIMER,
        "categories": list(MINDFULNESS_RESOURCES.keys())
    }), 200


@resources_bp.route("/breathing", methods=["GET"])
def get_breathing_exercises():
    """
    Get breathing exercises.
    
    Query Params:
    - id: Get specific exercise by ID
    """
    exercise_id = request.args.get("id")
    
    if exercise_id:
        exercise = next((e for e in BREATHING_EXERCISES if e["id"] == exercise_id), None)
        if not exercise:
            return jsonify({"error": f"Exercise not found: {exercise_id}"}), 404
        return jsonify({"exercise": exercise}), 200
    
    return jsonify({
        "exercises": BREATHING_EXERCISES,
        "disclaimer": "These exercises are for relaxation purposes. Stop if you feel dizzy or uncomfortable."
    }), 200


@resources_bp.route("/learn", methods=["GET"])
def get_learn_topics():
    """Get list of educational topics (summaries only)."""
    summaries = [
        {
            "id": t["id"],
            "title": t["title"],
            "summary": t["summary"],
            "icon": t["icon"]
        }
        for t in LEARN_TOPICS
    ]
    
    return jsonify({"topics": summaries}), 200


@resources_bp.route("/learn/<topic_id>", methods=["GET"])
def get_learn_topic(topic_id: str):
    """Get full content for a specific educational topic."""
    topic = next((t for t in LEARN_TOPICS if t["id"] == topic_id), None)
    
    if not topic:
        return jsonify({"error": f"Topic not found: {topic_id}"}), 404
    
    return jsonify({
        "topic": topic,
        "disclaimer": DISCLAIMER
    }), 200


# ---------------------------------------------------------------------------
# External Search (Therapist Finder)
# ---------------------------------------------------------------------------

@resources_bp.route("/search/therapist", methods=["GET"])
def search_therapist():
    """
    Generate a search URL for finding therapists.
    
    NOTE: This does NOT make external API calls to protect user privacy.
    Instead, it returns a properly formatted search URL the frontend can open.
    
    Query Params:
    - location: User's city/state or "near me"
    - specialty: Optional specialty (anxiety, depression, etc.)
    """
    location = request.args.get("location", "near me")
    specialty = request.args.get("specialty", "")
    
    # Build search query
    query_parts = ["therapist", specialty, location]
    query = " ".join(part for part in query_parts if part)
    
    # Generate search URLs (user's browser will handle the actual search)
    encoded_query = urllib.parse.quote(query)
    
    search_urls = {
        "duckduckgo": f"https://duckduckgo.com/?q={encoded_query}",
        "google": f"https://www.google.com/search?q={encoded_query}",
        "psychology_today": f"https://www.psychologytoday.com/us/therapists?search={urllib.parse.quote(location)}"
    }
    
    # Curated directories (no tracking)
    directories = [
        {
            "name": "Psychology Today",
            "url": "https://www.psychologytoday.com/us/therapists",
            "description": "Comprehensive therapist directory with filters for specialty, insurance, and location."
        },
        {
            "name": "Open Path Collective",
            "url": "https://openpathcollective.org/",
            "description": "Affordable therapy network with sessions starting at $30-$80."
        },
        {
            "name": "SAMHSA Treatment Locator",
            "url": "https://findtreatment.gov/",
            "description": "Official US government resource for finding mental health treatment facilities."
        },
        {
            "name": "NAMI HelpLine",
            "url": "https://www.nami.org/help",
            "description": "National Alliance on Mental Illness provides referrals and support."
        }
    ]
    
    return jsonify({
        "query": query,
        "search_urls": search_urls,
        "directories": directories,
        "privacy_note": "WALLS does not track your searches. Links open in your browser."
    }), 200


@resources_bp.route("/crisis", methods=["GET"])
def get_crisis_resources():
    """Get crisis helpline resources."""
    crisis_resources = MINDFULNESS_RESOURCES.get("crisis_resources", [])
    
    return jsonify({
        "resources": crisis_resources,
        "message": "If you are in immediate danger, please call 911 (US) or your local emergency number.",
        "is_urgent": True
    }), 200


# ---------------------------------------------------------------------------
# Quick Tips
# ---------------------------------------------------------------------------

QUICK_TIPS = [
    {
        "id": "grounding",
        "title": "5-4-3-2-1 Grounding",
        "content": "Notice 5 things you can see, 4 things you can touch, 3 things you can hear, 2 things you can smell, 1 thing you can taste.",
        "category": "anxiety"
    },
    {
        "id": "cold_water",
        "title": "Cold Water Reset",
        "content": "Splash cold water on your face or hold an ice cube. This activates the dive reflex and can quickly reduce anxiety.",
        "category": "anxiety"
    },
    {
        "id": "movement",
        "title": "Move Your Body",
        "content": "Even 5 minutes of walking, stretching, or dancing can shift your mood by releasing endorphins.",
        "category": "depression"
    },
    {
        "id": "gratitude",
        "title": "Three Good Things",
        "content": "Write down three good things that happened today, no matter how small. This rewires your brain to notice positives.",
        "category": "depression"
    },
    {
        "id": "sleep_tip",
        "title": "Screen-Free Hour",
        "content": "Stop using screens 1 hour before bed. Blue light suppresses melatonin production.",
        "category": "sleep"
    },
    {
        "id": "stress_tip",
        "title": "Brain Dump",
        "content": "Write everything on your mind onto paper. Getting thoughts out of your head reduces mental load.",
        "category": "stress"
    }
]


@resources_bp.route("/tips", methods=["GET"])
def get_quick_tips():
    """
    Get quick mental health tips.
    
    Query Params:
    - category: Filter by category (anxiety, depression, sleep, stress)
    """
    category = request.args.get("category")
    
    if category:
        tips = [t for t in QUICK_TIPS if t["category"] == category]
    else:
        tips = QUICK_TIPS
    
    return jsonify({"tips": tips}), 200

