import logging
import os
from authlib.integrations.flask_client import OAuth
from flask import Blueprint, current_app, url_for, redirect, session, flash, request
import jwt
from app.models import User  # Adjust this import based on your user model
from flask_login import login_user  # Import login_user from Flask-Login

logger = logging.getLogger(__name__)

oidc_bp = Blueprint('oidc', __name__)
oauth = OAuth(current_app)

def get_oidc_client():
    logger.debug("Initializing OIDC client")
    return oauth.register(
        'oidc',
        client_id=current_app.config['OIDC_CLIENT_ID'],
        client_secret=current_app.config['OIDC_CLIENT_SECRET'],
        server_metadata_url=current_app.config['OIDC_DISCOVERY_URL'],
        client_kwargs={'scope': 'openid email profile'}
    )

@oidc_bp.route('/login')
def login():
    oidc = get_oidc_client()
    redirect_uri = url_for('.auth', _external=True)
    
    try:
        nonce = os.urandom(16).hex()
        session['oidc_nonce'] = nonce
        logger.debug(f"Generated nonce: {nonce}")
        logger.debug(f"Redirecting to OIDC provider. Redirect URI: {redirect_uri}, Nonce: {nonce}")
        return oidc.authorize_redirect(redirect_uri, nonce=nonce)
    except Exception as e:
        logger.error(f'Nonce generation error: {e}', exc_info=True)
        flash('Authentication error.', 'error')
        return redirect(url_for('main.home'))

@oidc_bp.route('/auth')
def auth():
    oidc = get_oidc_client()
    try:
        token = oidc.authorize_access_token()
        if not token:
            logger.error('Failed to authenticate with OIDC provider.')
            flash('Authentication failed.', 'error')
            return redirect(url_for('main.home'))

        # Retrieve the nonce from the session
        nonce = session.pop('oidc_nonce', None)
        logger.debug(f"Retrieved nonce from session: {nonce}")

        # Extract the nonce from the ID token
        id_token = oidc.parse_id_token(token, nonce=nonce)
        received_nonce = id_token.get('nonce')
        logger.debug(f"Received nonce from ID token: {received_nonce}")

        if not nonce or nonce != received_nonce:
            logger.error('Nonce mismatch or missing.')
            flash('Authentication error.', 'error')
            return redirect(url_for('main.home'))

        user_info = oidc.parse_id_token(token, nonce=nonce)
        logger.debug(f"User authenticated: {user_info}")

        # Check if user exists in your system
        user = User.find_by_email(user_info['email'])
        if user:
            logger.debug('User found in database.')
            # Proceed with login using Flask-Login's login_user
            login_user(user)
        else:
            logger.error('User not found in database.')
            # Handle non-existent user (e.g., redirect or error message)

        return redirect(url_for('main.dashboard'))
    except Exception as e:
        logger.error(f'OIDC authentication error: {e}', exc_info=True)
        flash('Authentication error.', 'error')
        return redirect(url_for('main.home'))

@oidc_bp.route('/oidc/logout')
def oidc_logout():
    oidc = get_oidc_client()
    
    # Retrieve the client ID from your OAuth client registration
    client_id = oidc.client_id
    
    return oidc.logout(
        redirect_uri=url_for('.index', _external=True),
        post_logout_redirect_uri=url_for('.index', _external=True),
        client_id=client_id  # Use the client ID from your OAuth registration
    )