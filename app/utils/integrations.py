import requests
from flask import current_app

def api_get(endpoint: str, params: dict = None):
    base_url = current_app.config["INTEGRATIONS_BASE_URL"]
    url = f"{base_url.rstrip('/')}/{endpoint.lstrip('/')}"

    token = f"Bearer {current_app.config['INTEGRATIONS_TOKEN']}"
    headers = {
        "Authorization": token
    }

    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()
    return response.json()