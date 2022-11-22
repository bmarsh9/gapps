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
    current_app
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
        if not (user := User.query.filter(User.email == email).first()):
            flash(_l('Invalid email'), 'warning')
            return redirect(url_for('auth.login'))
        if not user.check_password(password):
            flash(_l('Invalid email or password'), 'warning')
            return redirect(next_page or url_for('auth.login'))
        if not user.is_active:
            flash(_l('User is inactive'), 'warning')
            return redirect(next_page or url_for('auth.login'))
        Logs.add_log("{} logged in".format(email),namespace="events")
        login_user(user)
        return redirect(next_page or url_for('main.home'))
    return render_template('auth/login.html')

@auth.route('/logout')
def logout():
    logout_user()
    flash("You are logged out", "success")
    return redirect(url_for('auth.login'))

@auth.route('/register', methods=['GET', 'POST'])
def register():
    next_page = request.args.get('next')
    if current_user.is_authenticated:
        flash("You are already registered", "success")
        return redirect(next_page or url_for('main.home'))

    email = None
    result = None
    if token := request.args.get("token"):
        if result := User.verify_invite_token(token):
            email = result["email"]

    if current_app.config["ENABLE_SELF_REGISTRATION"] != "1":
        if not token:
            flash("Missing token","warning")
            return redirect(url_for("auth.login"))
        if not result:
            flash("Invalid or expired token","warning")
            return redirect(url_for("auth.login"))
    if request.method == "POST":
        email = email or request.form["email"]
        username = request.form.get("username")
        password = request.form["password"]
        password2 = request.form["password2"]
        if not misc.perform_pwd_checks(password, password_two=password2):
            flash("Password did not pass checks", "warning")
            return redirect(url_for("auth.register", token=token))
        if user := User.query.filter(User.email == email).first():
            flash(f'({email}) already exists', 'warning')
            return redirect(url_for('auth.register', token=token))
        else:
            new_user = User.add(email, password=password,
                username=username, confirmed=True, roles=["User"], create_role=True)
            login_user(new_user)
            flash(f'{email}, you are now registered', 'success')
        return redirect(next_page or url_for('main.home'))
    return render_template('auth/register.html', email=email)

@auth.route("/reset_password", methods=['GET', 'POST'])
def reset_password():
    next_page = request.args.get('next')
    if current_user.is_authenticated:
        return redirect(next_page or url_for('main.home'))
    form = ResetPasswordReq()
    if form.validate_on_submit():
        email = form.email.data
        user = User.query.filter_by(email=email).first()
        if user:
            token = user.verify_expiration_token()
            db.session.commit()
            send_email(
                _l('Request change password'),
                sender=current_app.config['ADMINS'][0],
                recipients=[user.email],
                text_body=render_template(
                    'email/reset_password.txt',
                    token=token),
                html_body=render_template(
                    'email/reset_password.html',
                    token=token)
            )
            flash("Email sent, check your mail now!", "info")
            Logs.add_log("{} requested a password reset".format(user.email),namespace="events")
            return redirect(url_for('auth.login'))
        flash("This email not registered", "info")
    return render_template('auth/reset_password_req.html', form=form)

@auth.route("/reset_password_token/<token>", methods=['GET', 'POST'])
def reset_password_token(token):
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))
    form = ResetPassword()
    if form.validate_on_submit():
        user = User.query.filter_by(token=token).first()
        if user:
            user.set_password(form.password.data)
            db.session.commit()
            flash("Password changed!", "success")
            Logs.add_log("{} reset their password".format(user.email),namespace="events")
            return redirect(url_for('auth.login'))
    return render_template('auth/reset_password.html', form=form)
