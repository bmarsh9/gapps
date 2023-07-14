from app.utils.bg_worker import bg_app
from flask import current_app
from app import models
import arrow


class BgHelper:
    '''
    from app.utils.bg_worker import bg_app
    with bg_app.open():
        r = BgWorker().list_jobs(status="failed")
        print(json.dumps(r,indent=4,default=str))

    # query database
    current_app.db.session.execute("select * from procrastinate_events")
    '''
    def __init__(self):
        self.manager = bg_app.job_manager

    def summary(self):
        return {
            "jobs":self.list_jobs(),
            "tasks":self.list_tasks(),
            "queues":self.list_queues()
        }

    def rows_as_dicts(self, cursor):
        """convert tuple result to dict with cursor"""
        col_names = [i[0] for i in cursor.description]
        return [dict(zip(col_names, row)) for row in cursor]

    def resolve_queue_to_tenant(self, id):
        try:
            if id.isdigit():
                return models.Tenant.query.get(id)
        except Exception as e:
            return None

    def list_jobs(self, id=None, name=None, status=None, queue=None, lock=None, exclude_scheduler=False):
        '''
        status = ["failed","todo","doing","succeeded"]
        queue = ID of the tenant
        '''
        jobs = []
        for job in self.manager.list_jobs(id=id,task=name,status=status,queue=queue,lock=lock):
            job = job.asdict()
            job["context"] = {}
            '''
            option for filter to exclude the periodic scheduler b/c it can spam the logs
            '''
            if exclude_scheduler and job["task_name"].lower() == "scheduler":
                continue

            if job.get("created_at"):
                job["context"]["created_at_humanize"] = arrow.get(job["created_at"]).humanize()
            if job["scheduled_at"]:
                job["context"]["scheduled_at_humanize"] = arrow.get(job["scheduled_at"]).humanize()

            if tenant := self.resolve_queue_to_tenant(job["queue"]):
                job["context"]["tenant"] = tenant.name
                job["context"]["tenant_id"] = tenant.id
                job["context"]["tenant_uuid"] = tenant.uuid
            jobs.append(job)
        return jobs

    def list_tasks(self, name=None):
        tasks = self.manager.list_tasks()
        if name:
            for task in tasks:
                if task.get("name") == name.lower():
                    return task
            return {}
        return tasks

    def list_queues(self):
        return [x for x in self.manager.list_queues()]

    def get_job_by_id(self, id, first=False):
        """
        first record is the most recent one
        """
        query = "select * from procrastinate_jobs left join procrastinate_events on procrastinate_jobs.id = procrastinate_events.job_id where job_id = :id order by procrastinate_events.id desc"
        try:
            job = {}
            result = current_app.db.session.execute(query, {"id":id})
            current_app.db.session.commit()
            results = self.rows_as_dicts(result.cursor)
            if results:
                job = results[0]
                job["context"] = {}
                if job["scheduled_at"]:
                    job["context"]["scheduled_at_humanize"] = arrow.get(job["scheduled_at"]).humanize()

                if tenant := self.resolve_queue_to_tenant(job["queue"]):
                    job["context"]["tenant"] = tenant.name
                    job["context"]["tenant_id"] = tenant.id
                    job["context"]["tenant_uuid"] = tenant.uuid
                job["events"] = [{"status":x["type"],"timestamp":x["at"],"ts_humanize":arrow.get(x["at"]).humanize()} for x in results]
            return job
        except Exception as e:
            current_app.logger.error(e)
            current_app.db.session.rollback()
        finally:
            current_app.db.session.close()
        return job

    def delete_old_jobs(self, hours=8, include_error=False, queue=None):
        filter = {
            "nb_hours":int(hours),
            "include_error":include_error
        }
        if queue:
            filter["queue"] = queue
        return self.manager.delete_old_jobs(**filter)

    async def run_async_task(self, task, lock=None, seconds=10):
        """
        start async task
        returns task ID
        """
        if not lock:
            lock = task.get_lock()
        task_id = await bg_app.configure_task(
            name=f"{task.integration.name}:{task.name}",
            lock=lock,
            queueing_lock=lock,
            schedule_in={"seconds":seconds},
            queue=task.queue).defer_async(id=task.id)
        current_app.logger.info(f"Placed {lock} in the queue:{task.queue}. Task_ID:{task_id} scheduled in {seconds} seconds.")

    def test_task(self, name):
        current_app.logger.info(f"Trying to run task:{name} on queue: test")
        with bg_app.open():
            return bg_app.configure_task(name=name, lock="test", schedule_in={"seconds":2}, queue="test").defer(id="test")

