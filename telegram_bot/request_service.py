import os

import requests


def get_me(access_token):
    url = f"{os.getenv("API_BASE_URL")}auth/users/me/"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "Custom-Header": "custom-value",
    }

    response = requests.get(url, headers=headers)

    response_data = response.json()

    return response_data


def inject_content_type_header(headers: dict = None):
    if not headers:
        headers = {}

    headers["Content-Type"] = "application/json"

    return headers


def inject_service_auth_headers(user_id, headers: dict = None):
    if not headers:
        headers = {}

    headers["X-Service-Secret"] = str(os.getenv("TELEGRAM_BOT_SERVICE_SECRET"))
    headers["X-User-Id"] = str(user_id)

    return headers


def get_user_borrowings(user_id):
    url = f"{os.getenv("API_BASE_URL")}borrowings/"

    headers = inject_content_type_header(inject_service_auth_headers(user_id))

    response = requests.get(url, headers=headers)

    return response
