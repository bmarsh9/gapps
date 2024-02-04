from app import create_app
from flask_session import Session
from werkzeug.middleware.proxy_fix import ProxyFix
import os

app = create_app(os.getenv('FLASK_CONFIG') or 'default')

# Apply ProxyFix middleware to handle X-Forwarded-Proto header
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1)

# Configure server-side session
app.config['SESSION_TYPE'] = 'filesystem'
Session(app)

if __name__ == "__main__":
    app.run(use_reloader=False)