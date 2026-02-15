from datetime import timedelta
from sqlalchemy.engine.url import make_url
from urllib.parse import urlparse
import os


basedir = os.path.abspath(os.path.dirname(__file__))


def parse_url_with_defaults(url, default_scheme="http", default_port=5000):
    # Ensure the URL has a scheme, add the default if missing
    if "://" not in url:
        url = f"{default_scheme}://{url}"

    # Parse the URL
    parsed_url = urlparse(url)

    # Extract components with defaults
    scheme = parsed_url.scheme or default_scheme
    host_name = parsed_url.hostname or "localhost"

    # If scheme is https, default port to 443
    if scheme == "https" and parsed_url.port is None:
        port = 443
    else:
        port = parsed_url.port or default_port

    # Construct the full URL
    if (scheme == "http" and port == 80) or (scheme == "https" and port == 443):
        full_url = f"{scheme}://{host_name}/"
    else:
        full_url = f"{scheme}://{host_name}:{port}/"

    return scheme, host_name, port, full_url


class Config:
    APP_NAME = os.environ.get("APP_NAME", "Masri Digital Compliance")
    APP_SUBTITLE = os.environ.get("APP_SUBTITLE", "GRC Platform")
    CR_YEAR = os.environ.get("CR_YEAR", "2026")
    VERSION = os.environ.get("VERSION", "2.0.0")

    scheme, host_name, port, full_url = parse_url_with_defaults(
        os.environ.get("HOST_NAME", "localhost")
    )
    HOST_NAME = full_url
    SCHEME = scheme
    PORT = port

    LOG_TYPE = os.environ.get("LOG_TYPE", "stream")
    LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")
    ENABLE_GCP_LOGGING = os.environ.get("ENABLE_GCP_LOGGING", "false").lower() == "true"

    SECRET_KEY = os.environ.get("SECRET_KEY", "change_secret_key")
    ENCRYPTION_KEY = os.environ.get("ENCRYPTION_KEY", "")

    # Session / auto sign-out (default 10 minutes)
    SESSION_TIMEOUT_MINUTES = int(os.environ.get("SESSION_TIMEOUT_MINUTES", 10))
    SESSION_WARNING_SECONDS = int(os.environ.get("SESSION_WARNING_SECONDS", 60))
    FORCE_PASSWORD_CHANGE_DAYS = int(os.environ.get("FORCE_PASSWORD_CHANGE_DAYS", 0))
    PERMANENT_SESSION_LIFETIME = timedelta(
        minutes=int(os.environ.get("SESSION_TIMEOUT_MINUTES", 10))
    )
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"

    SQLALCHEMY_COMMIT_ON_TEARDOWN = True
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_RECORD_QUERIES = False
    MAIL_SERVER = os.environ.get("MAIL_SERVER", "smtp.googlemail.com")
    MAIL_PORT = int(os.environ.get("MAIL_PORT", 587))
    MAIL_USE_TLS = os.environ.get("MAIL_USE_TLS", "true").lower() == "true"
    MAIL_DEBUG = os.environ.get("MAIL_DEBUG", "false").lower() == "true"
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME")
    MAIL_DEFAULT_SENDER = os.environ.get("MAIL_DEFAULT_SENDER")
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD")
    BASE_DIR = basedir

    # Only allowed if email is configured as well - see "is_self_registration_enabled"
    ENABLE_SELF_REGISTRATION = (
        os.environ.get("ENABLE_SELF_REGISTRATION", "false").lower() == "true"
    )
    DOC_LINK = os.environ.get("DOC_LINK", "https://masridigital.com")
    DEFAULT_EMAIL = os.environ.get("DEFAULT_EMAIL", "admin@example.com")
    DEFAULT_PASSWORD = os.environ.get("DEFAULT_PASSWORD", "admin1234567")
    HELP_EMAIL = os.environ.get("HELP_EMAIL", DEFAULT_EMAIL)

    ENABLE_GOOGLE_AUTH = os.environ.get("ENABLE_GOOGLE_AUTH", "false").lower() == "true"
    ENABLE_MICROSOFT_AUTH = (
        os.environ.get("ENABLE_MICROSOFT_AUTH", "false").lower() == "true"
    )

    GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID")
    GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET")

    MICROSOFT_CLIENT_ID = os.environ.get("MICROSOFT_CLIENT_ID")
    MICROSOFT_CLIENT_SECRET = os.environ.get("MICROSOFT_CLIENT_SECRET")

    UPLOAD_FOLDER = os.environ.get(
        "UPLOAD_FOLDER", os.path.join(basedir, "app/files/reports")
    )
    FRAMEWORK_FOLDER = os.environ.get(
        "FRAMEWORK_FOLDER", os.path.join(basedir, "app/files/base_controls")
    )
    POLICY_FOLDER = os.environ.get(
        "POLICY_FOLDER", os.path.join(basedir, "app/files/base_policies")
    )
    EVIDENCE_FOLDER = os.environ.get(
        "EVIDENCE_FOLDER", os.path.join(basedir, "app/files/evidence")
    )
    UPLOAD_EXTENSIONS = os.environ.get(
        "UPLOAD_EXTENSIONS", [".csv", ".jpg", ".png", ".pdf"]
    )

    STORAGE_PROVIDERS = ["local", "s3", "gcs", "azure"]

    # GCS storage backend
    STORAGE_METHOD = os.environ.get("STORAGE_METHOD", "local")
    GCS_BUCKET = os.environ.get("GCS_BUCKET")
    GOOGLE_CLOUD_PROJECT = os.environ.get("GOOGLE_CLOUD_PROJECT")
    GOOGLE_APPLICATION_CREDENTIALS = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")

    # AWS storage backend
    AWS_BUCKET = os.environ.get("AWS_BUCKET")
    AWS_ACCESS_KEY = os.environ.get("AWS_ACCESS_KEY")
    AWS_SECRET_KEY = os.environ.get("AWS_SECRET_KEY")
    AWS_REGION = os.environ.get("AWS_REGION")

    # Azure Blob Storage backend
    AZURE_STORAGE_CONNECTION_STRING = os.environ.get("AZURE_STORAGE_CONNECTION_STRING")
    AZURE_STORAGE_ACCOUNT_NAME = os.environ.get("AZURE_STORAGE_ACCOUNT_NAME")
    AZURE_STORAGE_ACCOUNT_KEY = os.environ.get("AZURE_STORAGE_ACCOUNT_KEY")
    AZURE_STORAGE_CONTAINER = os.environ.get("AZURE_STORAGE_CONTAINER")

    # AI / LLM Configuration
    LLM_ENABLED = os.environ.get("LLM_ENABLED", "false").lower() == "true"
    LLM_NAME = os.environ.get("LLM_NAME")
    LLM_TOKEN = os.environ.get("LLM_TOKEN")
    LLM_PROVIDER = os.environ.get("LLM_PROVIDER", "")  # "claude" or "openai"
    LLM_MAX_TOKENS = int(os.environ.get("LLM_MAX_TOKENS", 2048))

    # Anthropic Claude
    ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
    ANTHROPIC_MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-20250514")

    # OpenAI
    OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
    OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o")

    # MCP Server
    MCP_SERVER_URL = os.environ.get("MCP_SERVER_URL")
    MCP_SERVER_TOKEN = os.environ.get("MCP_SERVER_TOKEN")

    # Integrations
    INTEGRATIONS_BASE_URL = os.environ.get("INTEGRATIONS_BASE_URL", "http://localhost:8080")
    INTEGRATIONS_TOKEN = os.environ.get("INTEGRATIONS_TOKEN", "changeme")

    # Expose certain env vars in front end (DO NOT PLACE SENSITIVE VARS)
    # Use csv (e.g. storage_method,gcs_bucket)
    DEBUG_ENV_VARS = (
        os.environ.get("DEBUG_ENV_VARS", "STORAGE_METHOD").upper().split(",")
    )

    PLAYGROUND_CSS = os.environ.get("PLAYGROUND_CSS")
    LAYOUT = {
        "header": True,
        "footer": False,
        "sidebar": True,
        "second-panel": True,
        "settings-panel": False,
        "sidebar-open": False,
        "y-padding": "py-2 pt-3",
        "x-padding": "px-6 md:px-8 lg:px-10",
        "header-padding": "3",
        "container": False,
        "2xl-breakpoint": False,
        "xl-breakpoint": False,
        "lg-breakpoint": False,
        "hide-app-name": False,
        "header-border": True,
        "fixed-header": True,
    }

    """
    Do not store sensitive data in feature flags.
    Frontend uses $store.currentUser.featureFlags.flag_name
    Backend uses current_app.config["FEATURE_FLAGS"][flag_name]
    # e.g. feature_flag_name=true
    """
    FEATURE_FLAGS = {
        key[len("feature_") :].lower(): value.lower() in ("1", "true", "yes", "on")
        for key, value in os.environ.items()
        if key.lower().startswith("feature_")
    }

    @staticmethod
    def init_app(app):
        pass


