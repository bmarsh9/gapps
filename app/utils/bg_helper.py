from app.utils.bg_worker import bg_app
from flask import current_app
from app.models import *
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

    def list_jobs(self, id=None, name=None, status=None, queue=None, exclude_scheduler=False):
        '''
        status = ["failed","todo","doing","succeeded"]
        queue = ID of the tenant
        '''
        jobs = []
        for job in self.manager.list_jobs(id=id,task=name,status=status,queue=queue):
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

            try:
                if tenant := Tenant.query.get(job["queue"]):
                    job["context"]["tenant"] = tenant.name
                    job["context"]["tenant_id"] = tenant.id
                    job["context"]["tenant_uuid"] = tenant.uuid
            except:
                pass
            jobs.append(job)
        return jobs

    def list_tasks(self):
        return [x for x in self.manager.list_tasks()]

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

                try:
                    if tenant := Tenant.query.get(job["queue"]):
                        job["context"]["tenant"] = tenant.name
                        job["context"]["tenant_id"] = tenant.id
                        job["context"]["tenant_uuid"] = tenant.uuid
                except:
                    pass
                job["events"] = [{"status":x["type"],"timestamp":x["at"],"ts_humanize":arrow.get(x["at"]).humanize()} for x in results]
            return job
        except Exception as e:
            current_app.logger.error(e)
            current_app.db.session.rollback()
        finally:
            current_app.db.session.close()
        return job

    def delete_old_jobs(self, hours=8, include_error=False):
        return self.manager.delete_old_jobs(
            nb_hours=int(hours),
            include_error=include_error
        )

    async def run_async_task(self, name=None, tenant_id=1):
        """
        start async task
        returns job ID
        """
        job_id = await bg_app.configure_task(name='add-sum',lock="my lock",schedule_in={"seconds":10},queue="test").defer_async(a=5,b=7)
#        current_app.logger.info(f"got {job_id}")

    def run_task(self, name=None, tenant_id=1):
#        bg_app.configure_task(name='add-sum',lock="my lock",schedule_in={"seconds":10},queue="test").defer(a=5,b=7)
        bg_app.configure_task(name='github-get-users',lock="my lock",schedule_in={"seconds":10},queue="test").defer()
