"""
Unified Settings API for managing SSO, Storage, LLM, SMTP, and encryption settings.
All sensitive values are encrypted at rest using the ConfigStore model.
"""

from flask import jsonify, request, current_app, abort
from . import api
from app import models, db
from flask_login import current_user
from app.utils.decorators import login_required
from app.utils.authorizer import Authorizer
from app.utils.encryption import encrypt_value, decrypt_value


# Settings categories and their keys
SETTINGS_SCHEMA = {
    "smtp": {
        "label": "Email / SMTP",
        "keys": [
            {"key": "MAIL_SERVER", "label": "SMTP Server", "type": "text", "sensitive": False},
            {"key": "MAIL_PORT", "label": "SMTP Port", "type": "number", "sensitive": False},
            {"key": "MAIL_USE_TLS", "label": "Use TLS", "type": "boolean", "sensitive": False},
            {"key": "MAIL_USERNAME", "label": "SMTP Username", "type": "text", "sensitive": False},
            {"key": "MAIL_PASSWORD", "label": "SMTP Password", "type": "password", "sensitive": True},
            {"key": "MAIL_DEFAULT_SENDER", "label": "Default Sender Email", "type": "email", "sensitive": False},
        ],
    },
    "sso": {
        "label": "Single Sign-On (SSO)",
        "keys": [
            {"key": "ENABLE_GOOGLE_AUTH", "label": "Enable Google SSO", "type": "boolean", "sensitive": False},
            {"key": "GOOGLE_CLIENT_ID", "label": "Google Client ID", "type": "text", "sensitive": False},
            {"key": "GOOGLE_CLIENT_SECRET", "label": "Google Client Secret", "type": "password", "sensitive": True},
            {"key": "ENABLE_MICROSOFT_AUTH", "label": "Enable Microsoft SSO", "type": "boolean", "sensitive": False},
            {"key": "MICROSOFT_CLIENT_ID", "label": "Microsoft Client ID", "type": "text", "sensitive": False},
            {"key": "MICROSOFT_CLIENT_SECRET", "label": "Microsoft Client Secret", "type": "password", "sensitive": True},
        ],
    },
    "storage": {
        "label": "File Storage",
        "keys": [
            {"key": "STORAGE_METHOD", "label": "Storage Provider", "type": "select",
             "options": ["local", "s3", "gcs", "azure"], "sensitive": False},
            {"key": "AWS_BUCKET", "label": "AWS S3 Bucket", "type": "text", "sensitive": False},
            {"key": "AWS_ACCESS_KEY", "label": "AWS Access Key", "type": "password", "sensitive": True},
            {"key": "AWS_SECRET_KEY", "label": "AWS Secret Key", "type": "password", "sensitive": True},
            {"key": "AWS_REGION", "label": "AWS Region", "type": "text", "sensitive": False},
            {"key": "GCS_BUCKET", "label": "GCS Bucket", "type": "text", "sensitive": False},
            {"key": "AZURE_STORAGE_ACCOUNT_NAME", "label": "Azure Account Name", "type": "text", "sensitive": False},
            {"key": "AZURE_STORAGE_ACCOUNT_KEY", "label": "Azure Account Key", "type": "password", "sensitive": True},
            {"key": "AZURE_STORAGE_CONTAINER", "label": "Azure Container", "type": "text", "sensitive": False},
            {"key": "AZURE_STORAGE_CONNECTION_STRING", "label": "Azure Connection String", "type": "password", "sensitive": True},
        ],
    },
    "llm": {
        "label": "AI / LLM",
        "keys": [
            {"key": "LLM_ENABLED", "label": "Enable AI Features", "type": "boolean", "sensitive": False},
            {"key": "LLM_PROVIDER", "label": "LLM Provider", "type": "select",
             "options": ["claude", "openai"], "sensitive": False},
            {"key": "ANTHROPIC_API_KEY", "label": "Anthropic (Claude) API Key", "type": "password", "sensitive": True},
            {"key": "ANTHROPIC_MODEL", "label": "Claude Model", "type": "text", "sensitive": False},
            {"key": "OPENAI_API_KEY", "label": "OpenAI API Key", "type": "password", "sensitive": True},
            {"key": "OPENAI_MODEL", "label": "OpenAI Model", "type": "text", "sensitive": False},
            {"key": "LLM_MAX_TOKENS", "label": "Max Tokens", "type": "number", "sensitive": False},
        ],
    },
    "mcp": {
        "label": "MCP Server",
        "keys": [
            {"key": "MCP_SERVER_URL", "label": "MCP Server URL", "type": "text", "sensitive": False},
            {"key": "MCP_SERVER_TOKEN", "label": "MCP Auth Token", "type": "password", "sensitive": True},
        ],
    },
    "general": {
        "label": "General",
        "keys": [
            {"key": "APP_NAME", "label": "Application Name", "type": "text", "sensitive": False},
            {"key": "APP_SUBTITLE", "label": "Application Subtitle", "type": "text", "sensitive": False},
            {"key": "HELP_EMAIL", "label": "Help Email", "type": "email", "sensitive": False},
            {"key": "ENABLE_SELF_REGISTRATION", "label": "Enable Self Registration", "type": "boolean", "sensitive": False},
        ],
    },
    "security": {
        "label": "Security",
        "keys": [
            {"key": "SESSION_TIMEOUT_MINUTES", "label": "Session Timeout (minutes)", "type": "number", "sensitive": False},
            {"key": "SESSION_WARNING_SECONDS", "label": "Timeout Warning (seconds before)", "type": "number", "sensitive": False},
            {"key": "FORCE_PASSWORD_CHANGE_DAYS", "label": "Force Password Change (days, 0=off)", "type": "number", "sensitive": False},
        ],
    },
}


