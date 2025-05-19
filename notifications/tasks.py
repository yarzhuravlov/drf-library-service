from celery import shared_task
import json
import logging
from django.conf import settings
from notifications.handlers import send_notification_redis

logger = logging.getLogger(__name__)


@shared_task
def send_notification_celery(telegram_ids, text):
    """
    Celery-задача для асинхронної відправки сповіщень

    Args:
        telegram_ids (list): Список ID в Telegram
        text (str): Текст повідомлення

    Returns:
        bool: True якщо повідомлення відправлено в чергу, False - помилка
    """
    try:
        return send_notification_redis(telegram_ids, text)
    except Exception as e:
        logger.error(f"Помилка при відправці сповіщення через Celery: {e}")
        return False
