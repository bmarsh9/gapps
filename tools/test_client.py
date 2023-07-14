import sys
sys.path.append("..") # Adds higher directory to python modules path.
from app import create_app
from app.models import *
import os,time
import json

app = create_app(os.getenv('FLASK_CONFIG') or 'default')

#from app.utils.bg_worker import bg_app

def test():
    with app.app_context():
        pass

test()