def _get_config_value(key):
    """Get a setting value from ConfigStore, falling back to app config."""
    store = models.ConfigStore.query.filter_by(key=f"setting_{key}").first()
    if store:
        return store.value
    return current_app.config.get(key)


def _set_config_value(key, value, sensitive=False):
    """Set a setting value in ConfigStore, encrypting if sensitive."""
    store_key = f"setting_{key}"
    if sensitive and value:
        value = encrypt_value(str(value))

    store = models.ConfigStore.query.filter_by(key=store_key).first()
    if store:
        store.value = str(value) if value is not None else ""
    else:
        store = models.ConfigStore(key=store_key, value=str(value) if value is not None else "")
        db.session.add(store)
    db.session.commit()


def _mask_sensitive(value):
    """Mask sensitive values for display."""
    if not value:
        return ""
    s = str(value)
    if len(s) <= 8:
        return "*" * len(s)
    return s[:4] + "*" * (len(s) - 8) + s[-4:]


@api.route("/admin/settings", methods=["GET"])
@login_required
def get_settings():
    """Get all settings grouped by category."""
    Authorizer(current_user).can_user_manage_platform()

    result = {}
    for category, schema in SETTINGS_SCHEMA.items():
        category_data = {"label": schema["label"], "settings": []}
        for field in schema["keys"]:
            raw_value = _get_config_value(field["key"])
            display_value = raw_value

            # Decrypt if stored encrypted
            if field.get("sensitive") and raw_value:
                decrypted = decrypt_value(str(raw_value))
                display_value = _mask_sensitive(decrypted)
            elif field.get("sensitive"):
                display_value = ""

            # Convert booleans
            if field["type"] == "boolean":
                if isinstance(raw_value, str):
                    display_value = raw_value.lower() in ("true", "1", "yes", "on")
                else:
                    display_value = bool(raw_value)

            setting_data = {
                "key": field["key"],
                "label": field["label"],
                "type": field["type"],
                "value": display_value,
                "sensitive": field.get("sensitive", False),
                "is_set": bool(raw_value),
            }
            if "options" in field:
                setting_data["options"] = field["options"]
            category_data["settings"].append(setting_data)
        result[category] = category_data

    return jsonify(result)


