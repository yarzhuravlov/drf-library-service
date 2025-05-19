import logging
from celery import shared_task
from notifications.handlers import send_notification_redis

logger = logging.getLogger(__name__)


@shared_task(name="send_notification_celery")
def send_notification_celery(telegram_ids, text):
    """
    Celery task для відправки повідомлення через Redis (message bus)
    """
    logger.info(
        f"Celery task: надсилаю повідомлення {telegram_ids}, {text[:50]}..."
    )
    # Виклик функції для відправки повідомлення через Redis
    # Це важливо для тестів, щоб патч працював правильно
    return send_notification_redis(telegram_ids, text)
