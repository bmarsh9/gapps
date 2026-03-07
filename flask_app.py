from app import create_app
import os

# If FLASK_ENV=development prefer the development config which now uses SQLite by default
env_config = os.getenv("FLASK_CONFIG")
if not env_config and os.getenv("FLASK_ENV") == "development":
    env_config = "development"

app = create_app(env_config or "default")

if __name__ == "__main__":
    app.run(use_reloader=False)
