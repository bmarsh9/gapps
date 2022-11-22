from flask import Flask,request,render_template,jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail
from config import config
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_babel import Babel, lazy_gettext as _l
import json

db = SQLAlchemy()
babel = Babel()
migrate = Migrate()
mail = Mail()
login = LoginManager()
login.login_view = 'auth.login'

def create_app(config_name="default"):
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    config[config_name].init_app(app)

    configure_models(app)
    registering_blueprints(app)
    configure_extensions(app)

    @app.errorhandler(404)
    def not_found(e):
        return render_template("layouts/errors/default.html", title="Not found"), 404

    @app.errorhandler(500)
    def internal_error(e):
        return render_template("layouts/errors/default.html", title="Internal error"), 500

    @app.errorhandler(401)
    def unauthorized(e):
        if 'Authorization' in request.headers:
            return jsonify({"message":"unauthorized"}),401
        return render_template("layouts/errors/default.html", title="Unauthorized"), 401

    @app.errorhandler(400)
    def malformed(e):
        if 'Authorization' in request.headers:
            return jsonify({"message":"malformed request"}),400
        return render_template("layouts/errors/default.html", title="Client error"), 400

    @app.errorhandler(403)
    def forbidden(e):
        if 'Authorization' in request.headers:
            return jsonify({"message":"forbidden"}),403
        return render_template("layouts/errors/default.html", title="Forbidden"), 403

    def is_user_admin(user=False):
        if not user:
            return False
        if user.is_authenticated:
            return user.has_role("admin")
        return False

    def to_pretty_json(value):
        return json.dumps(value, sort_keys=True,
                      indent=4, separators=(',', ': '))

    app.jinja_env.filters['is_admin'] = is_user_admin
    app.jinja_env.filters['tojson_pretty'] = to_pretty_json
    '''
    @app.before_request
    def before_request():
        pass
    '''

    return app

def configure_models(app):
    app.db = db
    return

def configure_extensions(app):
    db.init_app(app)
    mail.init_app(app)
    migrate.init_app(app, db)
    babel.init_app(app)
    login.init_app(app)
    return

def registering_blueprints(app):
    from app.main import main as main_blueprint
    app.register_blueprint(main_blueprint)

    from app.api_v1 import api as api_v1_blueprint
    app.register_blueprint(api_v1_blueprint, url_prefix='/api/v1')

    from app.auth import auth as auth_blueprint
    app.register_blueprint(auth_blueprint)
    return
