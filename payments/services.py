import os
from datetime import timedelta
from decimal import Decimal

import stripe
from django.urls import reverse
from django.utils import timezone
from rest_framework.request import Request

from borrowings.models import Borrowing
from payments.models import Payment

stripe.api_key = os.environ.get("STRIPE_SECRET_KEY")
currency = os.environ.get("DEFAULT_CURRENCY", "usd")
expiration_minutes = os.environ.get("EXPIRATION_MINUTES", 30)
fine_multiplier = os.environ.get("FINE_MULTIPLIER", "0.3")


def calc_borrowing_total_price(borrowing: Borrowing):
    borrowing_period = (borrowing.expected_return - borrowing.borrow_date).days
    return borrowing_period * borrowing.book.daily_fee


def calc_borrowing_fine_price(
    borrowing: Borrowing,
    fine_multiplier: str = fine_multiplier,
):
    overdue_days = (borrowing.actual_return - borrowing.expected_return).days
    fine = overdue_days * int(
        (
            str(Decimal(borrowing.book.daily_fee) * Decimal(fine_multiplier))
        ).split(".")[0]
    )
    return fine


def create_stripe_session(
    borrowing: Borrowing,
    borrowing_total_price: int,
    request: Request,
) -> stripe.checkout.Session:
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
        expires_at=int(
            (
                timezone.now() + timedelta(minutes=expiration_minutes)
            ).timestamp()
        ),
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
    )

    return payment


def update_payment_by_session_id(session_id: str):
    try:
        session = stripe.checkout.Session.retrieve(session_id)
    except stripe._error.InvalidRequestError:
        return None

    if session.payment_status == "paid":
        payment = Payment.objects.get(session_id=session_id)
        payment.status = Payment.Statuses.PAID
        payment.save()

        return Payment

    return None
