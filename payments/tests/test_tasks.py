from datetime import date, timedelta

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone

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
            type=Payment.Types.PAYMENT,
            expiration_at=timezone.now() - timedelta(minutes=1)
        )

    def test_check_expired_sessions(self):
        check_expired_sessions()
        
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, Payment.Statuses.EXPIRED)

    def test_check_non_expired_sessions(self):
        self.payment.expiration_at = timezone.now() + timedelta(minutes=30)
        self.payment.save()
        
        check_expired_sessions()
        
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, Payment.Statuses.PENDING) 