from celery import shared_task
from datetime import date
from borrowings.models import Borrowing
from notifications.handlers import send_notification_to_all_admin_users


@shared_task
def check_overdue_borrowings():
    today = date.today()
    overdue_borrowings = Borrowing.objects.filter(
        expected_return__lte=today, actual_return__isnull=True
    )
    if overdue_borrowings.exists():
        for borrowing in overdue_borrowings:
            days_overdue = (today - borrowing.expected_return).days
            message = (
                f"<b>Overdue Borrowing</b>\n"
                f"ID: {borrowing.id}\n"
                f"User: {borrowing.user.email}\n"
                f"Book: {borrowing.book.title}\n"
                f"Expected Return: {borrowing.expected_return}\n"
                f"Days Overdue: {days_overdue}"
            )
            send_notification_to_all_admin_users(message)
    else:
        send_notification_to_all_admin_users(
            "<b>No borrowings overdue today!</b>"
        )
