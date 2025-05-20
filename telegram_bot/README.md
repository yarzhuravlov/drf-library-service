# Library Service API

Library management system on Django REST Framework.

## Installation

1. Clone the repository
2. Create and activate a virtual environment

```
python -m venv venv
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate  # Windows
```

3. Install dependencies

```
pip install -r requirements.txt
```

4. Copy the `.env.sample` file to `.env` and configure environment variables
5. Apply migrations

```
python manage.py migrate
```

6. Run the server

```
python manage.py runserver
```

## Notification System

The notification system consists of two components:

1. **notifications** - Django app that sends messages to a Redis queue
2. **telegram_bot** - Worker process that listens to the Redis queue and sends messages via Telegram API

### Configuration

1. Create a bot in Telegram via [@BotFather](https://t.me/BotFather) and get a token
2. Add the token to the `.env` file:

```
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
```

3. Make sure the Redis server is running
4. Run the Telegram bot worker:

```
python telegram_bot/run_worker.py
```

### Sending Notifications

To send notifications, use the `send_telegram_notification_django` function from the `notifications.handlers` module:

```python
from notifications.handlers import send_telegram_notification_django

# Sending via Celery (asynchronously)
send_telegram_notification_django(
    telegram_ids=[123456789],  # User or chat ID in Telegram
    text="Hello, this is a test message!",
    use_celery=True
)

```
