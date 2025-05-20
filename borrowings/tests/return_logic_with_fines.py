from unittest.mock import patch, MagicMock
from decimal import Decimal

from django.utils import timezone

from django.test import TestCase
from rest_framework.test import APIRequestFactory

from borrowings.models import Borrowing
from books.models import Book, Author
from payments.models import Payment
from payments.services import (
    calc_borrowing_total_price,
    calc_borrowing_fine_price,
    create_stripe_session,
    create_payment,
    create_fine_payment,
    fine_multiplier,
)


class PaymentServicesTests(TestCase):
    def setUp(self):
        # Request factory to build a dummy Request
        factory = APIRequestFactory()
        self.request = factory.get("/")
        # Create a user, book, borrowing
        from django.contrib.auth import get_user_model
        User = get_user_model()
        self.user = User.objects.create_user(email="u@e.com", password="p")
        self.author = Author.objects.create(first_name="A", last_name="B")
        self.book = Book.objects.create(
            title="T", cover=Book.Covers.HARD, inventory=5, daily_fee=10
        )
        self.book.authors.add(self.author)

    def test_calc_borrowing_total_price(self):
        b = Borrowing.objects.create(
            user=self.user,
            book=self.book,
            borrow_date=timezone.now().date(),
            expected_return=timezone.now().date() + timezone.timedelta(days=4),
            actual_return=None,
        )
        # 4 days × $10 = $40
        assert calc_borrowing_total_price(b) == 4 * 10

    def test_calc_borrowing_fine_price_rounds_and_applies_multiplier(self):
        # set actual_return 3 days after expected
        borrow_date = timezone.now().date() - timezone.timedelta(days=7)
        expected = timezone.now().date() - timezone.timedelta(days=3)
        b = Borrowing.objects.create(
            user=self.user,
            book=self.book,
            borrow_date=borrow_date,
            expected_return=expected,
            actual_return=expected + timezone.timedelta(days=3),
        )
        # raw fee = 3 * 10 = 30; multiplier default as string
        m = Decimal(str(fine_multiplier))
        expected_fine = int((Decimal(b.book.daily_fee) * m) * 3)
        assert calc_borrowing_fine_price(b) == expected_fine

    @patch("payments.services.stripe.checkout.Session.create")
    def test_create_stripe_session_parameters(self, mock_create):
        # Arrange
        mock_session = MagicMock()
        mock_session.url = "https://fake/checkout"
        mock_session.id = "sess_123"
        mock_create.return_value = mock_session

        b = Borrowing.objects.create(
            user=self.user,
            book=self.book,
            borrow_date=timezone.now().date(),
            expected_return=timezone.now().date() + timezone.timedelta(days=1),
            actual_return=None,
        )
        total_price = calc_borrowing_total_price(b)

        # Act
        sess = create_stripe_session(b, total_price, self.request)

        # Assert stripe called with correct args
        mock_create.assert_called_once()
        args, kwargs = mock_create.call_args
        # Check line_items
        li = kwargs["line_items"][0]
        assert li["price_data"]["unit_amount"] == total_price
        assert kwargs["mode"] == "payment"
        assert "session_id" in kwargs["success_url"]
        assert kwargs["cancel_url"].startswith("http://testserver/")
        # Return value
        assert sess.url == mock_session.url
        assert sess.id == mock_session.id

    @patch("payments.services.create_stripe_session")
    def test_create_payment_creates_model(self, mock_session_fn):
        # Arrange
        fake = MagicMock(url="u", id="i")
        mock_session_fn.return_value = fake

        b = Borrowing.objects.create(
            user=self.user,
            book=self.book,
            borrow_date=timezone.now().date(),
            expected_return=timezone.now().date() + timezone.timedelta(days=2),
            actual_return=None,
        )

        # Act
        payment = create_payment(b, self.request)

        # Assert
        mock_session_fn.assert_called_once_with(b, calc_borrowing_total_price(b), self.request)
        assert isinstance(payment, Payment)
        assert payment.session_url == fake.url
        assert payment.session_id == fake.id
        assert payment.type == Payment.Types.PAYMENT
        assert payment.money_to_pay == calc_borrowing_total_price(b)

    @patch("payments.services.create_stripe_session")
    def test_create_fine_payment_creates_fine_model(self, mock_session_fn):
        # Arrange
        fake = MagicMock(url="u2", id="i2")
        mock_session_fn.return_value = fake

        # Create a borrowing with actual_return > expected_return
        borrow_date = timezone.now().date() - timezone.timedelta(days=5)
        expected = timezone.now().date() - timezone.timedelta(days=3)
        b = Borrowing.objects.create(
            user=self.user,
            book=self.book,
            borrow_date=borrow_date,
            expected_return=expected,
            actual_return=expected + timezone.timedelta(days=2),
        )

        # Act
        payment = create_fine_payment(b, self.request)

        # Assert service called with correct fine amount
        fine_amt = calc_borrowing_fine_price(b)
        mock_session_fn.assert_called_once_with(b, fine_amt, self.request)

        assert isinstance(payment, Payment)
        assert payment.type == Payment.Types.FINE
        assert payment.money_to_pay == fine_amt
        assert payment.session_url == fake.url
        assert payment.session_id == fake.id
