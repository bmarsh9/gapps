from datetime import datetime
import logging
from secrets import token_urlsafe
from flask import (
    request,
    render_template,
    flash,
    redirect,
    Blueprint,
    url_for,
    current_app,
    abort
)
from flask_babel import lazy_gettext as _l
from flask_login import current_user, logout_user, login_user, login_required
from . import auth

from app import db
from app.models import *
from app.email import send_email
from app.utils import misc
import datetime

logger = logging.getLogger(__name__)

@auth.route('/login', methods=['GET', 'POST'])
def login():
    next_page = request.args.get('next')
    if current_user.is_authenticated:
        return redirect(next_page or url_for('main.home'))
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        if not (user := User.find_by_email(email)):
            flash(_l('Invalid email or password'), 'warning')
            Logs.add(f"invalid email for {email}", level="warning")
            return redirect(url_for('auth.login'))
        if not user.check_password(password):
            flash(_l('Invalid email or password'), 'warning')
            Logs.add(f"invalid password for email:{email}", level="warning")
            return redirect(next_page or url_for('auth.login'))
        if not user.is_active:
            flash(_l('User is inactive'), 'warning')
            Logs.add(f"inactive user tried to login:{email}", level="warning")
            return redirect(next_page or url_for('auth.login'))
        flash("Welcome")
        Logs.add(f"{email} logged in")
        login_user(user)
        return redirect(next_page or url_for('main.home'))
    return render_template('auth/login.html')

@auth.route('/login/tenants/<int:tid>', methods=['GET', 'POST'])
def login_with_magic_link(tid):
    next_page = request.args.get('next')
    if current_user.is_authenticated:
        return redirect(next_page or url_for('main.home'))
    if not current_app.config["MAIL_USERNAME"] or not current_app.config["MAIL_PASSWORD"]:
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
            flash(_l('Invalid email'), 'warning')
            Logs.add(f"invalid email for {email}", level="warning")
            return redirect(url_for('auth.login_with_magic_link', tid=tid))
        if not user.is_active:
            flash(_l('User is inactive'), 'warning')
            Logs.add(f"inactive user tried to login:{email}", level="warning")
            return redirect(next_page or url_for('auth.login_with_magic_link', tid=tid))
        # send email with login
        token = user.generate_magic_link(tid)
        link = f"{current_app.config['HOST_NAME']}magic-login/{token}"
        title = f"{current_app.config['APP_NAME']}: Login Request"
        content = f"You have requested a login via email. If you did not request a magic link, please ignore. Otherwise, please click the button below to login."
        send_email(
            title,
            sender=current_app.config['MAIL_USERNAME'],
            recipients=[email],
            text_body=render_template(
                'email/basic_template.txt',
                title=title,
                content=content,
                button_link=link
            ),
            html_body=render_template(
                'email/basic_template.html',
                title=title,
                content=content,
                button_link=link,
                button_label="Login"
            )
        )
        Logs.add(f"magic link login request to {email}")
        flash("Please check your email for the login information")
    return render_template('auth/magic-login.html', tid=tid)

@auth.route('/magic-login/<string:token>', methods=['GET'])
def validate_magic_link(token):
    next_page = request.args.get('next')
    if not (vtoken := User.verify_magic_token(token)):
        flash("Token is invalid", "warning")
        return redirect(url_for('auth.login'))
    if not (user := User.query.get(vtoken.get("user_id"))):
        flash("Invalid user id", "warning")
        return redirect(url_for('auth.login'))
    if not (tenant := Tenant.query.get(vtoken.get("tenant_id"))):
        flash("Invalid tenant id", "warning")
        return redirect(url_for('auth.login'))
    if user.id == tenant.owner_id or user.has_tenant(tenant):
        flash("Welcome")
        Logs.add(f"{user.email} logged in via magic link")
        login_user(user)
        return redirect(next_page or url_for('main.home'))
    flash("User can not access tenant", "warning")
    return redirect(url_for('auth.login'))

@auth.route('/logout')
def logout():
    logout_user()
    flash("You are logged out", "success")
    Logs.add(f"{current_user} logged out")
    return redirect(url_for('auth.login'))

@auth.route('/register', methods=['GET', 'POST'])
def register():
    next_page = request.args.get('next')
    if current_user.is_authenticated:
        flash("You are already registered", "success")
        return redirect(next_page or url_for('main.home'))
    email = None
    result = {}
    if token := request.args.get("token"):
        if result := User.verify_invite_token(token):
            email = result["email"]
    if current_app.config["ENABLE_SELF_REGISTRATION"] != "1":
        if not token:
            Logs.add("missing token for registration", level="warning")
            flash("Missing token","warning")
            return redirect(url_for("auth.login"))
        if not result:
            Logs.add(f"invalid or expired token", level="warning")
            flash("Invalid or expired token","warning")
            return redirect(url_for("auth.login"))
    if request.method == "POST":
        email = email or request.form["email"]
        username = request.form.get("username")
        password = request.form.get("password")
        password2 = request.form.get("password2")
        if not User.validate_registration(email, username, password, password2):
            flash("Invalid email, username and/or password", "warning")
            return redirect(next_page or url_for('auth.register', token=token))
        new_user = User.add(email, password=password,
            username=username, confirmed=True,
            tenants=[{"id":result.get("tenant_id"), "roles": result.get("roles",[])}])
        login_user(new_user)
        flash(f'{email}, you are now registered', 'success')
        Logs.add(f"{email} successfully registered")
        return redirect(next_page or url_for('main.home'))
    return render_template('auth/register.html', email=email)

@auth.route("/reset-password", methods=['GET', 'POST'])
def reset_password_request():
    next_page = request.args.get('next')
    internal = request.args.get('internal')
    if current_user.is_authenticated and not internal:
        return redirect(next_page or url_for('main.home'))
    if request.method == "POST":
        email = request.form.get("email")
        if not (user := User.find_by_email(email)):
            flash("Email sent, check your mail")
            return redirect(next_page or url_for('auth.reset_password_request'))
        Logs.add(f"{email} requested a password reset", level="warning")
        token = user.generate_auth_token()
        link = f"{current_app.config['HOST_NAME']}reset-password/{token}"
        title = f"{current_app.config['APP_NAME']}: Password reset"
        content = f"You have requested a password reset. If you did not request a reset, please ignore. Otherwise, click the button below to continue."
        send_email(
            title,
            sender=current_app.config['MAIL_USERNAME'],
            recipients=[email],
            text_body=render_template(
                'email/basic_template.txt',
                title=title,
                content=content,
                button_link=link
            ),
            html_body=render_template(
                'email/basic_template.html',
                title=title,
                content=content,
                button_link=link,
                button_label="Reset"
            )
        )
        flash("Email sent, check your mail")
        return redirect(url_for('auth.login'))
    return render_template('auth/reset_password_request.html')

@auth.route("/reset-password/<token>", methods=['GET', 'POST'])
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))
    if not (user := User.verify_auth_token(token)):
        Logs.add("invalid or missing token for password reset", level="warning")
        flash("Missing or invalid token","warning")
        return redirect(url_for("auth.reset_password_request"))
    if request.method == "POST":
        password = request.form.get("password")
        password2 = request.form.get("password2")
        if not misc.perform_pwd_checks(password, password_two=password2):
            flash("Password did not pass checks", "warning")
            return redirect(url_for("auth.reset_password", token=token))
        user.set_password(password)
        db.session.commit()
        flash("Password reset! Please login with your new password", "success")
        Logs.add(f"{user.email} reset their password", level="warning")
        return redirect(url_for('auth.login'))
    return render_template('auth/reset_password.html',token=token)
