from . import auth
from flask import request, abort, redirect, url_for, session, current_app, flash
from authlib.integrations.base_client.errors import MismatchingStateError
from app.auth.flows import UserFlow
from app.models import Tenant
import secrets


@auth.route("/oidc/google/<string:flow>")
def google_auth(flow):
    """Authenticate the user through Google provider for login or registration"""
    if flow not in UserFlow.VALID_FLOW_TYPES:
        abort(400, "Invalid authentication flow")

    if flow == "accept" and not request.args.get("token"):
        abort(400, "Invalid authentication flow: missing acceptance token")

    if not current_app.is_google_auth_configured:
        flash("Provider not configured", "error")
        return redirect(url_for("auth.get_login"))

    nonce = secrets.token_urlsafe(16)
    session["nonce"] = nonce
    session["flow_type"] = flow
    session["token"] = request.args.get("token")
    redirect_uri = url_for(
        "auth.authorize_with_google",
        _external=True,
        _scheme=current_app.config["SCHEME"],
    )
    return current_app.providers["google"].authorize_redirect(redirect_uri, nonce=nonce)


@auth.route("/oidc/google/authorize")
def authorize_with_google():
    """Handles Google callback after authentication"""
    flow = session.get("flow_type")

    try:
        token = current_app.providers["google"].authorize_access_token()
    except MismatchingStateError as e:
        abort(403, "Mismatch error")

    nonce = session.pop("nonce", None)
    user_info = current_app.providers["google"].parse_id_token(token, nonce=nonce)

    attributes = {"token": session.get("token")}
    return UserFlow(user_info=user_info, flow_type=flow, provider="google").handle_flow(
        attributes
    )
