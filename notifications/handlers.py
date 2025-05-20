import json
import logging
from typing import List, Optional, Union

import redis
from django.conf import settings
from django.contrib.auth import get_user_model

from notifications.models import TelegramUser

User = get_user_model()

# Logging configuration
LOG_LEVEL_NOTIFICATIONS = getattr(settings, "LOG_LEVEL_NOTIFICATIONS", "INFO")
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL_NOTIFICATIONS),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def get_redis_connection() -> redis.Redis:
    """
    Gets a connection to Redis using django.conf.settings

    Returns:
        redis.Redis: Redis client
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

    # Only add password if it's set and not empty
    if redis_password and redis_password.strip():
        connection_params["password"] = redis_password

    return redis.Redis(**connection_params)


def send_notification_redis(
    telegram_ids: List[Union[int, str]], text: str
) -> bool:
    """
    Sends a message through Redis

    Args:
        telegram_ids (list): List of Telegram IDs
        text (str): Message text

    Returns:
        bool: True if the message was sent to the queue, False if error
    """
    if not telegram_ids or not text:
        logger.error("telegram_ids and text must be non-empty")
        return False

    try:
        message = {"telegram_ids": telegram_ids, "text": text}
        r = get_redis_connection()

        # Get queue name from django settings
        notifications_queue_name = getattr(
            settings, "NOTIFICATIONS_QUEUE", "notifications"
        )

        r.rpush(notifications_queue_name, json.dumps(message))
        logger.info(
            f"Message successfully added to queue "
            f"'{notifications_queue_name}' for "
            f"{len(telegram_ids)} recipients"
        )
        return True
    except Exception as e:
        logger.error(f"Error publishing message to Redis: {e}")
        return False


def send_telegram_notification_django(
    telegram_ids: List[Union[int, str]], text: str, use_celery: bool = True
) -> bool:
    """
    Function for sending Telegram notifications from Django

    Args:
        telegram_ids (list): List of recipient IDs in Telegram
        text (str): Message text
        use_celery (bool): Use Celery (True) or Redis directly (False)

    Returns:
        bool: True if the message was sent, False otherwise
    """
    try:
        if use_celery:
            # Import here to avoid circular dependencies
            from notifications.tasks import send_notification_celery

            send_notification_celery.delay(telegram_ids, text)
        else:
            return send_notification_redis(telegram_ids, text)
        return True
    except Exception as e:
        logger.error(f"Error sending Telegram notification: {e}")
        return False


def send_admin_notification(message: str, use_celery: bool = True) -> bool:
    """
    Sends a message to system administrators

    Args:
        message (str): Message text
        use_celery (bool): Use Celery

    Returns:
        bool: True if the message was sent, False otherwise
    """
    try:
        # Get admin IDs from settings
        admin_chat_id = getattr(settings, "TELEGRAM_ADMIN_CHAT_ID", None)

        if not admin_chat_id:
            logger.error("TELEGRAM_ADMIN_CHAT_ID not configured in settings")
            return False

        # Send message
        return send_telegram_notification_django(
            [admin_chat_id], message, use_celery
        )
    except Exception as e:
        logger.error(f"Error sending message to administrators: {e}")
        return False


def send_notification_to_all_admin_users(
    message: str, use_celery: bool = True
) -> bool:
    """
    Sends a message to all administrators who have a Telegram ID

    Args:
        message (str): Message text
        use_celery (bool): Use Celery

    Returns:
        bool: True if the message was sent, False otherwise
    """
    try:
        admin_telegram_ids = list(
            TelegramUser.objects.filter(user__is_staff=True).values_list(
                "telegram_id",
                flat=True,
            )
        )
        if not admin_telegram_ids:
            logger.warning("No administrators with Telegram ID found!")
            return False
        return send_telegram_notification_django(
            admin_telegram_ids, message, use_celery
        )
    except Exception as e:
        logger.error(f"Error sending message to all administrators: {e}")
        return False


def send_user_notification(
    user_telegram_id: Union[int, str], message: str, use_celery: bool = True
) -> bool:
    """
    Sends a message to a specific user by their Telegram ID

    Args:
        user_telegram_id (int, str): User's Telegram ID
        message (str): Message text
        use_celery (bool): Use Celery

    Returns:
        bool: True if the message was sent, False otherwise
    """
    if not user_telegram_id:
        logger.error("User's Telegram ID not specified")
        return False

    try:
        # Send message
        return send_telegram_notification_django(
            [user_telegram_id], message, use_celery
        )
    except Exception as e:
        logger.error(f"Error sending message to user: {e}")
        return False


def send_notification_to_user(
    user: User, message: str, use_celery: bool = True
) -> bool:
    """
    Sends a message to a Django user by their account

    Args:
        user (User): Django user object
        message (str): Message text
        use_celery (bool): Use Celery

    Returns:
        bool: True if the message was sent, False otherwise
    """
    try:
        user_id = TelegramUser.objects.get(user=user).telegram_id
        return send_user_notification(user_id, message, use_celery)
    except TelegramUser.DoesNotExist:
        logger.error(f"User {user} doesn't have a linked Telegram account!")
        return False
