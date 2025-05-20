from unittest.mock import patch
from datetime import date

from django.test import TestCase
from django.contrib.auth import get_user_model

from borrowings.models import Borrowing
from books.models import Book
from payments.models import Payment
from payments.tasks import check_expired_sessions


class TestCheckExpiredSessions(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email="test@test.com",
            password="testpass123"
        )
        self.book = Book.objects.create(
            title="Test Book",
            daily_fee=10,
            inventory=5,
            cover=Book.Covers.HARD
        )
        self.borrowing = Borrowing.objects.create(
            book=self.book,
            user=self.user,
            borrow_date=date(2024, 1, 1),
            expected_return=date(2024, 1, 10)
        )
        self.payment = Payment.objects.create(
            borrowing=self.borrowing,
            session_url="https://test.com",
            session_id="test_session",
            money_to_pay=100,
            status=Payment.Statuses.PENDING,
            type=Payment.Types.PAYMENT
        )

    @patch("stripe.checkout.Session.retrieve")
    def test_check_expired_sessions(self, mock_retrieve):
        mock_retrieve.return_value.status = "expired"
        
        check_expired_sessions()
        
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, Payment.Statuses.EXPIRED)

    @patch("stripe.checkout.Session.retrieve")
    def test_check_non_expired_sessions(self, mock_retrieve):
        mock_retrieve.return_value.status = "open"
        
        check_expired_sessions()
        
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, Payment.Statuses.PENDING) 