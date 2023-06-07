from app import create_app
from app.models import *
import os,time
import logging
import json
from app.utils.bg_worker import bg_app

app = create_app(os.getenv('FLASK_CONFIG') or 'default')

logging.basicConfig(level="DEBUG")

'''
# Help
https://github.com/procrastinate-org/procrastinate/issues/438

# Manual execution of worker
procrastinate --verbose --app=app.utils.bg_worker.bg_app worker

'''

class BgWorker:
    '''
    from app.utils.bg_worker import bg_app
    with bg_app.open():
        r = BgWorker().list_jobs(status="failed")
        print(json.dumps(r,indent=4,default=str))
    '''
    def __init__(self):
        self.manager = bg_app.job_manager

    def summary(self):
        return {
            "jobs":self.list_jobs(),
            "tasks":self.list_tasks(),
            "queues":self.list_queues()
        }

    def list_jobs(self, status=None):
        '''
        status = ["failed","todo","doing","succeeded"]
        '''
        jobs = [x.asdict() for x in self.manager.list_jobs()]
        if status:
            jobs = [x for x in jobs if x["status"] == status]
        return jobs

    def list_tasks(self):
        return [x for x in self.manager.list_tasks()]

    def list_queues(self):
        return [x for x in self.manager.list_queues()]

    def get_job_by_id(self, id):
        job = [x for x in self.list_jobs() if x["id"] == id]
        if job:
            return job[0]
        return None

    def delete_old_jobs(self, hours=8, include_error=False):
        return self.manager.delete_old_jobs(nb_hours=int(hours),include_error=include_error)


with bg_app.open():
  worker = BgWorker()
  r = worker.list_jobs(status="succeeded")
  print(json.dumps(r,indent=4,default=str))
