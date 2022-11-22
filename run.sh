#!/bin/bash

# Script performs the following checks to start the service
#  - check if we can connect to the server
#  - check if we can query the database models
#  - if we cant query the models and SETUP_DB is set, it will create the db models
# Use SKIP_INI_CHECKS to start the service without checks

if [ "$SKIP_INI_CHECKS" == "yes" ]; then
  echo "[INFO] Skipping the health checks for database"
  echo "[INFO] Starting the server"
  gunicorn --bind 0.0.0.0:5000 flask_app:app --access-logfile '-' --error-logfile "-"
else
  # check if we can connect to the db
  until python3 tools/check_db_connection.py
  do
    echo "[INFO] Waiting for 3 seconds"
    sleep 3
  done

  # check and setup the database models
  if cd tools;python3 check_db_models.py;cd ..; then
    if [ "$SETUP_DB" == "yes" ]; then
      echo "[INFO] Setting up the database models"
      python3 manage.py init_db
    fi
    echo "[INFO] Starting the server"
    # uwsgi
    #uwsgi --ini start.ini

    # gunicorn
    gunicorn --bind 0.0.0.0:5000 flask_app:app --access-logfile '-' --error-logfile "-"
  fi
fi
