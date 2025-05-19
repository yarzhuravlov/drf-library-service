import json
import logging
import redis

from notifications.config import (
    REDIS_HOST,
    REDIS_PORT,
    REDIS_DB,
    REDIS_PASSWORD,
    NOTIFICATIONS_QUEUE,
    LOG_LEVEL,
)

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def get_redis_connection():
    """
    Отримує з'єднання з Redis
    Returns:
        redis.Redis: клієнт
    """
    return redis.Redis(
        host=REDIS_HOST,
        port=REDIS_PORT,
        db=REDIS_DB,
        password=REDIS_PASSWORD,
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
        r.rpush(NOTIFICATIONS_QUEUE, json.dumps(message))
        logger.info(
            f"Повідомлення успішно додано в чергу для "
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
