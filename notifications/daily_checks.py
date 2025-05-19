import logging
import asyncio
import requests
from datetime import datetime
from django.conf import settings

from notifications.handlers import send_telegram_notification_django

# Налаштування логування
logging.basicConfig(
    level=getattr(
        logging, getattr(settings, "LOG_LEVEL_NOTIFICATIONS", "INFO")
    ),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def get_overdue_borrowings(api_url, auth_token=None):
    """
    Отримує список прострочених позичань через API

    Args:
        api_url (str): URL API для отримання прострочених позичань
        auth_token (str, optional): Токен авторизації

    Returns:
        list: Список прострочених позичань або None у випадку помилки
    """
    try:
        headers = {}
        if auth_token:
            headers["Authorization"] = f"Bearer {auth_token}"

        response = requests.get(api_url, headers=headers)
        response.raise_for_status()

        return response.json()
    except Exception as e:
        logger.error(f"Помилка при отриманні прострочених позичань: {e}")
        return None


def check_overdue_borrowings(
    api_url, admin_chat_ids, auth_token=None, use_celery=True
):
    """
    Перевіряє прострочені позичання та надсилає сповіщення

    Args:
        api_url (str): URL API для отримання прострочених позичань
        admin_chat_ids (list): Список ID адміністраторів для сповіщень
        auth_token (str, optional): Токен авторизації
        use_celery (bool): Використовувати Celery (True) або Redis (False)

    Returns:
        int: Кількість надісланих сповіщень або -1 у випадку помилки
    """
    try:
        # Отримання прострочених позичань
        overdue_borrowings = get_overdue_borrowings(api_url, auth_token)

        if overdue_borrowings is None:
            return -1

        if not overdue_borrowings:
            # Якщо немає прострочених позичань, відправляємо повідомлення
            logger.info("Немає прострочених позичань на сьогодні")

            message = f"""
<b>📚 Звіт про прострочення книг</b>

Дата: {datetime.now().strftime('%d.%m.%Y')}
Статус: ✅ Немає прострочених позичань на сьогодні!
"""
            send_telegram_notification_django(
                telegram_ids=admin_chat_ids,
                text=message,
                use_celery=use_celery,
            )
            return 0

        # Відправка сповіщень про кожне прострочення
        for borrowing in overdue_borrowings:
            user = borrowing.get("user", {})
            book = borrowing.get("book", {})

            # Формування тексту повідомлення
            message = f"""
<b>⚠️ УВАГА! Прострочене повернення книги!</b>

📖 <b>Книга:</b> {book.get("title")}
✍️ <b>Автор:</b> {book.get("author")}
👤 <b>Користувач:</b> {user.get("first_name")} {user.get("last_name")}
📧 <b>Email:</b> {user.get("email")}
📅 <b>Дата позичання:</b> {borrowing.get("borrow_date")}
📅 <b>Очікувана дата повернення:</b> {borrowing.get("expected_return_date")}
⏱️ <b>Прострочено днів:</b> {borrowing.get("days_overdue", 0)}
💵 <b>Щоденна плата:</b> ${book.get("daily_fee", 0)}
"""

            # Відправка сповіщення
            send_telegram_notification_django(
                telegram_ids=admin_chat_ids,
                text=message,
                use_celery=use_celery,
            )

        # Відправка підсумкового повідомлення
        summary_message = f"""
<b>📚 Звіт про прострочення книг</b>

Дата: {datetime.now().strftime('%d.%m.%Y')}
Статус: ⚠️ Виявлено {len(overdue_borrowings)} прострочених позичань!
"""
        send_telegram_notification_django(
            telegram_ids=admin_chat_ids,
            text=summary_message,
            use_celery=use_celery,
        )

        return len(overdue_borrowings)

    except Exception as e:
        logger.error(f"Помилка при перевірці прострочених позичань: {e}")
        return -1


# Функція для виклику з Celery
def scheduled_check_overdue_borrowings(
    api_url, admin_chat_ids, auth_token=None, use_celery=True
):
    """
    Функція для планувальника (Celery)

    Args:
        api_url (str): URL API для отримання прострочених позичань
        admin_chat_ids (list): Список ID адміністраторів для сповіщень
        auth_token (str, optional): Токен авторизації
        use_celery (bool): Використовувати Celery (True) або Redis (False)
    """
    try:
        logger.info("Запуск щоденної перевірки прострочених позичань")
        result = check_overdue_borrowings(
            api_url=api_url,
            admin_chat_ids=admin_chat_ids,
            auth_token=auth_token,
            use_celery=use_celery,
        )
        logger.info(f"Щоденну перевірку виконано. Результат: {result}")
        return result
    except Exception as e:
        logger.error(f"Помилка при виконанні щоденної перевірки: {e}")
        return -1


if __name__ == "__main__":
    # Приклад використання для тестування
    API_URL = "http://localhost:8000/api/borrowings/overdue/"
    ADMIN_CHAT_IDS = [123456789]  # Замініть на ID вашого чату
    AUTH_TOKEN = "your_api_token_here"  # Замініть на ваш токен

    result = scheduled_check_overdue_borrowings(
        api_url=API_URL, admin_chat_ids=ADMIN_CHAT_IDS, auth_token=AUTH_TOKEN
    )

    print(f"Результат щоденної перевірки: {result}")
