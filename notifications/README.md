# Notifications App

This Django application is responsible for generating and sending notifications in the system.
It serves as a central point for initiating various notifications that can then be processed by different services (for example, a Telegram bot).

## Key Features

- **Notification Generation**: Creates messages based on system events (for example, daily checks for overdue books).
- **Message Queue Integration**: Sends notifications to a Redis queue, from which they can be retrieved by other workers.
- **Asynchronous Sending**: Ability to send notifications asynchronously using Celery.

## How It Works

1.  Other parts of the Django project (or scheduled tasks) call functions from `notifications.handlers`.
2.  Handlers format the message and pass it either directly to Redis (for immediate processing) or through Celery (for background processing).
3.  Messages in the Redis queue have the following JSON format (example):
    ```json
    {
      "telegram_ids": [123456789, 987654321],
      "text": "Your notification text"
    }
    ```

## Configuration

Most settings (Redis URL, queue name) are managed centrally through `config/settings.py` and the corresponding environment variables in the main `.env` file of the project.

- `REDIS_HOST`, `REDIS_PORT`, `REDIS_DB`, `REDIS_PASSWORD`: Redis connection parameters.
- `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND`: Celery settings.
- `NOTIFICATIONS_QUEUE`: The name of the Redis queue used for notifications.
- `LOG_LEVEL_NOTIFICATIONS`: Logging level for this application.

## Usage for Different Modules

### General Usage

To send a notification from any part of the Django project:

```python
from notifications.handlers import send_telegram_notification_django

# Example of sending (assuming telegram_ids is a list of chat/user IDs)
user_telegram_ids = [123456789]
message_text = "Your order has been updated!"

# Sending via Celery (recommended for most cases)
send_telegram_notification_django(
    telegram_ids=user_telegram_ids,
    text=message_text,
    use_celery=True
)

# Sending directly to Redis (if Celery is not configured or for specific cases)
send_telegram_notification_django(
    telegram_ids=user_telegram_ids,
    text=message_text,
    use_celery=False
)
```

### For the Borrowings Module

Already implemented functions:

```python
from notifications.handlers import notify_new_borrowing, notify_book_returned
from borrowings.models import Borrowing

# When a user creates a new borrowing:
borrowing = Borrowing.objects.get(id=1)
notify_new_borrowing(borrowing)

# When a book is returned:
borrowing = Borrowing.objects.get(id=1)
notify_book_returned(borrowing)
```

### For the Payments Module

Example integration for the payments module:

```python
from notifications.handlers import send_telegram_notification_django
from django.conf import settings

def notify_payment_received(payment):
    """
    Sends a notification about payment receipt

    Args:
        payment: Payment object with payment information

    Returns:
        bool: Result of sending the message
    """
    try:
        # Get admin IDs from settings
        admin_chat_id = getattr(settings, "TELEGRAM_ADMIN_CHAT_ID", None)

        if not admin_chat_id:
            return False

        # Format HTML message
        message = (
            f"💰 <b>New payment received</b>\n\n"
            f"🆔 Payment ID: {payment.id}\n"
            f"👤 User: {payment.user.email}\n"
            f"📚 Borrowing: {payment.borrowing.book.title}\n"
            f"💵 Amount: ${payment.amount}\n"
            f"📅 Date: {payment.date}\n"
            f"✅ Status: {payment.status}"
        )

        # Send message
        return send_telegram_notification_django([admin_chat_id], message)
    except Exception as e:
        # Log error
        return False
```

### For the Accounts Module

Here's an example for notifications about new users:

```python
from notifications.handlers import send_telegram_notification_django
from django.conf import settings

def notify_new_user_registered(user):
    """
    Sends a notification about a new user registration

    Args:
        user: User object who just registered

    Returns:
        bool: Result of sending the message
    """
    try:
        admin_chat_id = getattr(settings, "TELEGRAM_ADMIN_CHAT_ID", None)

        if not admin_chat_id:
            return False

        message = (
            f"👤 <b>New user registered</b>\n\n"
            f"📧 Email: {user.email}\n"
            f"👤 Name: {user.username}\n"
            f"📅 Registration date: {user.date_joined.strftime('%Y-%m-%d %H:%M')}"
        )

        return send_telegram_notification_django([admin_chat_id], message)
    except Exception as e:
        return False
```

## Creating Custom Notification Handlers

To add your own notification handler for your module, it's recommended to:

1. Create a `notifications.py` file in your app
2. Add functions for generating necessary messages
3. Call these functions from the appropriate places in your code

**Example structure for the payments module**:

```python
# payments/notifications.py
from notifications.handlers import send_telegram_notification_django
from django.conf import settings

def notify_payment_received(payment):
    # Your handler code...
    pass

def notify_payment_failed(payment, error_message):
    # Your handler code...
    pass
```

## Testing

To run tests specific to this app, execute the following command from the project root directory:

```bash
python manage.py test notifications
```
