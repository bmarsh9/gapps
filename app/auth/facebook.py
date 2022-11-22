from datetime import datetime as dt
from secrets import token_urlsafe
from flask import flash, redirect, url_for

from flask_babel import lazy_gettext as _l
from flask_login import login_user, current_user
from flask_dance.consumer.storage.sqla import SQLAlchemyStorage
from flask_dance.consumer import oauth_authorized, oauth_error
from flask_dance.contrib.facebook import make_facebook_blueprint
from sqlalchemy.orm.exc import NoResultFound

from app.utils.misc import get_random_password_string
from app import db
from app.models import OAuth, User

facebook_bp = make_facebook_blueprint(
    storage=SQLAlchemyStorage(OAuth, db.session, user=current_user)
)

@oauth_authorized.connect_via(facebook_bp)
def facebook_logged_in(blueprint, token):
    if not token:
        flash("Failed to log in.", category="error")
        return redirect(url_for('main.index'))
    resp = blueprint.session.get("/me?fields=email,name")
    if not resp.ok:
        msg = "Failed to fetch user info."
        flash(msg, "warning")
        return redirect(url_for('main.index'))

    info = resp.json()
    user_id = info.get("id", None)
    query = OAuth.query.filter_by(
        provider=blueprint.name,
        provider_user_id=str(user_id))

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
        username = info.get("name", "No name")
        email = info.get("email")
        user = User(
            username=username.lower(),
            email=email,
            created=dt.now(),
            token=token_urlsafe(),
            token_expiration=dt.now()
        )
        password_generated = get_random_password_string(10)
        user.set_password(password_generated)
        # Associate the new local user account with the OAuth token
        oauth.user = user
        db.session.add_all([user, oauth])
        db.session.commit()
        flash(_l("Successfully facebook connection"), 'success')
    login_user(user)
    return redirect(url_for('main.index'))


@oauth_error.connect_via(facebook_bp)
def facebook_error(blueprint, message, response):
    msg = (_l("{message} {response}")).format(
        message=message,
        response=response
    )
    flash(msg, 'warning')
    return redirect(url_for('auth.login'))