def _default_db_uri():
    """Build default database URI from individual env vars or use the full URI."""
    uri = os.environ.get("SQLALCHEMY_DATABASE_URI")
    if uri:
        return uri
    db_engine = os.environ.get("DB_ENGINE", "mysql+pymysql")
    db_user = os.environ.get("DB_USER", "db1")
    db_password = os.environ.get("DB_PASSWORD", "db1")
    db_host = os.environ.get("DB_HOST", "mariadb")
    db_port = os.environ.get("DB_PORT", "3306")
    db_name = os.environ.get("DB_NAME", "db1")
    return f"{db_engine}://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}?charset=utf8mb4"


class ProductionConfig(Config):
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = _default_db_uri()
    url = make_url(SQLALCHEMY_DATABASE_URI)
    DB_HOST = url.host
    DB_USER = url.username
    DB_PASSWORD = url.password
    DB_NAME = url.database


class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = _default_db_uri()
    url = make_url(SQLALCHEMY_DATABASE_URI)
    DB_HOST = url.host
    DB_USER = url.username
    DB_PASSWORD = url.password
    DB_NAME = url.database


class TestingConfig(Config):
    TESTING = True
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = _default_db_uri()
    url = make_url(SQLALCHEMY_DATABASE_URI)
    DB_HOST = url.host
    DB_USER = url.username
    DB_PASSWORD = url.password
    DB_NAME = url.database
    WTF_CSRF_ENABLED = False


config = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "default": ProductionConfig,
}
