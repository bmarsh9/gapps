# Always import these 3 lines
from app.integrations.utils.decorators import task
from app.integrations.utils import shared
from flask import current_app

# Add imports for the integration
from app.integrations.demo.src.utils import demo_test


@task(name="demo:get_users", queue="demo")
def demo_get_users(task, lockers, *args, **kwargs):
    data = demo_test()
    result = task.save_results(data, version="1.1.1")
    # See /app/integrations/DEVELOPMENT.md for more information
    return True
