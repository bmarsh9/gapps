from azure.common.credentials import ServicePrincipalCredentials
from azure.mgmt.compute import ComputeManagementClient

class AzureQuery:
    def __init__(self, tenant_id, client_id, secret, subscription_id):
        self.credentials = ServicePrincipalCredentials(
            tenant=tenant_id,
            client_id=client_id,
            secret=secret
        )
        self.compute_client = ComputeManagementClient(
            self.credentials,
            subscription_id
        )

    def list_instances(self):
        instances = []
        for vm in self.compute_client.virtual_machines.list_all():
            instances.append(vm.serialize())
        return instances

    def get_instance_status(self, resource_group, vm_name):
        vm = self.compute_client.virtual_machines.get(resource_group, vm_name, expand='instanceView')
        return vm.instance_view.statuses[1].display_status


'''
azure_query = AzureQuery('YOUR_TENANT_ID', 'YOUR_CLIENT_ID', 'YOUR_SECRET', 'YOUR_SUBSCRIPTION_ID')
instances = azure_query.list_instances()
for instance in instances:
    print(instance['name'])
instance_status = azure_query.get_instance_status('resource_group', 'vm_name')
print(instance_status)

'''
