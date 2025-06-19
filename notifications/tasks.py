from celery import shared_task
import logging
from notifications.handlers import send_notification_redis

logger = logging.getLogger(__name__)


@shared_task(name="notifications.tasks.send_notification_celery")
def send_notification_celery(telegram_ids, text):
    """
    Celery task for asynchronous notification sending

    Args:
        telegram_ids (list): List of Telegram IDs
        text (str): Message text

    Returns:
        bool: True if the message was sent to the queue, False if error
    """
    try:
        return send_notification_redis(telegram_ids, text)
    except Exception as e:
        logger.error(f"Error sending notification through Celery: {e}")
        return False
