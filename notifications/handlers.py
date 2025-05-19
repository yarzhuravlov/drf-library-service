import json
import logging
import redis
from django.conf import settings

LOG_LEVEL_NOTIFICATIONS = getattr(settings, "LOG_LEVEL_NOTIFICATIONS", "INFO")

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL_NOTIFICATIONS),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def get_redis_connection():
    """
    Отримує з'єднання з Redis, використовуючи налаштування django.conf.settings
    Returns:
        redis.Redis: клієнт
    """
    redis_host = getattr(settings, "REDIS_HOST", "localhost")
    redis_port = getattr(settings, "REDIS_PORT", 6379)
    redis_db = getattr(settings, "REDIS_DB", 0)
    redis_password = getattr(settings, "REDIS_PASSWORD", None)

    return redis.Redis(
        host=redis_host,
        port=redis_port,
        db=redis_db,
        password=redis_password,
        decode_responses=True,
    )


def send_notification_redis(telegram_ids, text):
    """
    Надсилає повідомлення через Redis
    Args:
        telegram_ids (list): Список ID в Telegram
        text (str): Текст повідомлення
    Returns:
        bool: True якщо повідомлення відправлено в чергу, False - помилка
    """
    try:
        if not telegram_ids or not text:
            logger.error("telegram_ids та text мають бути непустими")
            return False
        message = {"telegram_ids": telegram_ids, "text": text}
        r = get_redis_connection()

        # Назву черги також беремо з django settings
        notifications_queue_name = getattr(
            settings, "NOTIFICATIONS_QUEUE", "notifications"
        )

        r.rpush(notifications_queue_name, json.dumps(message))
        logger.info(
            f"Повідомлення успішно додано в чергу"
            f"'{notifications_queue_name}' для "
            f"{len(telegram_ids)} отримувачів"
        )
        return True
    except Exception as e:
        logger.error(f"Помилка при публікації повідомлення в Redis: {e}")
        return False


def send_telegram_notification_django(telegram_ids, text, use_celery=True):
    """
    Функція для відправки Telegram сповіщень з Django

    Args:
        telegram_ids (list): Список ID отримувачів в Telegram
        text (str): Текст повідомлення
        use_celery (bool): Використовувати Celery (True)
        або безпосередньо Redis (False)

    Returns:
        bool: True якщо повідомлення відправлено, False в іншому випадку
    """
    try:
        if use_celery:
            from notifications.tasks import send_notification_celery

            send_notification_celery.delay(telegram_ids, text)
        else:
            send_notification_redis(telegram_ids, text)
        return True
    except Exception as e:
        logger.error(f"Помилка при відправці Telegram сповіщення: {e}")
        return False
