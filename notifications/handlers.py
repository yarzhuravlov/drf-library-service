import json
import logging
import redis
from django.conf import settings
from django.contrib.auth import get_user_model

from notifications.models import TelegramUser

User = get_user_model()

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

    connection_params = {
        "host": redis_host,
        "port": redis_port,
        "db": redis_db,
        "decode_responses": True,
    }

    # Додаємо пароль тільки якщо він заданий і не пустий
    if redis_password and redis_password.strip():
        connection_params["password"] = redis_password

    return redis.Redis(**connection_params)


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


def send_admin_notification(message, use_celery=True):
    """
    Надсилає повідомлення адміністраторам системи

    Args:
        message (str): Текст повідомлення
        use_celery (bool): Використовувати Celery (True) або безпосередньо Redis (False)

    Returns:
        bool: True якщо повідомлення відправлено, False в іншому випадку
    """
    try:
        # Отримуємо ID адміністраторів з налаштувань
        admin_chat_id = getattr(settings, "TELEGRAM_ADMIN_CHAT_ID", None)

        if not admin_chat_id:
            logger.error("TELEGRAM_ADMIN_CHAT_ID не налаштовано в settings")
            return False

        # Надсилаємо повідомлення
        return send_telegram_notification_django(
            [admin_chat_id], message, use_celery
        )
    except Exception as e:
        logger.error(
            f"Помилка при відправці повідомлення адміністраторам: {e}"
        )
        return False


def send_notification_to_all_admin_users(message: str, use_celery=True):
    admin_telegram_ids = list(
        TelegramUser.objects.filter(user__is_staff=True).values_list(
            "telegram_id",
            flat=True,
        )
    )
    return send_telegram_notification_django(
        admin_telegram_ids, message, use_celery
    )


def send_user_notification(user_telegram_id, message, use_celery=True):
    """
    Надсилає повідомлення конкретному користувачу

    Args:
        user_telegram_id (int): ID користувача в Telegram
        message (str): Текст повідомлення
        use_celery (bool): Використовувати Celery (True) або безпосередньо Redis (False)

    Returns:
        bool: True якщо повідомлення відправлено, False в іншому випадку
    """
    try:
        if not user_telegram_id:
            logger.error("ID користувача в Telegram не вказано")
            return False

        # Надсилаємо повідомлення
        return send_telegram_notification_django(
            [user_telegram_id], message, use_celery
        )
    except Exception as e:
        logger.error(f"Помилка при відправці повідомлення користувачу: {e}")
        return False


def send_notification_to_user(user: User, message: str, use_celery=True):
    user_id = TelegramUser.objects.get(user=user).telegram_id

    return send_user_notification(user_id, message, use_celery)
