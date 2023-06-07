from app import create_app
from app.utils.bg_worker import bg_app
import logging
import os

app = create_app(os.getenv('FLASK_CONFIG') or 'default')
logging.basicConfig(level=app.config["WORKER_LOG_LEVEL"] or app.config["LOG_LEVEL"])

with bg_app.open():
    options = {
        "name":os.environ.get("WORKER_NAME","worker"),
        "concurrency":int(os.environ.get("WORKER_CONCURRENCY", 1)),
    }
    if os.environ.get("WORKER_QUEUES"):
        options["queues"] = os.environ.get("WORKER_QUEUES").split(",")
    if os.environ.get("WORKER_WAIT"):
        options["wait"] = True

    with app.app_context():
        #app.db.session.rollback()
        bg_app.run_worker(**options)
