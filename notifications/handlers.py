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

    # Параметри підключення
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


# Спеціалізовані функції для різних типів повідомлень


def notify_new_borrowing(borrowing):
    """
    Відправляє сповіщення про нове позичання книги

    Args:
        borrowing: Об'єкт Borrowing з інформацією про позичання

    Returns:
        bool: Результат надсилання повідомлення
    """
    try:
        # Отримуємо ID адміністраторів з налаштувань
        admin_chat_id = getattr(settings, "TELEGRAM_ADMIN_CHAT_ID", None)

        if not admin_chat_id:
            logger.error("TELEGRAM_ADMIN_CHAT_ID не налаштовано в settings")
            return False

        # Формуємо HTML-повідомлення
        message = (
            f"🔔 <b>Нове замовлення книги</b>\n\n"
            f"📚 Книга: <i>{borrowing.book.title}</i>\n"
            f"👤 Користувач: {borrowing.user.email}\n"
            f"📅 Дата позичання: {borrowing.borrow_date}\n"
            f"📅 Очікуване повернення: {borrowing.expected_return}\n"
            f"💰 Щоденна плата: ${borrowing.book.daily_fee}"
        )

        # Надсилаємо через стандартну функцію
        return send_telegram_notification_django([admin_chat_id], message)
    except Exception as e:
        logger.error(
            f"Помилка при формуванні повідомлення про нове позичання: {e}"
        )
        return False


def notify_book_returned(borrowing):
    """
    Відправляє сповіщення про повернення книги

    Args:
        borrowing: Об'єкт Borrowing з інформацією про позичання

    Returns:
        bool: Результат надсилання повідомлення
    """
    try:
        # Отримуємо ID адміністраторів з налаштувань
        admin_chat_id = getattr(settings, "TELEGRAM_ADMIN_CHAT_ID", None)

        if not admin_chat_id:
            logger.error("TELEGRAM_ADMIN_CHAT_ID не налаштовано в settings")
            return False

        # Обчислюємо кількість днів користування
        days_used = (borrowing.actual_return - borrowing.borrow_date).days

        # Формуємо HTML-повідомлення
        message = (
            f"📚 <b>Книгу повернуто</b>\n\n"
            f"📚 Книга: <i>{borrowing.book.title}</i>\n"
            f"👤 Користувач: {borrowing.user.email}\n"
            f"📅 Дата позичання: {borrowing.borrow_date}\n"
            f"📅 Фактичне повернення: {borrowing.actual_return}\n"
            f"⏱️ Тривалість: {days_used} днів"
        )

        # Перевіряємо чи є прострочення
        if borrowing.actual_return > borrowing.expected_return:
            overdue_days = (
                borrowing.actual_return - borrowing.expected_return
            ).days
            message += (
                f"\n\n⚠️ <b>Увага! Прострочення на {overdue_days} днів</b>\n"
                f"💰 Очікується штраф!"
            )

        # Надсилаємо через стандартну функцію
        return send_telegram_notification_django([admin_chat_id], message)
    except Exception as e:
        logger.error(
            f"Помилка при формуванні повідомлення про повернення книги: {e}"
        )
        return False
