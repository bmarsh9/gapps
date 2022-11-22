from functools import wraps
from flask import current_app, g, request, jsonify,redirect,url_for,session,flash
from app.models import *
from app import db
from flask_login import current_user, login_user

def validate_token_in_header(enc_token):
    user = User.verify_auth_token(enc_token)
    if not user: # invalid token
        return False
    if not user.is_active:
        return False
    return False

def has_valid_tenant_key(f):
    @wraps(f)
    def decorated_function(*args, **kws):
        token = request.headers.get("tenant-key")
        tenant = Tenant.query.filter(Tenant.token == token).first()
        if not tenant:
            return jsonify({"registered":False,"msg":"invalid tenant token"}),424
        return f(tenant, *args, **kws)
    return decorated_function

def has_valid_tenant_and_agent(f):
    @wraps(f)
    def decorated_function(*args, **kws):
        token = request.headers.get("tenant-key")
        tenant = Tenant.query.filter(Tenant.token == token).first()
        if not tenant:
            return jsonify({"registered":False,"msg":"invalid tenant token"}),424
        agent_key = request.headers.get("aid")
        if not agent_key:
            return jsonify({"registered":False,"msg":"agent key is missing"}),424
        agent = Agent.find(agent_key)
        if not agent:
            return jsonify({"registered":False,"msg":"agent not found"}),424
        if not agent.enabled:
            return jsonify({"registered":False,"msg":"agent is disabled"}),424
        return f(agent, *args, **kws)
    return decorated_function

def roles_accepted(*role_names):
    """| This decorator ensures that the current user is logged in,
    | and has *at least one* of the specified roles (OR operation).
    Example::
        @route('/edit_article')
        @roles_accepted('Writer', 'Editor')
        def edit_article():  # User must be 'Writer' OR 'Editor'
            ...
    | Calls unauthenticated_view() when the user is not logged in
        or when user has not confirmed their email address.
    | Calls unauthorized_view() when the user does not have the required roles.
    | Calls the decorated view otherwise.
    """
    # convert the list to a list containing that list.
    # Because roles_required(a, b) requires A AND B
    # while roles_required([a, b]) requires A OR B
    def wrapper(view_function):

        @wraps(view_function)    # Tells debuggers that is is a function wrapper
        def decorator(*args, **kwargs):
            from flask_login import current_user

            #// Try to authenticate with an token (API login, must have token in HTTP header)
            enc_token = request.headers.get("token")
            if enc_token:
                user = validate_token_in_header(enc_token)
                if user:
                    current_user = user
                    login_user(user)
                else:
                    return jsonify({"message":"authentication failed"}),401
            else:
                if not current_user.is_authenticated:
                    return redirect(url_for("auth.login"))

            # User must have the required roles
            # NB: roles_required would call has_roles(*role_names): ('A', 'B') --> ('A', 'B')
            # But: roles_accepted must call has_roles(role_names):  ('A', 'B') --< (('A', 'B'),)
            if not current_user.has_role(role_names):
                if enc_token:
                    return jsonify({"message":"forbidden"}),403
                # Redirect to the unauthorized page
                flash("User does not have the required roles to access this resource!",category="warning")
                return redirect(url_for("main.home"))

            # It's OK to call the view
            return view_function(*args, **kwargs)

        return decorator

    return wrapper


def roles_required(*role_names):
    """| This decorator ensures that the current user is logged in,
    | and has *all* of the specified roles (AND operation).
    Example::
        @route('/escape')
        @roles_required('Special', 'Agent')
        def escape_capture():  # User must be 'Special' AND 'Agent'
            ...
    | Calls unauthenticated_view() when the user is not logged in
        or when user has not confirmed their email address.
    | Calls unauthorized_view() when the user does not have the required roles.
    | Calls the decorated view otherwise.
    """
    def wrapper(view_function):

        @wraps(view_function)    # Tells debuggers that is is a function wrapper
        def decorator(*args, **kwargs):
            from flask_login import current_user

            #// Try to authenticate with an token (API login, must have token in HTTP header)
            enc_token = request.headers.get("token")
            if enc_token:
                user = validate_token_in_header(enc_token)
                if user:
                    current_user = user
                    login_user(user)
                else:
                    return jsonify({"message":"authentication failed"}),401
            else:
                if not current_user.is_authenticated:
                    return redirect(url_for("auth.login"))

            # User must have the required roles
            if not current_user.has_roles(*role_names):
                if enc_token:
                    return jsonify({"message":"forbidden"}),403
                # Redirect to the unauthorized page
                flash("User does not have the required roles to access this resource!",category="warning")
                return redirect(url_for("main.home"))

            # It's OK to call the view
            return view_function(*args, **kwargs)

        return decorator

    return wrapper
