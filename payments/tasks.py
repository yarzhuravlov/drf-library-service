from celery import shared_task
from django.utils import timezone

from payments.models import Payment


@shared_task
def check_expired_sessions() -> None:
    """Check for expired payment sessions and update their statuses."""
    pending_payments = Payment.objects.filter(
        status=Payment.Statuses.PENDING,
        expiration_at__lte=timezone.now(),
    )
    pending_payments.update(status=Payment.Statuses.EXPIRED)
