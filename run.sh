#!/bin/bash

# Entrypoint script for the Flask app
# Performs checks before starting the service:
#  - Ensures database connection is available
#  - Verifies or initializes database models
#  - Runs database migrations if required
#  - Resets the database if RESET_DB=yes
#  - Can skip all checks if SKIP_INI_CHECKS=yes

set -e  # Exit script immediately on failure

PORT=${PORT:-5000}
GUNICORN_WORKERS=${GUNICORN_WORKERS:-1}
GUNICORN_THREADS=${GUNICORN_THREADS:-0}
GUNICORN_TIMEOUT=${GUNICORN_TIMEOUT:-60}
GUNICORN_KEEP_ALIVE=${GUNICORN_KEEP_ALIVE:-60}

start_server() {
    echo "[INFO] Starting the server with $GUNICORN_WORKERS workers"
    exec gunicorn --bind "0.0.0.0:$PORT" \
        flask_app:app \
        --access-logfile '-' --error-logfile '-' \
        --workers="$GUNICORN_WORKERS" \
        --threads="$GUNICORN_THREADS" \
        --timeout="$GUNICORN_TIMEOUT" \
        --keep-alive="$GUNICORN_KEEP_ALIVE"
}

check_migration() {
    if [ "$INIT_MIGRATE" == "yes" ]; then
        echo "[INFO] Initializing database migrations"
        python3 manage.py db init || echo "[WARNING] Migrations already initialized"
    fi

    if [ "$MIGRATE" == "yes" ]; then
        echo "[INFO] Running database migrations"
        python3 manage.py db migrate && python3 manage.py db stamp head
        python3 manage.py db upgrade
    fi
}

if [ "$SKIP_INI_CHECKS" == "yes" ]; then
    echo "[INFO] Skipping database health checks"
    start_server
else
    echo "[INFO] Checking database connectivity..."
    until python3 tools/check_db_connection.py; do
        echo "[INFO] Database unavailable, retrying in 3 seconds..."
        sleep 3
    done
    echo "[INFO] Database connection established"

    echo "[INFO] Checking database models..."
    if python3 tools/check_db_models.py; then
        if [ "$RESET_DB" == "yes" ]; then
            echo "[WARNING] Resetting the database (this will erase all data)."
            echo "[WARNING] Waiting 10 seconds before proceeding... (Ctrl-C to abort)"
            sleep 10
            python3 manage.py init_db
        fi
    else
        echo "[INFO] Initializing database models"
        python3 manage.py init_db
    fi

    check_migration

    if [ "$ONESHOT" == "yes" ]; then
        echo "[INFO] ONESHOT mode enabled. Exiting."
        exit 0
    fi

    start_server
fi
