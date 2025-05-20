# Notification Integration in Your Module

This document describes how to integrate notifications into your Django module. The main notification functions are already implemented — you just need to call them from your code and pass the prepared messages.

> **IMPORTANT:** Formatting the message text is entirely the module developer's responsibility. Notification functions only accept pre-formatted message text.

## Available Notification Functions

Start commands

celery -A config worker -l INFO --pool=solo - Celery
python -m telegram_bot.worker - worker who works with redis
python manage.py runserser - server
redis - localy

We provide three main functions for sending notifications:

### 1. Notifications for Administrators

```python
from notifications.handlers import send_notification_to_all_admin_users

# Usage example:
message = "Your message here"
send_notification_to_all_admin_users(message)
```

### 2. Notifications for Users

```python
from django.contrib.auth import get_user_model
from notifications.handlers import send_notification_to_user

User = get_user_model()
user = User.objects.get(email="email@site.com")
send_notification_to_user(user, "message")

```

### 3. Advanced Function for More Flexibility

```python
from notifications.handlers import send_user_notification

telegram_id = 123456789  # tg id
send_user_notification(telegram_id, "message")
```

## Usage in Your Code

Each module developer is responsible for formatting the message text. This text is then passed to the notification functions:

```python
# your_app/views.py or your_app/signals.py
from notifications.handlers import send_notification_to_all_admin_users, send_user_notification

def some_view(request):
    # Your code...

    # Format message for administrators
    admin_message = (
        f"<b>New action in the system</b>\n\n"
        f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
        f"User: {request.user.email}\n"
        f"Action: creating a record"
    )
    send_notification_to_all_admin_users(admin_message)

    # Format message for the user
    user_message = f"Thank you for using our service! Your request has been processed."
    user_telegram_id = get_user_telegram_id(request.user)  # Your function to get the ID
    if user_telegram_id:
        send_user_notification(user_telegram_id, user_message)

    # Continue with your code...
```

## Important Points

1. **Message Formatting:** You are fully responsible for formatting the message text. This gives you maximum flexibility in presentation.

2. **Error Handling:** We recommend wrapping the function call in a try-except block:

   ```python
   try:
       send_admin_notification(message)
   except Exception as e:
       logger.error(f"Error sending notification: {e}")
   ```

3. **HTML Formatting:** Telegram supports HTML tags: `<b>`, `<i>`, `<u>`, `<s>`, `<a>`, `<code>`, `<pre>`. You can use them in your messages.

## Example with HTML Formatting

```python
message = (
    f"<b>Message Title</b>\n\n"
    f"First line\n"
    f"Second line with <i>italics</i>\n"
    f"<a href='https://example.com'>Link</a>"
)
send_admin_notification(message)
```

## Templates for Message Formatting

For convenience, you can use templates from the `notifications/templates/` directory:

```python
# Example of formatting a payment message
def format_payment_message(payment):
    return (
        f"💰 <b>New payment received</b>\n\n"
        f"🆔 Payment ID: {payment.id}\n"
        f"👤 User: {payment.user.email}\n"
        f"💵 Amount: ${payment.amount}\n"
        f"📅 Date: {payment.date}\n"
        f"✅ Status: {payment.status}"
    )

# Then use the send function:
send_admin_notification(format_payment_message(payment))
```

## Usage Examples

For more detailed examples, see the `notifications/README.md` file.
