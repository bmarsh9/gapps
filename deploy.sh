#!/bin/bash
# =============================================================================
# Masri Digital Compliance Platform - Deploy Script
# =============================================================================
# Runs automatically after `git pull` (via post-merge hook) or manually.
# Installs any new dependencies, runs migrations, and restarts the app.
#
# Usage:
#   bash deploy.sh          # standard deploy
#   MIGRATE=yes bash deploy.sh  # deploy + run database migrations
# =============================================================================

set -e

APP_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="$APP_DIR/venv"
LOG_PREFIX="[deploy]"

echo "$LOG_PREFIX Starting deployment..."
echo "$LOG_PREFIX App directory: $APP_DIR"

# --- Activate virtualenv ---
if [ -d "$VENV_DIR" ]; then
    source "$VENV_DIR/bin/activate"
    echo "$LOG_PREFIX Activated virtualenv"
else
    echo "$LOG_PREFIX [WARNING] No virtualenv found at $VENV_DIR"
    echo "$LOG_PREFIX Run cloudways_setup.sh first"
    exit 1
fi

# --- Install/update dependencies ---
echo "$LOG_PREFIX Installing dependencies..."
pip install -r "$APP_DIR/requirements.txt" -q

# --- Ensure directories exist ---
mkdir -p "$APP_DIR/app/files/evidence" "$APP_DIR/app/files/reports"

# --- Check database connection ---
echo "$LOG_PREFIX Checking database connection..."
if ! python3 "$APP_DIR/tools/check_db_connection.py"; then
    echo "$LOG_PREFIX [ERROR] Cannot connect to database. Check your .env file."
    exit 1
fi

# --- Run migrations if requested ---
if [ "$MIGRATE" == "yes" ]; then
    echo "$LOG_PREFIX Running database migrations..."
    cd "$APP_DIR"
    python3 manage.py db migrate 2>/dev/null || echo "$LOG_PREFIX No new migrations"
    python3 manage.py db stamp head 2>/dev/null || true
    python3 manage.py db upgrade 2>/dev/null || echo "$LOG_PREFIX Upgrade complete (or no changes)"
fi

# --- Restart application via Supervisor ---
echo "$LOG_PREFIX Restarting application..."
if command -v supervisorctl &>/dev/null; then
    sudo supervisorctl restart masri-compliance 2>/dev/null && \
        echo "$LOG_PREFIX Application restarted via Supervisor" || \
        echo "$LOG_PREFIX [WARNING] Supervisor restart failed - you may need to start manually"
else
    echo "$LOG_PREFIX [INFO] Supervisor not found. Restart the app manually."
fi

echo "$LOG_PREFIX Deployment complete!"
