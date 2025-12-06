"""
WALLS Resources Module

Provides curated mindfulness resources and external search.
"""
from .api import resources_bp
from .data import MINDFULNESS_RESOURCES, BREATHING_EXERCISES, LEARN_TOPICS

__all__ = ["resources_bp", "MINDFULNESS_RESOURCES", "BREATHING_EXERCISES", "LEARN_TOPICS"]

