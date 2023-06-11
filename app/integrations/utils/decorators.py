from app.utils.bg_worker import bg_app
import logging


def task(*args, **kwargs):
    def wrap(func):
        def new_func(*job_args, **job_kwargs):
            logging.debug("starting")
            result = func(*job_args, **job_kwargs)
            logging.debug("ending")
            return result
        return bg_app.task(*args, **kwargs)(new_func)
    return wrap
