## Docs on background worker

#### Details  

##### Overview
Workers are spun up to run the background jobs. An single execution of a job is called a task. So you can (and will) have multiple jobs but everytime a job executes, it is called a task. Tasks are placed in queues and picked up by the workers. Tasks are namespaced (e.g. they have a `tenant_id` foreign key) by the tenant. By default, the task is placed in the queue of the the tenant ID. This will allow you to start workers on specific queues. So you could have 5 workers looking at the queue for Tenant 1 and 2 workers looking at the queue for Tenant 2.  

There is a default job called `scheduler` that can be found at `app/integrations/base/tasks.py`. The purpose of this job is to read the `Task` table and periodically place jobs into their respective queues (based on tenant_id). It does not execute the jobs but just defers (schedules them) based on the details of the jobs. So you could start a worker on the scheduler queue (WORKER_QUEUES=scheduler) and jobs would be created as `todo` but they would not be executed until you started another worker for the specific queues. 

##### Docs  
[docs are here](https://github.com/procrastinate-org/procrastinate)

##### Setup  
```
docker-compose up -d postgres
export AS_WORKER=yes
source venv/bin/activate
bash run.sh
```

###### Run worker
```
AS_WORKER=yes bash run.sh
```

###### Run worker for Tenant ID 1
```
AS_WORKER=yes WORKER_QUEUES=1 bash run.sh
```

###### Procrastinate help  

```
export PYTHONPATH=.
procrastinate --app=app.utils.bg_worker.bg_app shell
procrastinate --verbose --app=app.utils.bg_worker.bg_app worker
procrastinate --verbose --app=app.utils.bg_worker.bg_app healthchecks
```

###### Add task
```
from app.models import *

# create tenant
user = User.query.get(1)
tenant = Tenant.create(user, "demo", user.email)

# create integration and task
integration = Integration(name="github", tenant_id=tenant.id)
integration.add_task(name="get_users", cron="* * * * *")

# create locker
Locker.add("test","value", tenant.id)
```

###### View tasks
```
from app.utils.bg_helper import BgHelper
from app.utils.bg_worker import bg_app

bg_app.open()
[print(i) for i in BgHelper().list_jobs()]
```

