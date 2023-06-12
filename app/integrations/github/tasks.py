from app.utils.bg_worker import bg_app
from app.utils.misc import get_class_by_tablename
from app.utils.bg_helper import BgHelper
from app.models import Finding
from flask import current_app
from app import db
import arrow

# integration imports
from app.integrations.github.src.utils import github_test

@bg_app.task(name="github:get_users", queue="github")
def github_get_users(**kwargs):
    r = github_test()
    print(r)
    print(Finding.query.all())
    return True
