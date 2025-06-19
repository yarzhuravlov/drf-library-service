import os

from celery import Celery
from celery.schedules import crontab

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("config")

app.config_from_object("django.conf:settings", namespace="CELERY")

app.autodiscover_tasks()

app.conf.beat_schedule = {
    "check-expired-sessions": {
        "task": "payments.tasks.check_expired_sessions",
        "schedule": crontab(minute="*"),  # every minute
    },
    "check-overdue-borrowings-every-day": {
        "task": "borrowings.tasks.check_overdue_borrowings",
        "schedule": crontab(hour=0, minute=0),  # every day at midnight
    },
}


@app.task(bind=True)
def debug_task(self):
    print(f"Request: {self.request!r}")
