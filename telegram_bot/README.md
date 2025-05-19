# Library Service API

Система управління бібліотекою на Django REST Framework.

## Встановлення

1. Склонуйте репозиторій
2. Створіть та активуйте віртуальне середовище

```
python -m venv venv
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate  # Windows
```

3. Встановіть залежності

```
pip install -r requirements.txt
```

4. Скопіюйте файл `.env.sample` до `.env` та налаштуйте змінні середовища
5. Застосуйте міграції

```
python manage.py migrate
```

6. Запустіть сервер

```
python manage.py runserver
```

## Система сповіщень

Система сповіщень складається з двох компонентів:

1. **notifications** - Django додаток, який відправляє повідомлення у чергу Redis
2. **telegram_bot** - Воркер-процес, який слухає чергу Redis та відправляє повідомлення через Telegram API

### Налаштування

1. Створіть бота в Telegram через [@BotFather](https://t.me/BotFather) та отримайте токен
2. Додайте токен у файл `.env`:

```
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
```

3. Переконайтеся, що Redis сервер запущений
4. Запустіть воркер Telegram бота:

```
python telegram_bot/run_worker.py
```

### Відправка сповіщень

Для відправки сповіщень використовуйте функцію `send_telegram_notification_django` з модуля `notifications.handlers`:

```python
from notifications.handlers import send_telegram_notification_django

# Відправка через Celery (асинхронно)
send_telegram_notification_django(
    telegram_ids=[123456789],  # ID користувача або чату в Telegram
    text="Привіт, це тестове повідомлення!",
    use_celery=True
)

```
