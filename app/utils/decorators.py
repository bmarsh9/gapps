from functools import wraps
from flask import current_app, g, request, jsonify,redirect,url_for,session,flash
from app.models import *
from app import db
from flask_login import current_user, login_user

def validate_token_in_header(enc_token):
    user = User.verify_auth_token(enc_token)
    if not user:
        return False
    if not user.is_active:
        return False
    return user

def is_vendor_for_tenant(current_user):
    if tenant := Tenant.query.get(session.get("tenant-id")):
        if tenant.has_user_with_role(current_user, "vendor"):
            return True
    return False

def is_super(f):
    @wraps(f)
    def decorated_function(*args, **kws):
        if not current_user.super:
            return jsonify({"message":"unauthorized"}),401
        return f(*args, **kws)
    return decorated_function

def roles_denied(*role_names):
    """| This decorator ensures that the current user is logged in,
    | and does not have *at least one* of the specified roles (OR operation).
    Example::
        @route('/edit_article')
        @roles_denied('Writer', 'Editor')
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
            if current_user.has_any_role_for_tenant_by_id(session.get("tenant-id"), role_names) and not current_user.super:
                if enc_token:
                    return jsonify({"message":"forbidden"}),403
                # Redirect to the unauthorized page
                flash("User does not have the required roles to access this resource!",category="warning")
                return redirect(url_for("main.home"))

            # It's OK to call the view
            return view_function(*args, **kwargs)

        return decorator

    return wrapper

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
            if not current_user.has_any_role_for_tenant_by_id(session.get("tenant-id"), role_names) and not current_user.super:
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
            if not current_user.has_all_roles_for_tenant_by_id(session.get("tenant-id"), *role_names) and not current_user.super:
                if enc_token:
                    return jsonify({"message":"forbidden"}),403
                # Redirect to the unauthorized page
                flash("User does not have the required roles to access this resource!",category="warning")
                return redirect(url_for("main.home"))

            # It's OK to call the view
            return view_function(*args, **kwargs)

        return decorator

    return wrapper

def login_required(view_function):
    """ This decorator ensures that the current user is logged in.
    Example::
        @route('/member_page')
        @login_required
        def member_page():  # User must be logged in
            ...
    If USER_ENABLE_EMAIL is True and USER_ENABLE_CONFIRM_EMAIL is True,
    this view decorator also ensures that the user has a confirmed email address.
    | Calls unauthorized_view() when the user is not logged in
        or when the user has not confirmed their email address.
    | Calls the decorated view otherwise.
    """
    @wraps(view_function)    # Tells debuggers that is is a function wrapper
    def decorator(*args, **kwargs):
        #user_manager = current_app.user_manager
        from flask_login import current_user

        # try to authenticate with an token (API login, must have token in HTTP header)
        api = False
        if token := request.headers.get("token"):
            api = True
            if not (user := validate_token_in_header(token)):
                return jsonify({"message":"authentication failed"}),401
            current_user = user
            login_user(current_user)
        else:
            if not current_user.is_authenticated:
                return redirect(url_for("auth.login", next=request.full_path))

        # It's OK to call the view
        return view_function(*args, **kwargs)

    return decorator
