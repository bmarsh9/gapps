from app.utils.bg_worker import bg_app
from app.utils.misc import get_class_by_tablename
from app.utils.bg_helper import BgHelper
from app import db
from flask import current_app
from croniter import croniter
from datetime import datetime
import arrow
import os


@bg_app.periodic(cron="* * * * *")
@bg_app.task(name="scheduler", queue="scheduler")
async def scheduler(timestamp: int):
    tenant_id = "12345"
    Task = get_class_by_tablename("Task")
    tasks = Task.query.all()
    if not tasks:
        current_app.logger.debug("Database does not contain any periodic tasks... skipping")
        return True
    current_app.logger.debug(f"Found {len(tasks)} periodic tasks")
    for task in tasks:
        now = datetime.now()
        not_before = croniter(task.cron, task.last_run).get_next(datetime)
        if not task.last_run or now > not_before:
            current_app.logger.debug(f"Executing periodic task: {task.name}")
            await BgHelper().run_async_task()
            task.last_run = now
            task.not_before = croniter(task.cron, now).get_next(datetime)
            db.session.commit()
        else:
            current_app.logger.debug(f"Periodic task: {task.name} is not ready... skipping")
    return True
