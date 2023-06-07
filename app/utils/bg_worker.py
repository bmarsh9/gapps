from typing import Type
import procrastinate
import os


connector_class: Type[procrastinate.BaseConnector]
connector_class = procrastinate.AiopgConnector

import_paths = ["app.integrations.base.tasks","app.integrations.github.tasks"]

bg_app = procrastinate.App(
    connector=connector_class(
        host=os.environ.get("POSTGRES_HOST"),
        user=os.environ.get("POSTGRES_USER"),
        password=os.environ.get("POSTGRES_PASSWORD")
    ),
    import_paths=import_paths)
