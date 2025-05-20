import os
from datetime import timedelta
from decimal import Decimal

import stripe
from django.urls import reverse
from django.utils import timezone
from rest_framework.request import Request
from django.conf import settings

from borrowings.models import Borrowing
from payments.models import Payment

stripe.api_key = settings.STRIPE_SECRET_KEY
currency = settings.DEFAULT_CURRENCY
expiration_minutes = settings.EXPIRATION_MINUTES
fine_multiplier = settings.FINE_MULTIPLIER
MIN_AMOUNT = 50  # Stripe minimum amount in cents


def calc_borrowing_total_price(borrowing: Borrowing) -> int:
    """Calculate total price for borrowing in cents.
    Ensures the minimum amount is at least 50 cents."""
    borrowing_period = (borrowing.expected_return - borrowing.borrow_date).days
    amount = borrowing_period * borrowing.book.daily_fee * 100  # Convert to cents
    return max(amount, MIN_AMOUNT)


def calc_borrowing_fine_price(
    borrowing: Borrowing,
    fine_multiplier: str = fine_multiplier,
) -> int:
    """Calculate fine price for overdue borrowing in cents.
    Ensures the minimum amount is at least 50 cents."""
    overdue_days = (borrowing.actual_return - borrowing.expected_return).days
    fine = overdue_days * int(
        (
            str(Decimal(borrowing.book.daily_fee) * Decimal(fine_multiplier))
        ).split(".")[0]
    ) * 100  # Convert to cents
    return max(fine, MIN_AMOUNT)


def create_stripe_session(
    borrowing: Borrowing,
    borrowing_total_price: int,
    request: Request,
) -> stripe.checkout.Session:
    expiration_at = timezone.now() + timedelta(minutes=expiration_minutes)
    session = stripe.checkout.Session.create(
        line_items=[
            {
                "price_data": {
                    "currency": currency,
                    "product_data": {
                        "name": f"Borrowing #{borrowing.id}",
                    },
                    "unit_amount": borrowing_total_price,
                },
                "quantity": 1,
            }
        ],
        mode="payment",
        success_url=request.build_absolute_uri(
            reverse("payments:payment-success")
        )
        + "?session_id={CHECKOUT_SESSION_ID}",
        cancel_url=request.build_absolute_uri(
            reverse("payments:payment-cancel")
        ),
        metadata={"borrowing_id": borrowing.id},
        expires_at=int(expiration_at.timestamp()),
        customer_email=borrowing.user.email,
    )

    return session


def create_payment(borrowing: Borrowing, request: Request) -> Payment:
    borrowing_total_price = calc_borrowing_total_price(borrowing)
    session = create_stripe_session(borrowing, borrowing_total_price, request)

    payment = Payment.objects.create(
        borrowing=borrowing,
        session_url=session.url,
        session_id=session.id,
        money_to_pay=borrowing_total_price,
        type=Payment.Types.PAYMENT,
        expiration_at=timezone.now() + timedelta(minutes=expiration_minutes),
    )
    return payment


def create_fine_payment(borrowing: Borrowing, request: Request):
    fine = calc_borrowing_fine_price(borrowing)
    session = create_stripe_session(borrowing, fine, request)

    payment = Payment.objects.create(
        borrowing=borrowing,
        session_url=session.url,
        session_id=session.id,
        money_to_pay=fine,
        type=Payment.Types.FINE,
        expiration_at=timezone.now() + timedelta(minutes=expiration_minutes),
    )

    return payment


def update_payment_by_session_id(session_id: str):
    try:
        session = stripe.checkout.Session.retrieve(session_id)
    except stripe.error.InvalidRequestError:
        return None

    if session.payment_status == "paid":
        payment = Payment.objects.get(session_id=session_id)
        payment.status = Payment.Statuses.PAID
        payment.save()

        return payment

    return None


def renew_payment_session(payment: Payment, request: Request) -> Payment:
    """Create new Stripe session for expired payment."""
    if payment.status != Payment.Statuses.EXPIRED:
        return payment

    session = create_stripe_session(
        payment.borrowing,
        payment.money_to_pay,
        request
    )

    payment.session_url = session.url
    payment.session_id = session.id
    payment.status = Payment.Statuses.PENDING
    payment.expiration_at = (
        timezone.now() + timedelta(minutes=expiration_minutes)
    )
    payment.save()

    return payment
