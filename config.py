from sqlalchemy.engine.url import make_url
from flask import request
import os


basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    APP_NAME = os.environ.get("APP_NAME","Gapps")
    APP_SUBTITLE = os.environ.get("APP_SUBTITLE","")
    CR_YEAR = os.environ.get("CR_YEAR","2023")
    VERSION = os.environ.get("VERSION","1.0.0")

    try:
        if host_name := os.environ.get("HOST_NAME"):
            if not host_name.startswith("http"):
                host_name = f"https://{host_name}"
            if not host_name.endswith("/"):
                host_name = f"{host_name}/"
            HOST_NAME = host_name
        else:
            HOST_NAME = request.host_url
    except:
        HOST_NAME = ""

    LOG_TYPE = os.environ.get("LOG_TYPE", "stream")
    LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")
    WORKER_LOG_LEVEL = os.environ.get("WORKER_LOG_LEVEL", LOG_LEVEL)

    SECRET_KEY = os.environ.get('SECRET_KEY', 'change_secret_key')
    SQLALCHEMY_COMMIT_ON_TEARDOWN = True
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_RECORD_QUERIES = False
    MAIL_SERVER = os.environ.get('MAIL_SERVER','smtp.googlemail.com')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS = os.environ.get("MAIL_USE_TLS", "True") == "True"
    MAIL_DEBUG = os.environ.get("MAIL_DEBUG", "False") == "True"
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    BASE_DIR = basedir
    ENABLE_SELF_REGISTRATION = os.environ.get("ENABLE_SELF_REGISTRATION",False)
    ENABLE_GOOGLE_AUTH = os.environ.get("ENABLE_GOOGLE_AUTH","0")
    DOC_LINK = os.environ.get("DOC_LINK","https://github.com/bmarsh9/gapps")
    CONSOLE_LINK = os.environ.get("CONSOLE_LINK","https://github.com/bmarsh9/gapps")

    DEFAULT_EMAIL = os.environ.get("DEFAULT_EMAIL", "admin@example.com")
    DEFAULT_PASSWORD = os.environ.get("DEFAULT_PASSWORD", "admin")

    DEFAULT_TENANT_LABEL = "Default Tenant"

    OAUTHLIB_RELAX_TOKEN_SCOPE = os.environ.get("OAUTHLIB_RELAX_TOKEN_SCOPE","1")
    os.environ['OAUTHLIB_RELAX_TOKEN_SCOPE'] = OAUTHLIB_RELAX_TOKEN_SCOPE
    GOOGLE_OAUTH_CLIENT_SECRET = os.environ.get("GOOGLE_OAUTH_CLIENT_SECRET")
    GOOGLE_OAUTH_CLIENT_ID = os.environ.get("GOOGLE_OAUTH_CLIENT_ID")

    UPLOAD_FOLDER = os.environ.get("UPLOAD_FOLDER", os.path.join(basedir, "app/files/reports"))
    FRAMEWORK_FOLDER = os.environ.get("FRAMEWORK_FOLDER", os.path.join(basedir, "app/files/base_controls"))
    POLICY_FOLDER = os.environ.get("POLICY_FOLDER", os.path.join(basedir, "app/files/base_policies"))

    EVIDENCE_FOLDER = os.environ.get("EVIDENCE_FOLDER", os.path.join(basedir, "app/files/evidence"))
    UPLOAD_EXTENSIONS = os.environ.get("UPLOAD_EXTENSIONS", [".jpg", ".png", ".pdf"])

    # integration import paths
    int_import_paths = os.environ.get("INTEGRATION_IMPORT_PATHS")
    if not int_import_paths:
        INTEGRATION_IMPORT_PATHS = ["app.integrations.base.tasks"]
    else:
        INTEGRATION_IMPORT_PATHS = int_import_paths.split(",")

    LAYOUT = {
      "header": True,
      "footer": False,
      "sidebar": True,
      "second-panel": True,
      "settings-panel": False,
      "sidebar-open":False,
      "y-padding":"py-2",
      "x-padding":"px-6 md:px-8 lg:px-10",
      "header-padding":"3",
      "container":False,
      "2xl-breakpoint":False,
      "xl-breakpoint":False,
      "lg-breakpoint":False,
      "hide-app-name":False,
      "header-border":True,
      "fixed-header":True
    }

    @staticmethod
    def init_app(app):
        pass

class ProductionConfig(Config, ):
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = os.environ.get('SQLALCHEMY_DATABASE_URI') or \
        "postgresql://db1:db1@postgres/db1"
    url = make_url(SQLALCHEMY_DATABASE_URI)
    POSTGRES_HOST = url.host
    POSTGRES_USER = url.username
    POSTGRES_PASSWORD = url.password
    POSTGRES_DB = url.database

class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('SQLALCHEMY_DATABASE_URI') or \
        "postgresql://db1:db1@postgres/db1"
    url = make_url(SQLALCHEMY_DATABASE_URI)
    POSTGRES_HOST = url.host
    POSTGRES_USER = url.username
    POSTGRES_PASSWORD = url.password
    POSTGRES_DB = url.database

class TestingConfig(Config):
    TESTING = True
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('SQLALCHEMY_DATABASE_URI') or \
        "postgresql://db1:db1@postgres/db1"
    url = make_url(SQLALCHEMY_DATABASE_URI)
    POSTGRES_HOST = url.host
    POSTGRES_USER = url.username
    POSTGRES_PASSWORD = url.password
    POSTGRES_DB = url.database
    WTF_CSRF_ENABLED = False

config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'default': ProductionConfig
}
