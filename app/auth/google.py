from datetime import datetime as dt
from secrets import token_urlsafe
from flask import flash, redirect, url_for

from flask_babel import lazy_gettext as _l
from flask_login import login_user, current_user
from flask_dance.consumer.storage.sqla import SQLAlchemyStorage
from flask_dance.consumer import oauth_authorized, oauth_error
from flask_dance.contrib.google import make_google_blueprint
from sqlalchemy.orm.exc import NoResultFound

from app.utils.misc import generate_uuid
from app import db
from app.models import OAuth, User

google_bp = make_google_blueprint(
    scope=[
        'https://www.googleapis.com/auth/plus.me',
        'https://www.googleapis.com/auth/userinfo.email',
        'https://www.googleapis.com/auth/userinfo.profile'
    ],
    storage=SQLAlchemyStorage(OAuth, db.session, user=current_user),
)

@oauth_authorized.connect_via(google_bp)
def google_logged_in(blueprint, token):
    if not token:
        flash("Failed to log in.", category="error")
        current_app.logger.warning("Missing token for OAuth login")
        return redirect(url_for('main.home'))

    resp = blueprint.session.get("/oauth2/v1/userinfo")
    if not resp.ok:
        msg = "Failed to fetch user info."
        flash(msg, category="error")
        current_app.logger.warning("Failed response for OAuth login")
        return redirect(url_for('main.home'))

    info = resp.json()
    user_id = info.get("id", None)
    query = OAuth.query.filter_by(
        provider=blueprint.name,
        provider_user_id=user_id)

    try:
        oauth = query.one()
    except NoResultFound:
        oauth = OAuth(
            provider=blueprint.name,
            provider_user_id=user_id,
            token=token)

    if oauth.user:
        user = oauth.user
    else:
        # Create a new local user account for this user
        username = info.get("given_name", "No name")
        user = User(
            username=username.lower(),
            email=info.get("email", "No email"),
            token=token_urlsafe(),
            token_expiration=dt.now()
        )
        password_generated = generate_uuid()
        user.set_password(password_generated)
        # Associate the new local user account with the OAuth token
        oauth.user = user
        db.session.add_all([user, oauth])
        db.session.commit()
        flash(_l("Signed up with your Google account"), 'success')
    login_user(user)
    next_page = request.args.get('next')
    return redirect(next_page or url_for('main.home'))

@oauth_error.connect_via(google_bp)
def google_error(blueprint, message, response):
    msg = ("OAuth error{name}! ""{message} {response}").format(
        name=blueprint.name, message=message, response=response
    )
    flash(msg, "error")
    current_app.logger.warning("Google OAuth error:{}".format(msg))
    return redirect(url_for('main.home'))
