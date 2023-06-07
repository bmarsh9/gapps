class GoogleWorkspaceAPI(object):

    def __init__(self, client_id, client_secret, refresh_token):
        self.client_id = client_id
        self.client_secret = client_secret
        self.refresh_token = refresh_token

    def authorize(self):
        # Create a Google OAuth2 client
        client = GoogleCredentials.get_application_default()

        # Exchange the refresh token for an access token
        access_token = client.refresh(self.refresh_token)

        # Set the access token on the client
        client.access_token = access_token

        return client

    def query(self, endpoint, method, **kwargs):
        # Create a request object
        request = googleapiclient.http.HttpRequest(
            endpoint,
            method=method,
            **kwargs
        )

        # Set the access token on the request
        request.headers['Authorization'] = 'Bearer ' + self.access_token

        # Make the request
        response = self.authorize().execute(request)

        # Return the response
        return response

'''
api = GoogleWorkspaceAPI(
    client_id='YOUR_CLIENT_ID',
    client_secret='YOUR_CLIENT_SECRET',
    refresh_token='YOUR_REFRESH_TOKEN'
)

users = api.query(
    'https://www.googleapis.com/admin/directory/v1/users',
    'GET'
)

for user in users['users']:
    print(user['name'])
'''
