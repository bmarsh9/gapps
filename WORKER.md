## Docs on background worker

#### Details  

##### Docs  
[docs are here](https://github.com/procrastinate-org/procrastinate)

##### Setup  
```
export SETUP_DB=yes;docker-compose up -d postgres
source venv/bin/activate
(OPTIONAL) - export PYTHONPATH=.
procrastinate --app=app.utils.bg_worker.bg_app schema --apply
bash run.sh
```

###### Run worker
```
python3 p_worker/run_worker.py
```

###### Class module  
```
python3 p_worker/test_client.py
```

###### Procrastinate help  

```
procrastinate --app=app.utils.bg_worker.bg_app shell
procrastinate --verbose --app=app.utils.bg_worker.bg_app worker
procrastinate --verbose --app=app.utils.bg_worker.bg_app healthchecks

# Add tasks to app/worker/tasks.py
```
