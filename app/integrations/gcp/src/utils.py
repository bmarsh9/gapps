from google.cloud import compute_v1

class GCPQuery:
    def __init__(self, project_id, credentials):
        self.project_id = project_id
        self.credentials = credentials
        self.compute_client = compute_v1.ComputeClient(credentials=self.credentials, project=self.project_id)

    def list_instances(self):
        instances = []
        result = self.compute_client.instances().list(project=self.project_id, zone='us-central1-a').execute()
        if 'items' in result:
            for instance in result['items']:
                instances.append(instance)
        return instances

    def get_instance_status(self, instance_name):
        result = self.compute_client.instances().get(project=self.project_id, zone='us-central1-a', instance=instance_name).execute()
        return result['status']

'''
from google.oauth2 import service_account

credentials = service_account.Credentials.from_service_account_file('/path/to/credentials.json')
gcp_query = GCPQuery('YOUR_PROJECT_ID', credentials)
instances = gcp_query.list_instances()
for instance in instances:
    print(instance['name'])
instance_status = gcp_query.get_instance_status('instance-1')
print(instance_status)

'''
