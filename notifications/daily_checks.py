import logging
import requests
from datetime import datetime
from django.conf import settings

from notifications.handlers import send_telegram_notification_django

# Logging setup
logging.basicConfig(
    level=getattr(
        logging, getattr(settings, "LOG_LEVEL_NOTIFICATIONS", "INFO")
    ),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def get_overdue_borrowings(api_url, auth_token=None):
    """
    Gets a list of overdue borrowings via API

    Args:
        api_url (str): API URL for getting overdue borrowings
        auth_token (str, optional): Authorization token

    Returns:
        list: List of overdue borrowings or None in case of error
    """
    try:
        headers = {}
        if auth_token:
            headers["Authorization"] = f"Bearer {auth_token}"

        response = requests.get(api_url, headers=headers)
        response.raise_for_status()

        return response.json()
    except Exception as e:
        logger.error(f"Error getting overdue borrowings: {e}")
        return None


def check_overdue_borrowings(
    api_url, admin_chat_ids, auth_token=None, use_celery=True
):
    """
    Checks overdue borrowings and sends notifications

    Args:
        api_url (str): API URL for getting overdue borrowings
        admin_chat_ids (list): List of admin IDs for notifications
        auth_token (str, optional): Authorization token
        use_celery (bool): Use Celery (True) or Redis (False)

    Returns:
        int: Number of notifications sent or -1 in case of error
    """
    try:
        # Get overdue borrowings
        overdue_borrowings = get_overdue_borrowings(api_url, auth_token)

        if overdue_borrowings is None:
            return -1

        if not overdue_borrowings:
            # If there are no overdue borrowings, send a message
            logger.info("No overdue borrowings today")

            message = f"""
<b>📚 Overdue Books Report</b>

Date: {datetime.now().strftime('%d.%m.%Y')}
Status: ✅ No overdue borrowings today!
"""
            send_telegram_notification_django(
                telegram_ids=admin_chat_ids,
                text=message,
                use_celery=use_celery,
            )
            return 0

        # Send notifications about each overdue borrowing
        for borrowing in overdue_borrowings:
            user = borrowing.get("user", {})
            book = borrowing.get("book", {})

            # Format message text
            message = f"""
<b>⚠️ ATTENTION! Overdue book return!</b>

📖 <b>Book:</b> {book.get("title")}
✍️ <b>Author:</b> {book.get("author")}
👤 <b>User:</b> {user.get("first_name")} {user.get("last_name")}
📧 <b>Email:</b> {user.get("email")}
📅 <b>Borrow date:</b> {borrowing.get("borrow_date")}
📅 <b>Expected return date:</b> {borrowing.get("expected_return_date")}
⏱️ <b>Days overdue:</b> {borrowing.get("days_overdue", 0)}
💵 <b>Daily fee:</b> ${book.get("daily_fee", 0)}
"""

            # Send notification
            send_telegram_notification_django(
                telegram_ids=admin_chat_ids,
                text=message,
                use_celery=use_celery,
            )

        # Send summary message
        summary_message = f"""
<b>📚 Overdue Books Report</b>

Date: {datetime.now().strftime('%d.%m.%Y')}
Status: ⚠️ Found {len(overdue_borrowings)} overdue borrowings!
"""
        send_telegram_notification_django(
            telegram_ids=admin_chat_ids,
            text=summary_message,
            use_celery=use_celery,
        )

        return len(overdue_borrowings)

    except Exception as e:
        logger.error(f"Error checking overdue borrowings: {e}")
        return -1


# Function to be called from Celery
def scheduled_check_overdue_borrowings(
    api_url, admin_chat_ids, auth_token=None, use_celery=True
):
    """
    Function for scheduler (Celery)

    Args:
        api_url (str): API URL for getting overdue borrowings
        admin_chat_ids (list): List of admin IDs for notifications
        auth_token (str, optional): Authorization token
        use_celery (bool): Use Celery (True) or Redis (False)
    """
    try:
        logger.info("Starting daily check for overdue borrowings")
        result = check_overdue_borrowings(
            api_url=api_url,
            admin_chat_ids=admin_chat_ids,
            auth_token=auth_token,
            use_celery=use_celery,
        )
        logger.info(f"Daily check completed. Result: {result}")
        return result
    except Exception as e:
        logger.error(f"Error performing daily check: {e}")
        return -1


if __name__ == "__main__":
    # Usage example for testing
    API_URL = "http://localhost:8000/api/borrowings/overdue/"
    ADMIN_CHAT_IDS = [123456789]  # Replace with your chat ID
    AUTH_TOKEN = "your_api_token_here"  # Replace with your token

    result = scheduled_check_overdue_borrowings(
        api_url=API_URL, admin_chat_ids=ADMIN_CHAT_IDS, auth_token=AUTH_TOKEN
    )

    print(f"Daily check result: {result}")
