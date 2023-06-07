from app import create_app
from app.models import *
import os,time
import logging
import json
from app.utils.bg_worker import bg_app

app = create_app(os.getenv('FLASK_CONFIG') or 'default')

logging.basicConfig(level="DEBUG")

'''
# Help
https://github.com/procrastinate-org/procrastinate/issues/438

# Manual execution of worker
procrastinate --verbose --app=app.utils.bg_worker.bg_app worker

'''

#https://procrastinate.readthedocs.io/en/stable/reference.html#procrastinate.App.run_worker

with bg_app.open():
    bg_app.run_worker(concurrency=1)
