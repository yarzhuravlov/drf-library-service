default_app_config = "notifications.apps.NotificationsConfig"

from notifications.tasks import send_notification_celery  # noqa
