from app.models import Task
from app.utils.bg_worker import bg_app
import logging


def task(*args, **kwargs):
    def wrap(func):
        def new_func(*job_args, **job_kwargs):
            job_kwargs = {**job_kwargs, **kwargs}

            """
            add the Task object and the lockers that
            the task has access to
            """
            # testing a task
            if job_kwargs["id"] == "test":
                task = None
                lockers = []
                lock = "test"
            else:
                task = Task.query.get(job_kwargs["id"])
                lockers = task.integration.get_lockers()
                lock = task.get_lock()

            logging.info(f"Starting task: {lock}")
            result = func(task, lockers, *job_args, **job_kwargs)
            logging.info(f"Task complete: {lock}")
            return result
        return bg_app.task(*args, **kwargs)(new_func)
    return wrap
