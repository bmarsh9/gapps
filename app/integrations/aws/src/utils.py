
import boto3

class AWSQuery:
    def __init__(self, region_name, aws_access_key_id, aws_secret_access_key):
        self.region_name = region_name
        self.aws_access_key_id = aws_access_key_id
        self.aws_secret_access_key = aws_secret_access_key
        self.client = boto3.client('ec2', region_name=self.region_name, aws_access_key_id=self.aws_access_key_id, aws_secret_access_key=self.aws_secret_access_key)

    def list_instances(self):
        response = self.client.describe_instances()
        instances = []
        for reservation in response['Reservations']:
            for instance in reservation['Instances']:
                instances.append(instance)
        return instances

    def get_instance_status(self, instance_id):
        response = self.client.describe_instance_status(InstanceIds=[instance_id])
        if len(response['InstanceStatuses']) > 0:
            return response['InstanceStatuses'][0]
        else:
            return None


'''
aws_query = AWSQuery('us-east-1', 'YOUR_AWS_ACCESS_KEY_ID', 'YOUR_AWS_SECRET_ACCESS_KEY')
instances = aws_query.list_instances()
for instance in instances:
    print(instance['InstanceId'])
instance_status = aws_query.get_instance_status('i-0123456789abcdefg')
print(instance_status['InstanceState']['Name'])
'''
