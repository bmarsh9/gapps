from flask import (
    current_app,
    jsonify,
    request
)
from . import api
from app.models import *
from app.utils.authorizer import Authorizer
from app.utils.decorators import login_required
from app.utils.integrations import api_get


@api.route("/integrations", methods=["GET"])
@login_required
def list_integrations():
    response = api_get("integrations")
    return jsonify(response)

@api.route("/deployments", methods=["GET"])
@login_required
def list_deployments():
    response = api_get("deployments")
    return jsonify(response)

@api.route("/deployments/<string:id>", methods=["GET"])
@login_required
def get_deployment(id):
    response = api_get(f"deployments/{id}")
    return jsonify(response)

@api.route("/deployments/<string:id>/violations", methods=["GET"])
@login_required
def list_violations_for_deployment(id):
    response = api_get(f"deployments/{id}/violations")
    return jsonify(response)

