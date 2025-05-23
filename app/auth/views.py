from flask import (
    request,
    flash,
    redirect,
    url_for,
)
from flask_login import current_user, logout_user
from app.utils.decorators import custom_login, login_required, is_logged_in
from . import auth
from app.models import *
from app.email import send_email
from app.utils import misc
from app.auth.flows import UserFlow


@auth.route("/login", methods=["GET"])
@is_logged_in
def get_login():
    return render_template("auth/login.html")


@auth.route("/login", methods=["POST"])
@is_logged_in
def post_login():
    next_page = request.args.get("next")
    return UserFlow(
        request.form, "login", "local", next_page=next_page or url_for("main.home")
    ).handle_flow()


@auth.route("/logout")
def logout():
    logout_user()
    flash("You are logged out", "success")
    return redirect(url_for("auth.get_login"))


@auth.route("/confirm-email", methods=["GET"])
@login_required
def confirm_email():
    if current_user.email_confirmed_at:
        flash("User is already confirmed.")
        return redirect(url_for("main.home"))
    print(current_app.is_email_configured)
    return render_template(
        "auth/confirm_email.html", email_configured=current_app.is_email_configured
    )


@auth.route("/login/tenants/<string:tid>", methods=["GET", "POST"])
@is_logged_in
def login_with_magic_link(tid):
    next_page = request.args.get("next")
    if current_user.is_authenticated:
        return redirect(next_page or url_for("main.home"))

    if not current_app.is_email_configured:
        flash("Email is not configured", "warning")
        abort(404)
    if not (tenant := Tenant.query.get(tid)):
        abort(404)
    if not tenant.magic_link_login:
        flash("Feature is not enabled", "warning")
        abort(404)
    if request.method == "POST":
        email = request.form["email"]
        if not (user := User.find_by_email(email)):
            flash("Invalid email", "warning")
            tenant.add_log(message=f"invalid email for {email}", level="warning")
            return redirect(url_for("auth.login_with_magic_link", tid=tid))
        if not user.is_active:
            flash("User is inactive", "warning")
            tenant.add_log(
                message=f"inactive user tried to login:{email}",
                level="warning",
            )
            return redirect(next_page or url_for("auth.login_with_magic_link", tid=tid))
        # send email with login
        token = user.generate_magic_link(tid)
        link = f"{current_app.config['HOST_NAME']}magic-login/{token}"
        title = f"{current_app.config['APP_NAME']}: Login Request"
        content = f"You have requested a login via email. If you did not request a magic link, please ignore. Otherwise, please click the button below to login."
        send_email(
            title,
            recipients=[email],
            text_body=render_template(
                "email/basic_template.txt",
                title=title,
                content=content,
                button_link=link,
            ),
            html_body=render_template(
                "email/basic_template.html",
                title=title,
                content=content,
                button_link=link,
                button_label="Login",
            ),
        )
        tenant.add_log(message=f"magic link login request to {email}")
        flash("Please check your email for the login information")
    return render_template("auth/magic-login.html", tid=tid)


@auth.route("/magic-login/<string:token>", methods=["GET"])
@is_logged_in
def validate_magic_link(token):
    next_page = request.args.get("next")
    if not (vtoken := User.verify_magic_token(token)):
        flash("Token is invalid", "warning")
        return redirect(url_for("auth.get_login"))
    if not (user := User.query.get(vtoken.get("user_id"))):
        flash("Invalid user id", "warning")
        return redirect(url_for("auth.get_login"))
    if not (tenant := Tenant.query.get(vtoken.get("tenant_id"))):
        flash("Invalid tenant id", "warning")
        return redirect(url_for("auth.get_login"))
    if user.id == tenant.owner_id or user.has_tenant(tenant):
        flash("Welcome")
        Logs.add(message=f"{user.email} logged in via magic link", user_id=user.id)
        custom_login(user)
        return redirect(next_page or url_for("main.home"))
    flash("User can not access tenant", "warning")
    return redirect(url_for("auth.get_login"))


@auth.route("/accept", methods=["GET"])
@is_logged_in
def get_accept():
    """
    GET endpoint for a user accepting invitations
    """
    if not (result := User.verify_invite_token(request.args.get("token"))):
        abort(403, "Invalid or expired invite token")

    if not (user := User.find_by_email(result.get("email"))):
        abort(403, "Invalid token: email not found")

    # If user has already logged in, we show them the login page, otherwise
    # we will show them the accept page (register)
    result["login_count"] = user.login_count
    if user.login_count > 0:
        return redirect(
            url_for(
                "auth.get_login", email=result.get("email"), tenant=result.get("tenant")
            )
        )

    return render_template(
        "auth/accept.html", data=result, token=request.args.get("token")
    )


