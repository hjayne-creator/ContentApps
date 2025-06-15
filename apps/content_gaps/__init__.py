# This file is intentionally empty as all initialization is handled by Flask-SQLAlchemy

from flask import Blueprint
from .models import db, init_db
from .routes import content_gaps_bp

def init_app(app):
    """Initialize the content_gaps app with the Flask app"""
    # Initialize the database
    init_db(app)
    
    # Register the blueprint
    app.register_blueprint(content_gaps_bp)