@api.route("/admin/settings", methods=["PUT"])
@login_required
def update_settings():
    """Update settings. Expects JSON with category and key-value pairs."""
    Authorizer(current_user).can_user_manage_platform()
    data = request.get_json()

    category = data.get("category")
    settings = data.get("settings", {})

    if not category or category not in SETTINGS_SCHEMA:
        abort(400, "Invalid settings category")

    schema = SETTINGS_SCHEMA[category]
    valid_keys = {f["key"]: f for f in schema["keys"]}

    updated = []
    for key, value in settings.items():
        if key not in valid_keys:
            continue

        field = valid_keys[key]

        # Skip empty sensitive fields (means "don't change")
        if field.get("sensitive") and not value:
            continue

        _set_config_value(key, value, sensitive=field.get("sensitive", False))

        # Also update the running app config for non-sensitive values
        if not field.get("sensitive"):
            if field["type"] == "boolean":
                if isinstance(value, str):
                    current_app.config[key] = value.lower() in ("true", "1", "yes", "on")
                else:
                    current_app.config[key] = bool(value)
            elif field["type"] == "number":
                try:
                    current_app.config[key] = int(value)
                except (ValueError, TypeError):
                    current_app.config[key] = value
            else:
                current_app.config[key] = value

        updated.append(key)

    return jsonify({"message": "Settings updated", "updated": updated})


@api.route("/admin/settings/test-smtp", methods=["POST"])
@login_required
def test_smtp_settings():
    """Send a test email to verify SMTP settings."""
    Authorizer(current_user).can_user_manage_platform()
    from app.email import send_email
    from flask import render_template

    try:
        title = f"{current_app.config['APP_NAME']}: SMTP Test"
        content = "SMTP configuration test successful."
        response = send_email(
            title,
            recipients=[current_user.email],
            text_body=render_template(
                "email/basic_template.txt",
                title=title,
                content=content,
                button_link=current_app.config["HOST_NAME"],
            ),
            html_body=render_template(
                "email/basic_template.html",
                title=title,
                content=content,
                button_link=current_app.config["HOST_NAME"],
                button_label="Open Platform",
            ),
            async_send=False,
        )
        return jsonify({"message": "Test email sent", "success": response})
    except Exception as e:
        return jsonify({"message": str(e), "success": False}), 500


@api.route("/admin/settings/test-llm", methods=["POST"])
@login_required
def test_llm_settings():
    """Test LLM connection."""
    Authorizer(current_user).can_user_manage_platform()

    try:
        from app.utils.llm_provider import get_llm_provider

        provider = get_llm_provider(current_app.config)
        if not provider.is_configured():
            return jsonify({"message": "LLM provider not configured", "success": False})

        response = provider.chat(
            [{"role": "user", "content": "Say 'LLM connection successful' in exactly those words."}]
        )

        if "error" in response:
            return jsonify({"message": response["error"], "success": False})

        return jsonify({
            "message": response.get("message", "Connected"),
            "model": response.get("model", "unknown"),
            "success": True,
        })
    except Exception as e:
        return jsonify({"message": str(e), "success": False}), 500


@api.route("/admin/settings/test-storage", methods=["POST"])
@login_required
def test_storage_settings():
    """Test storage provider connection."""
    Authorizer(current_user).can_user_manage_platform()

    try:
        from app.utils.file_handler import FileStorageHandler

        provider = current_app.config.get("STORAGE_METHOD", "local")
        handler = FileStorageHandler(provider=provider)
        return jsonify({"message": f"Storage provider '{provider}' connected", "success": True})
    except Exception as e:
        return jsonify({"message": str(e), "success": False}), 500


@api.route("/admin/settings/schema", methods=["GET"])
@login_required
def get_settings_schema():
    """Get the settings schema for the frontend."""
    Authorizer(current_user).can_user_manage_platform()
    return jsonify(SETTINGS_SCHEMA)


@api.route("/session-timeout", methods=["GET"])
@login_required
def get_session_timeout():
    """Get session timeout config for the frontend idle timer."""
    timeout = _get_config_value("SESSION_TIMEOUT_MINUTES")
    warning = _get_config_value("SESSION_WARNING_SECONDS")
    try:
        timeout = int(timeout) if timeout else current_app.config.get("SESSION_TIMEOUT_MINUTES", 10)
    except (ValueError, TypeError):
        timeout = 10
    try:
        warning = int(warning) if warning else current_app.config.get("SESSION_WARNING_SECONDS", 60)
    except (ValueError, TypeError):
        warning = 60
    return jsonify({"timeout_minutes": timeout, "warning_seconds": warning})
