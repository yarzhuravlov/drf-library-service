import os
import logging
import httpx

logger = logging.getLogger(__name__)

API_BASE_URL = os.getenv("API_BASE_URL")


async def get_me(access_token):
    """
    Get current user data

    Args:
        access_token: JWT access token

    Returns:
        dict: User data or None in case of error
    """
    url = f"{API_BASE_URL}auth/users/me/"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers, timeout=10.0)
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        logger.error(
            f"error get_me: {e.response.status_code} - {e.response.text}"
        )
        return None
    except Exception as e:
        logger.error(f"Error in get_me: {e}")
        return None


def inject_content_type_header(headers: dict = None):
    """Adds Content-Type header to headers"""
    if not headers:
        headers = {}
    headers["Content-Type"] = "application/json"
    return headers


def inject_service_auth_headers(user_id, headers: dict = None):
    """Adds service authorization headers and user ID"""
    if not headers:
        headers = {}
    headers["X-Service-Secret"] = str(
        os.getenv("TELEGRAM_BOT_SERVICE_SECRET", "")
    )
    headers["X-User-Id"] = str(user_id)
    return headers


async def get_user_borrowings(user_id):
    """
    Get list of books borrowed by user

    Args:
        user_id: User ID

    Returns:
        list: List of dictionaries with borrowing data or empty list
    """
    url = f"{API_BASE_URL}borrowings/?user_id={user_id}"
    headers = inject_content_type_header(inject_service_auth_headers(user_id))
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers, timeout=10.0)
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        logger.error(
            f"HTTP error in get_user_borrowings: {e.response.status_code} - "
            f"{e.response.text}"
        )
        return []
    except Exception as e:
        logger.error(f"Error in get_user_borrowings: {e}")
        return []


async def borrow_book(access_token, book_id):
    """
    Borrow a book

    Args:
        access_token: JWT access token
        book_id: Book ID

    Returns:
        tuple: (success (bool), response_data or error_text)
    """
    from datetime import date, timedelta

    today = date.today()
    expected_return = today + timedelta(days=14)

    url = f"{API_BASE_URL}borrowings/"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                json={
                    "book": int(book_id),
                    "borrow_date": today.isoformat(),
                    "expected_return": expected_return.isoformat(),
                },
                headers=headers,
                timeout=10.0,
            )
            response.raise_for_status()
            return True, response.json()
    except httpx.HTTPStatusError as e:
        try:
            error_data = e.response.json()
            if isinstance(error_data, dict):
                error_details = []
                for key, value in error_data.items():
                    if isinstance(value, list) and value:
                        error_details.append(f"{key}: {value[0]}")
                    else:
                        error_details.append(f"{key}: {value}")
                error_text = ", ".join(error_details)
            else:
                error_text = f"HTTP error {e.response.status_code}"
        except Exception:
            error_text = f"HTTP error {e.response.status_code}"

        logger.error(f"HTTP error in borrow_book: {error_text}")
        return False, error_text
    except Exception as e:
        logger.error(f"Error in borrow_book: {e}")
        return False, str(e)


async def get_books(access_token, search_query=None):
    """
    Get list of available books

    Args:
        access_token: JWT access token
        search_query: Optional search parameter

    Returns:
        list: List of books or empty list in case of error
    """
    url = f"{API_BASE_URL}books/"
    if search_query:
        url += f"?search={search_query}"

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers, timeout=10.0)
            response.raise_for_status()
            data = response.json()

            if isinstance(data, dict) and "results" in data:
                return data["results"]
            if isinstance(data, list):
                return data
            return []
    except httpx.HTTPStatusError as e:
        logger.error(
            f"HTTP error in get_books: {e.response.status_code} - "
            f"{e.response.text}"
        )
        return []
    except Exception as e:
        logger.error(f"Error in get_books: {e}")
        return []


async def get_book_details(access_token, book_id):
    """
    Get book details by ID

    Args:
        access_token: JWT access token
        book_id: Book ID

    Returns:
        dict: Book information or None in case of error
    """
    url = f"{API_BASE_URL}books/{book_id}/"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers, timeout=10.0)
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        logger.error(
            f"HTTP error in get_book_details: {e.response.status_code} - "
            f"{e.response.text}"
        )
        return None
    except Exception as e:
        logger.error(f"Error in get_book_details: {e}")
        return None


async def register_telegram_user(email, password, telegram_id):
    """
    Register telegram user and get tokens

    Args:
        email: User email
        password: User password
        telegram_id: Telegram user ID

    Returns:
        tuple: (success (bool), data or error_text)
    """
    url = f"{API_BASE_URL}bots/register_user/"
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                json={
                    "email": email,
                    "password": password,
                    "telegram_id": int(telegram_id),
                },
                timeout=10.0,
            )

            if response.status_code == 200:
                data = response.json()
                if "access" in data:
                    return True, data
                return (
                    False,
                    "Received incomplete authorization data from server",
                )

            try:
                error_data = response.json()
                if isinstance(error_data, dict):
                    if "error" in error_data:
                        return False, error_data["error"]

                    error_details = []
                    for key, value in error_data.items():
                        if isinstance(value, list) and value:
                            error_details.append(f"{key}: {value[0]}")
                        else:
                            error_details.append(f"{key}: {value}")
                    error_text = ", ".join(error_details)
                    return False, error_text
                return (
                    False,
                    f"Server error: HTTP {response.status_code}",
                )
            except Exception:
                return False, f"Server error: HTTP {response.status_code}"

    except Exception as e:
        logger.error(f"Error in register_telegram_user: {e}")
        return False, f"Connection error: {str(e)}"


async def refresh_token(refresh_token_value):
    """
    Refresh access_token using refresh_token

    Args:
        refresh_token_value: Refresh token value

    Returns:
        tuple: (success (bool), new_access_token or error)
    """
    url = f"{API_BASE_URL}token/refresh/"
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                json={"refresh": refresh_token_value},
                timeout=10.0,
            )
            response.raise_for_status()
            data = response.json()
            if "access" in data:
                return True, data["access"]
            return False, "Server did not return access token"
    except httpx.HTTPStatusError as e:
        logger.error(
            f"HTTP error in refresh_token: {e.response.status_code} - "
            f"{e.response.text}"
        )
        return False, f"Token refresh error: {e.response.status_code}"
    except Exception as e:
        logger.error(f"Error in refresh_token: {e}")
        return False, f"Connection error: {str(e)}"
