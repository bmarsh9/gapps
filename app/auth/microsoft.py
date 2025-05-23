from . import auth
from flask import request, abort, redirect, url_for, session, current_app, flash
from authlib.integrations.base_client.errors import MismatchingStateError
from app.auth.flows import UserFlow
import secrets


@auth.route("/oidc/microsoft/<string:flow>")
def microsoft_auth(flow):
    """Authenticate the user through Microsoft provider for login or registration"""
    if flow not in UserFlow.VALID_FLOW_TYPES:
        abort(400, "Invalid authentication flow")

    if flow == "accept" and not request.args.get("token"):
        abort(400, "Invalid authentication flow: missing acceptance token")

    if not current_app.is_microsoft_auth_configured:
        flash("Provider not configured", "error")
        return redirect(url_for("auth.get_login"))

    nonce = secrets.token_urlsafe(16)
    session["nonce"] = nonce
    session["flow_type"] = flow
    redirect_uri = url_for(
        "auth.authorize_with_microsoft",
        _external=True,
        _scheme=current_app.config["SCHEME"],
    )

    return current_app.providers["microsoft"].authorize_redirect(
        redirect_uri, nonce=nonce
    )


@auth.route("/oidc/microsoft/authorize")
def authorize_with_microsoft():
    """Handles Microsoft callback after authentication"""
    flow = session.get("flow_type")

    try:
        token = current_app.providers["microsoft"].authorize_access_token()
    except MismatchingStateError as e:
        abort(403, "Mismatch error")

    nonce = session.pop("nonce", None)
    user_info = current_app.providers["microsoft"].parse_id_token(token, nonce=nonce)

    attributes = {"token": session.get("token")}
    return UserFlow(
        user_info=user_info, flow_type=flow, provider="microsoft"
    ).handle_flow(attributes)
