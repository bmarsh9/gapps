#### Helpful functions to use within your tasks

```
# Save results for a task
task.save_results(data={"message":"some data"})

# Save results for a task with a version
task.save_results(data={"message":"some data"}, version="1.1.1")

# Save results for a task with a version (and update)
task.save_results(data={"message":"some data"}, version="1.1.1", update=True)

# Get the first result
task.get_first_result()

# Get the first result by version
task.get_first_result(sort="version")

# Get the latest result
task.get_latest_result()

# Get the latest result by version
task.get_latest_result(sort="version")

# Get all results
task.sort_results()

# Get all results by version
task.sort_results(sort="version")

# Get result by specific version
task.get_result_by_version("1.1.1")

# Add finding
task.add_finding(title="testing the title2",risk=7,status="in progress")
```


#### Creating your own integrations  

Take a look at `/app/integrations/demo` for a tutorial on how to add your own integration

#### TBD
