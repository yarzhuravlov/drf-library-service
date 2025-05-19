import os
from datetime import timedelta

import stripe
from django.utils import timezone

from borrowings.models import Borrowing
from payments.models import Payment

stripe.api_key = os.environ.get("STRIPE_SECRET_KEY")
currency = os.environ.get("DEFAULT_CURRENCY", "usd")
expiration_minutes = os.environ.get("EXPIRATION_MINUTES", 30)

success_url = "http://example.com/success"
cancel_url = "http://example.com/cancel"


def calc_borrowing_total_price(borrowing: Borrowing):
    borrowing_period = (borrowing.expected_return - borrowing.borrow_date).days
    return borrowing_period * borrowing.book.daily_fee


def create_stripe_session(
    borrowing: Borrowing,
    borrowing_total_price: int,
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
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={"borrowing_id": borrowing.id},
        expires_at=int(
            (
                timezone.now() + timedelta(minutes=expiration_minutes)
            ).timestamp()
        ),
        customer_email=borrowing.user.email,
    )

    return session


def create_payment(borrowing: Borrowing) -> Payment:
    borrowing_total_price = calc_borrowing_total_price(borrowing)
    session = create_stripe_session(borrowing, borrowing_total_price)

    payment = Payment.objects.create(
        borrowing=borrowing,
        session_url=session.url,
        session_id=session.id,
        money_to_pay=borrowing_total_price,
        type=Payment.Types.PAYMENT,
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
