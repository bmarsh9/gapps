from app import create_app
from app.utils.bg_worker import bg_app
import os


app = create_app(os.getenv('FLASK_CONFIG') or 'default')

with bg_app.open():
    options = {
        "name":app.config.get("WORKER_NAME","worker"),
        "concurrency":int(app.config.get("WORKER_CONCURRENCY", 1)),
    }
    if app.config.get("WORKER_QUEUES"):
        options["queues"] = app.config.get("WORKER_QUEUES").split(",")
    if app.config.get("WORKER_WAIT"):
        options["wait"] = True

    with app.app_context():
        bg_app.run_worker(**options)
