"""
Legacy Flask routes preserved for backward compatibility.

This blueprint mirrors the previous app.py behavior, including the survey
workflow that triggers the classic DecisionTree-based diagnosis.
"""
from __future__ import annotations

from flask import Blueprint, jsonify, render_template, request

from legacy.disorder import Disorder

legacy_bp = Blueprint(
    "legacy",
    __name__,
    template_folder="../templates",
    static_folder="../Static",
)


@legacy_bp.route("/")
@legacy_bp.route("/home")
def home():
    return render_template("index.html")


@legacy_bp.route("/thome")
def thome():
    return render_template("home.html", value="dog")


@legacy_bp.route("/login")
def login():
    return render_template("login.html")


@legacy_bp.route("/logout")
def logout():
    return home()


@legacy_bp.route("/register")
def register():
    return render_template("signup.html")


@legacy_bp.route("/philo")
def philo():
    return render_template("philo.html")


@legacy_bp.route("/exercise")
def exercise():
    return render_template("exercise.html")


@legacy_bp.route("/home2")
def home2():
    return render_template("home2.html")


@legacy_bp.route("/aid")
def aid():
    return render_template("aid.html")


@legacy_bp.route("/calendar")
def calendar():
    return render_template("calendar.html")


@legacy_bp.route("/social")
def social():
    return render_template("social.html")


@legacy_bp.route("/process-data", methods=["POST"])
def process_data():
    """
    Legacy prediction endpoint.

    Accepts JSON `answers` (yes/no list) and renders the legacy home page.
    """
    data = request.json.get("answers") if request.is_json else None
    d = Disorder()
    prediction = d.getDisorder(data) if data else None
    # For backward compatibility, still render the home template.
    return render_template("home.html", value="cat", prediction=prediction)


@legacy_bp.route("/survey")
def survey():
    return render_template("main.html")


