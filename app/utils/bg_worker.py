from config import config
from typing import Type
import procrastinate
import os


app = config.get(os.getenv('FLASK_CONFIG') or 'default')

connector_class: Type[procrastinate.BaseConnector]
connector_class = procrastinate.AiopgConnector

bg_app = procrastinate.App(
    connector=connector_class(
        host=app.POSTGRES_HOST,
        user=app.POSTGRES_USER,
        password=app.POSTGRES_PASSWORD
    ),
    import_paths=app.INTEGRATION_IMPORT_PATHS)
