# app/auth/__init__.py

from flask import Blueprint

# Existing auth blueprint
auth = Blueprint('auth', __name__)

# Import OIDC blueprint from oidc.py
from .oidc import oidc_bp

# Import views of auth
from . import views

# Function to register blueprints
def register_auth_blueprints(app):
    app.register_blueprint(auth)
    app.register_blueprint(oidc_bp, url_prefix='/oidc')