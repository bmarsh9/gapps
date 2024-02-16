from flask import Flask,request,render_template,jsonify
from config import config
from flask_babel import Babel, lazy_gettext as _l
import json

from app.db import db
from app.login import login
from app.utils.custom_errors import CustomError

babel = Babel()

def create_app(config_name="default"):
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    config[config_name].init_app(app)

    configure_models(app)
    registering_blueprints(app)
    configure_extensions(app)

    @app.errorhandler(Exception)
    def handle_error(error):
        if isinstance(error, CustomError):
            message = error.message
            status = error.status
            response = jsonify({"error": message})
            response.status_code = status
            return response
        return None

    @app.errorhandler(404)
    def not_found(e):
        if request.path.startswith("/api/"):
            if isinstance(e.description, dict):
                return jsonify(e.description), e.code
            return jsonify({"ok":False, "message":e.description, "code":e.code}), e.code
        return render_template("layouts/errors/default.html", title="Not found"), e.code

    @app.errorhandler(403)
    def not_authorized(e):
        if request.path.startswith("/api/"):
            if isinstance(e.description, dict):
                return jsonify(e.description), e.code
            return jsonify({"ok":False, "message":e.description, "code":e.code}), e.code
        return render_template("layouts/errors/default.html", title="Unauthorized"), e.code

    @app.errorhandler(401)
    def not_authenticated(e):
        if request.path.startswith("/api/"):
            if isinstance(e.description, dict):
                return jsonify(e.description), e.code
            return jsonify({"ok":False, "message":e.description, "code":e.code}), e.code
        return render_template("layouts/errors/default.html", title="Unauthenticated"), e.code

    @app.errorhandler(500)
    def internal_error(e):
        if request.path.startswith("/api/"):
            if isinstance(e.description, dict):
                return jsonify(e.description), e.code
            return jsonify({"ok":False, "message":e.description, "code":e.code}), e.code
        return render_template("layouts/errors/default.html", title="Internal error"), e.code

    def to_pretty_json(value):
        return json.dumps(value, sort_keys=True,
                      indent=4, separators=(',', ': '))

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