@auth.route("/accept", methods=["POST"])
@is_logged_in
def post_accept():
    """
    POST endpoint for a user accepting invitations
    """
    next_page = request.args.get("next")
    attributes = {"token": request.args.get("token")}
    return UserFlow(
        user_info=request.form,
        flow_type="accept",
        provider="local",
        next_page=next_page,
    ).handle_flow(attributes)


@auth.route("/reset-password", methods=["GET", "POST"])
def reset_password_request():
    next_page = request.args.get("next")
    internal = request.args.get("internal")
    if current_user.is_authenticated and not internal:
        return redirect(next_page or url_for("main.home"))

    if not current_app.is_email_configured:
        flash("Email is not configured. Please contact your admin.", "warning")
        return redirect(url_for("main.home"))

    if request.method == "POST":
        email = request.form.get("email")
        if not (user := User.find_by_email(email)):
            flash("Email sent, check your mail")
            return redirect(next_page or url_for("auth.reset_password_request"))
        Logs.add(
            message=f"{email} requested a password reset",
            level="warning",
            user_id=user.id,
        )
        token = user.generate_auth_token()
        link = f"{current_app.config['HOST_NAME']}reset-password/{token}"
        title = "Password reset"
        content = f"You have requested a password reset. If you did not request a reset, please ignore. Otherwise, click the button below to continue."
        send_email(
            title,
            recipients=[email],
            text_body=render_template(
                "email/basic_template.txt",
                title=title,
                content=content,
                button_link=link,
            ),
            html_body=render_template(
                "email/basic_template.html",
                title=title,
                content=content,
                button_link=link,
                button_label="Reset",
            ),
        )
        flash("Email sent, check your mail")
        return redirect(url_for("auth.get_login"))
    return render_template("auth/reset_password_request.html")


@auth.route("/reset-password/<string:token>", methods=["GET", "POST"])
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(url_for("main.home"))
    if not (user := User.verify_auth_token(token)):
        Logs.add(
            message="invalid or missing token for password reset",
            level="warning",
            user_id=user.id,
        )
        flash("Missing or invalid token", "warning")
        return redirect(url_for("auth.reset_password_request"))
    if request.method == "POST":
        password = request.form.get("password")
        password2 = request.form.get("password2")
        if not misc.perform_pwd_checks(password, password_two=password2):
            flash("Password did not pass checks", "warning")
            return redirect(url_for("auth.reset_password", token=token))
        user.set_password(password, set_pwd_change=True)
        db.session.commit()
        flash("Password reset! Please login with your new password", "success")
        Logs.add(
            message=f"{user.email} reset their password",
            level="warning",
            user_id=user.id,
        )
        return redirect(url_for("auth.get_login"))
    return render_template("auth/reset_password.html", token=token)


@auth.route("/set-password", methods=["GET"])
@login_required
def set_password():
    """
    When a user must set or change their password
    """
    return render_template("auth/set_password.html")


@auth.route("/register", methods=["GET"])
@is_logged_in
def get_register():

    if not current_app.is_self_registration_enabled:
        abort(403, "Self-service registration is disabled")

    return render_template(
        "auth/register.html",
        registration_enabled=current_app.is_self_registration_enabled,
    )


@auth.route("/register", methods=["POST"])
def post_register():
    """
    POST endpoint for registering new users
    """
    attributes = {"token": request.args.get("token") or request.form.get("token")}
    return UserFlow(request.form, "register", "local").handle_flow(attributes)


@auth.route("/get-started", methods=["GET"])
@login_required
def get_started():
    return render_template("auth/get_started.html")


@auth.route("/get-started", methods=["POST"])
@login_required
def post_get_started():
    """
    Endpoint for creating new tenants after a user registers
    """
    result = Authorizer(current_user).can_user_create_tenants()
    if not (tenant_name := request.form.get("tenant")):
        abort(400, "Tenant name is required")
    try:
        tenant = Tenant.create(
            current_user,
            tenant_name,
            current_user.email,
            init_data=True,
        )
    except Exception as e:
        abort(400, str(e))
    flash("Created tenant")
    return redirect(url_for("main.home"))
