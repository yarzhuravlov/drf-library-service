# Інтеграція сповіщень у ваш модуль

Цей документ описує, як інтегрувати сповіщення в ваш Django-модуль. Основні функції для відправки сповіщень вже реалізовані — вам потрібно лише викликати їх з вашого коду та передати готові повідомлення.

> **ВАЖЛИВО:** Формування тексту повідомлення знаходиться повністю у відповідальності розробника модуля. Функції сповіщень приймають лише готовий текст повідомлення.

## Доступні функції для відправки сповіщень

Start commands

celery -A config worker -l INFO --pool=solo - Celery
python -m telegram_bot.worker - worker who works with redis
python manage.py runserser - server
redis - localy

Ми надаємо три основні функції для надсилання сповіщень:

### 1. Сповіщення для адміністраторів

```python
from notifications.handlers import send_admin_notification

# Приклад використання:
message = "Ваше повідомлення тут"
send_admin_notification(message)
```

### 2. Сповіщення для користувачів

```python
from notifications.handlers import send_user_notification

# Приклад використання:
user_telegram_id = 123456789  # ID користувача в Telegram
message = "Ваше повідомлення тут"
send_user_notification(user_telegram_id, message)

```

### 3. Розширена функція для більшої гнучкості

```python
from notifications.handlers import send_telegram_notification_django

# Приклад використання для декількох отримувачів:
telegram_ids = [123456789, 987654321]  # Список ID отримувачів
message = "Ваше повідомлення тут"
send_telegram_notification_django(telegram_ids, message)
```

## Використання в вашому коді

Кожен розробник модуля відповідає за формування тексту повідомлення. Потім цей текст передається у функції сповіщень:

```python
# your_app/views.py або your_app/signals.py
from notifications.handlers import send_admin_notification, send_user_notification

def some_view(request):
    # Ваш код...

    # Формуєте повідомлення для адміністраторів
    admin_message = (
        f"<b>Нова дія в системі</b>\n\n"
        f"Дата: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
        f"Користувач: {request.user.email}\n"
        f"Дія: створення запису"
    )
    send_admin_notification(admin_message)

    # Формуєте повідомлення для користувача
    user_message = f"Дякуємо за використання нашого сервісу! Ваш запит оброблено."
    user_telegram_id = get_user_telegram_id(request.user)  # Ваша функція для отримання ID
    if user_telegram_id:
        send_user_notification(user_telegram_id, user_message)

    # Продовження вашого коду...
```

## Важливі моменти

1. **Формування повідомлень:** Ви повністю відповідаєте за формування тексту повідомлення. Це дає вам максимальну гнучкість в оформленні.

2. **Обробка помилок:** Рекомендуємо обгортати виклик функції в try-except блок:

   ```python
   try:
       send_admin_notification(message)
   except Exception as e:
       logger.error(f"Помилка при відправці сповіщення: {e}")
   ```

3. **HTML-форматування:** Telegram підтримує HTML-теги: `<b>`, `<i>`, `<u>`, `<s>`, `<a>`, `<code>`, `<pre>`. Ви можете використовувати їх у своїх повідомленнях.

## Приклад з форматуванням HTML

```python
message = (
    f"<b>Заголовок повідомлення</b>\n\n"
    f"Перший рядок\n"
    f"Другий рядок з <i>курсивом</i>\n"
    f"<a href='https://example.com'>Посилання</a>"
)
send_admin_notification(message)
```

## Шаблони для формування повідомлень

Для зручності ви можете використовувати шаблони з директорії `notifications/templates/`:

```python
# Приклад формування повідомлення для оплати
def format_payment_message(payment):
    return (
        f"💰 <b>Нова оплата отримана</b>\n\n"
        f"🆔 ID оплати: {payment.id}\n"
        f"👤 Користувач: {payment.user.email}\n"
        f"💵 Сума: ${payment.amount}\n"
        f"📅 Дата: {payment.date}\n"
        f"✅ Статус: {payment.status}"
    )

# А потім використовуєте функцію відправки:
send_admin_notification(format_payment_message(payment))
```

## Приклади використання

Для детальніших прикладів дивіться файл `notifications/README.md`.
