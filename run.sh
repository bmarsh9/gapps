#!/bin/bash

# Script performs the following checks to start the service
#  - check if we can connect to the server
#  - check if we can query the database models
#  - if we cant query the models, the database will be created
#  - if we CAN query the models and RESET_DB=yes, it will recreate the db
# Use SKIP_INI_CHECKS to start the service without checks

check_migration() {
  if [ "$INIT_MIGRATE" == "yes" ]; then
    echo "[INFO] Setting up migrations"
    python3 manage.py db init
  fi
  if [ "$MIGRATE" == "yes" ]; then
    echo "[INFO] Performing database migration"
    python3 manage.py db migrate
    python3 manage.py db stamp head
    python3 manage.py db migrate
    python3 manage.py db upgrade
  fi
}

if [ "$AS_WORKER" == "yes" ]; then
  echo "[INFO] Running as a worker. Trying to start..."
  if python3 tools/check_db_models.py; then
    export PYTHONPATH=.
    procrastinate --app=app.utils.bg_worker.bg_app schema --apply
    echo "[INFO] Worker is ready. Starting..."
    python3 run_worker.py
  else
    echo "[ERROR] Unable to query the database models. Worker is exiting..."
    exit 1
  fi
else
  if [ "$SKIP_INI_CHECKS" == "yes" ]; then
    echo "[INFO] Skipping the health checks for database"
    echo "[INFO] Starting the server with ${GUNICORN_WORKERS:-1} workers"
    gunicorn --bind 0.0.0.0:5000 flask_app:app --access-logfile '-' --error-logfile "-" --workers="${GUNICORN_WORKERS:-1}" --threads="${GUNICORN_THREADS:-0}" --timeout="${GUNICORN_TIMEOUT:-60}" --keep-alive="${GUNICORN_KEEP_ALIVE:-60}"
  else
    # check if we can connect to the db
    until python3 tools/check_db_connection.py
    do
      echo "[INFO] Waiting for 3 seconds"
      sleep 3
    done

    # check and/or set up the database models
    if python3 tools/check_db_models.py; then
      if [ "$RESET_DB" == "yes" ]; then
        echo "[WARNING] Recreating the database models - this will delete all data in the database (RESET_DB env is set). Waiting for 10 seconds before proceeding (Cntrl-C to stop)."
        sleep 10
        python3 manage.py init_db
      fi
    else
      echo "[INFO] Setting up the database models"
      python3 manage.py init_db
    fi

    # check for migration
    check_migration

    if [ "$ONESHOT" == "yes" ]; then
      exit
    fi
    # start the app with gunicorn
    echo "[INFO] Starting the server with ${GUNICORN_WORKERS:-1} workers"
    gunicorn --bind 0.0.0.0:5000 flask_app:app --access-logfile '-' --error-logfile "-" --workers="${GUNICORN_WORKERS:-1}" --threads="${GUNICORN_THREADS:-0}" --timeout="${GUNICORN_TIMEOUT:-60}" --keep-alive="${GUNICORN_KEEP_ALIVE:-60}"
  fi
fi
