from app.integrations.utils.decorators import task
from app.integrations.utils import shared
from flask import current_app
from app.models import Finding, Task
from app import db

# integration imports
from app.integrations.github.src.utils import github_test

@task(name="github:get_users", queue="github")
def github_get_users(task, lockers, *args, **kwargs):
    data = github_test()
    result = task.save_results(data, version="1.1.1", update=True)
    #latest = shared.get_latest_result(task.id)
    return True
