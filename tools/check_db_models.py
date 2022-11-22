import sys
sys.path.append("..") # Adds higher directory to python modules path.
from app import create_app
from app.models import *

app = create_app(os.getenv('FLASK_CONFIG') or 'default')

def can_we_query_model():
    with app.app_context():
        try:
            User.query.count()
            return True
        except Exception as e:
            print(f"[ERROR] Traceback while querying db model: {e}")
            return False
    return False

print(f"[INFO] Checking if we can query the database models")
if not can_we_query_model():
    print(f"[ERROR] Unable to query the database models")
    exit(1)
print(f"[INFO] Successfully queried the database models")
exit(0)
