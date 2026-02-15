"""Check database connectivity using SQLAlchemy (supports MySQL/MariaDB, PostgreSQL, SQLite)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text


def _build_uri():
    """Build database URI from env vars (same logic as config.py)."""
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


def can_we_connect():
    uri = _build_uri()
    try:
        engine = create_engine(uri)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        engine.dispose()
        return True
    except Exception as e:
        print(f"[ERROR] {e}".strip())
        return False


uri = _build_uri()
print(f"[INFO] Checking if we can connect to the database server: {uri}")
if not can_we_connect():
    print("[ERROR] Unable to connect to the database server")
    exit(1)
print("[INFO] Successfully connected to the database server")
exit(0)
