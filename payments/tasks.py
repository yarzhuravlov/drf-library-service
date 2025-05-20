import stripe
from celery import shared_task

from payments.models import Payment


@shared_task
def check_expired_sessions() -> None:
    """Check for expired Stripe sessions and update payment statuses."""
    pending_payments = Payment.objects.filter(status=Payment.Statuses.PENDING)

    for payment in pending_payments:
        try:
            session = stripe.checkout.Session.retrieve(payment.session_id)
            if session.status == "expired":
                payment.status = Payment.Statuses.EXPIRED
                payment.save()
        except stripe.error.StripeError:
            continue
