import json
import logging
from typing import List, Optional, Union

import redis
from django.conf import settings
from django.contrib.auth import get_user_model

from notifications.models import TelegramUser

User = get_user_model()

# Налаштування логування
LOG_LEVEL_NOTIFICATIONS = getattr(settings, "LOG_LEVEL_NOTIFICATIONS", "INFO")
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL_NOTIFICATIONS),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def get_redis_connection() -> redis.Redis:
    """
    Отримує з'єднання з Redis, використовуючи налаштування django.conf.settings

    Returns:
        redis.Redis: клієнт Redis
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


def send_notification_redis(
    telegram_ids: List[Union[int, str]], text: str
) -> bool:
    """
    Надсилає повідомлення через Redis

    Args:
        telegram_ids (list): Список ID в Telegram
        text (str): Текст повідомлення

    Returns:
        bool: True якщо повідомлення відправлено в чергу, False - помилка
    """
    if not telegram_ids or not text:
        logger.error("telegram_ids та text мають бути непустими")
        return False

    try:
        message = {"telegram_ids": telegram_ids, "text": text}
        r = get_redis_connection()

        # Назву черги беремо з django settings
        notifications_queue_name = getattr(
            settings, "NOTIFICATIONS_QUEUE", "notifications"
        )

        r.rpush(notifications_queue_name, json.dumps(message))
        logger.info(
            f"Повідомлення успішно додано в чергу "
            f"'{notifications_queue_name}' для "
            f"{len(telegram_ids)} отримувачів"
        )
        return True
    except Exception as e:
        logger.error(f"Помилка при публікації повідомлення в Redis: {e}")
        return False


def send_telegram_notification_django(
    telegram_ids: List[Union[int, str]], text: str, use_celery: bool = True
) -> bool:
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
            # Імпортуємо тут, щоб уникнути циклічних залежностей
            from notifications.tasks import send_notification_celery

            send_notification_celery.delay(telegram_ids, text)
        else:
            return send_notification_redis(telegram_ids, text)
        return True
    except Exception as e:
        logger.error(f"Помилка при відправці Telegram сповіщення: {e}")
        return False


def send_admin_notification(message: str, use_celery: bool = True) -> bool:
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


def send_notification_to_all_admin_users(
    message: str, use_celery: bool = True
) -> bool:
    """
    Надсилає повідомлення всім адміністраторам, які мають Telegram ID

    Args:
        message (str): Текст повідомлення
        use_celery (bool): Використовувати Celery (True) або безпосередньо Redis (False)

    Returns:
        bool: True якщо повідомлення відправлено, False в іншому випадку
    """
    try:
        admin_telegram_ids = list(
            TelegramUser.objects.filter(user__is_staff=True).values_list(
                "telegram_id",
                flat=True,
            )
        )
        if not admin_telegram_ids:
            logger.warning("Жодного адміністратора з Telegram ID не знайдено!")
            return False
        return send_telegram_notification_django(
            admin_telegram_ids, message, use_celery
        )
    except Exception as e:
        logger.error(
            f"Помилка при надсиланні повідомлення всім адміністраторам: {e}"
        )
        return False


def send_user_notification(
    user_telegram_id: Union[int, str], message: str, use_celery: bool = True
) -> bool:
    """
    Надсилає повідомлення конкретному користувачу за його Telegram ID

    Args:
        user_telegram_id (int, str): ID користувача в Telegram
        message (str): Текст повідомлення
        use_celery (bool): Використовувати Celery (True) або безпосередньо Redis (False)

    Returns:
        bool: True якщо повідомлення відправлено, False в іншому випадку
    """
    if not user_telegram_id:
        logger.error("ID користувача в Telegram не вказано")
        return False

    try:
        # Надсилаємо повідомлення
        return send_telegram_notification_django(
            [user_telegram_id], message, use_celery
        )
    except Exception as e:
        logger.error(f"Помилка при відправці повідомлення користувачу: {e}")
        return False


def send_notification_to_user(
    user: User, message: str, use_celery: bool = True
) -> bool:
    """
    Надсилає повідомлення користувачу Django за його обліковим записом

    Args:
        user (User): Об'єкт користувача Django
        message (str): Текст повідомлення
        use_celery (bool): Використовувати Celery (True) або безпосередньо Redis (False)

    Returns:
        bool: True якщо повідомлення відправлено, False в іншому випадку
    """
    try:
        user_id = TelegramUser.objects.get(user=user).telegram_id
        return send_user_notification(user_id, message, use_celery)
    except TelegramUser.DoesNotExist:
        logger.error(f"User {user} не має прив'язаного Telegram акаунта!")
        return False
