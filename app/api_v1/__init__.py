from flask import Blueprint

api = Blueprint("api", __name__)

from . import base, views, vendors, integrations, settings, questionnaire, forms
