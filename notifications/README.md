# Notifications App

Цей Django-додаток відповідає за генерацію та відправку сповіщень у системі.
Він слугує як центральна точка для ініціації різноманітних сповіщень, які потім можуть бути оброблені різними сервісами (наприклад, Telegram ботом).

## Основні функції

- **Генерація сповіщень**: Формує повідомлення на основі подій у системі (наприклад, щоденні перевірки прострочених книг).
- **Інтеграція з чергою повідомлень**: Надсилає сповіщення у чергу Redis, звідки їх можуть забирати інші воркери.
- **Асинхронна відправка**: Можливість відправляти сповіщення асинхронно за допомогою Celery.

## Як це працює

1.  Інші частини Django-проєкту (або заплановані завдання) викликають функції з `notifications.handlers`.
2.  Хендлери формують повідомлення та передають його або напряму в Redis (для негайної обробки), або через Celery (для фонової обробки).
3.  Повідомлення у черзі Redis має наступний JSON-формат (приклад):
    ```json
    {
      "telegram_ids": [123456789, 987654321],
      "text": "Текст вашого сповіщення"
    }
    ```

## Налаштування

Більшість налаштувань (Redis URL, назва черги) керуються централізовано через `config/settings.py` та відповідні змінні оточення у головному `.env` файлі проєкту.

- `REDIS_HOST`, `REDIS_PORT`, `REDIS_DB`, `REDIS_PASSWORD`: Параметри підключення до Redis.
- `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND`: Налаштування для Celery.
- `NOTIFICATIONS_QUEUE`: Назва черги Redis, яка використовується для сповіщень.
- `LOG_LEVEL_NOTIFICATIONS`: Рівень логування для цього додатку.

## Використання для різних модулів

### Загальне використання

Для відправки сповіщення з будь-якої частини Django-проєкту:

```python
from notifications.handlers import send_telegram_notification_django

# Приклад відправки (припускаємо, що telegram_ids - це список ID чатів/користувачів)
user_telegram_ids = [123456789]
message_text = "Ваше замовлення оновлено!"

# Відправка через Celery (рекомендовано для більшості випадків)
send_telegram_notification_django(
    telegram_ids=user_telegram_ids,
    text=message_text,
    use_celery=True
)

# Відправка напряму в Redis (якщо Celery не налаштований або для специфічних випадків)
send_telegram_notification_django(
    telegram_ids=user_telegram_ids,
    text=message_text,
    use_celery=False
)
```

### Для модуля Borrowings (позичання)

Вже реалізовані функції:

```python
from notifications.handlers import notify_new_borrowing, notify_book_returned
from borrowings.models import Borrowing

# Коли користувач створює нове позичання:
borrowing = Borrowing.objects.get(id=1)
notify_new_borrowing(borrowing)

# Коли книга повертається:
borrowing = Borrowing.objects.get(id=1)
notify_book_returned(borrowing)
```

### Для модуля Payments (оплати)

Приклад інтеграції для модуля оплат:

```python
from notifications.handlers import send_telegram_notification_django
from django.conf import settings

def notify_payment_received(payment):
    """
    Відправляє сповіщення про отримання оплати

    Args:
        payment: Об'єкт Payment з інформацією про оплату

    Returns:
        bool: Результат надсилання повідомлення
    """
    try:
        # Отримуємо ID адміністраторів з налаштувань
        admin_chat_id = getattr(settings, "TELEGRAM_ADMIN_CHAT_ID", None)

        if not admin_chat_id:
            return False

        # Формуємо HTML-повідомлення
        message = (
            f"💰 <b>Нова оплата отримана</b>\n\n"
            f"🆔 ID оплати: {payment.id}\n"
            f"👤 Користувач: {payment.user.email}\n"
            f"📚 Позичання: {payment.borrowing.book.title}\n"
            f"💵 Сума: ${payment.amount}\n"
            f"📅 Дата: {payment.date}\n"
            f"✅ Статус: {payment.status}"
        )

        # Надсилаємо повідомлення
        return send_telegram_notification_django([admin_chat_id], message)
    except Exception as e:
        # Логування помилки
        return False
```

### Для модуля Accounts (користувачі)

Ось приклад для сповіщень про нових користувачів:

```python
from notifications.handlers import send_telegram_notification_django
from django.conf import settings

def notify_new_user_registered(user):
    """
    Відправляє сповіщення про реєстрацію нового користувача

    Args:
        user: Об'єкт користувача, який щойно зареєструвався

    Returns:
        bool: Результат надсилання повідомлення
    """
    try:
        admin_chat_id = getattr(settings, "TELEGRAM_ADMIN_CHAT_ID", None)

        if not admin_chat_id:
            return False

        message = (
            f"👤 <b>Новий користувач зареєструвався</b>\n\n"
            f"📧 Email: {user.email}\n"
            f"👤 Ім'я: {user.username}\n"
            f"📅 Дата реєстрації: {user.date_joined.strftime('%Y-%m-%d %H:%M')}"
        )

        return send_telegram_notification_django([admin_chat_id], message)
    except Exception as e:
        return False
```

## Створення власних обробників сповіщень

Щоб додати власний обробник сповіщень для свого модуля, рекомендується:

1. Створіть файл `notifications.py` у своєму додатку
2. Додайте функції для генерації необхідних повідомлень
3. Викликайте ці функції з відповідних місць вашого коду

**Приклад структури файлу для модуля оплат**:

```python
# payments/notifications.py
from notifications.handlers import send_telegram_notification_django
from django.conf import settings

def notify_payment_received(payment):
    # Код вашого обробника...
    pass

def notify_payment_failed(payment, error_message):
    # Код вашого обробника...
    pass
```

## Тестування

Для запуску тестів, специфічних для цього додатку, виконайте команду з кореневої директорії проєкту:

```bash
python manage.py test notifications
```
