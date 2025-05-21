from datetime import timedelta

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.utils import timezone

from books.models import Book
from borrowings.models import Borrowing
from payments.models import Payment


class PaymentModelTests(TestCase):
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
            borrow_date=timezone.now().date(),
            expected_return=timezone.now().date() + timedelta(days=7)
        )
        self.payment = Payment.objects.create(
            borrowing=self.borrowing,
            session_url="https://test.com",
            session_id="test_session",
            money_to_pay=100,
            type=Payment.Types.PAYMENT,
            status=Payment.Statuses.PENDING,
            expiration_at=timezone.now() + timedelta(minutes=30)
        )

    def test_payment_str_representation(self):
        """Test the string representation of the Payment model."""
        expected_str = f"Payment by {self.user.email}."
        self.assertEqual(str(self.payment), expected_str)

    def test_payment_is_expired_true(self):
        """Test is_expired method returns True for expired payments."""
        self.payment.expiration_at = timezone.now() - timedelta(minutes=1)
        self.payment.save()
        self.assertTrue(self.payment.is_expired())

    def test_payment_is_expired_false(self):
        """Test is_expired method returns False for non-expired payments."""
        self.payment.expiration_at = timezone.now() + timedelta(minutes=30)
        self.payment.save()
        self.assertFalse(self.payment.is_expired())

    def test_unique_type_borrowing_constraint(self):
        """Test that we cannot create two payments of the same type
        for one borrowing."""
        with self.assertRaises(IntegrityError):
            Payment.objects.create(
                borrowing=self.borrowing,
                session_url="https://test2.com",
                session_id="test_session2",
                money_to_pay=100,
                type=Payment.Types.PAYMENT,
                status=Payment.Statuses.PENDING,
                expiration_at=timezone.now() + timedelta(minutes=30)
            )

    def test_can_create_different_type_payments(self):
        """Test that we can create payments of different types
        for one borrowing."""
        fine_payment = Payment.objects.create(
            borrowing=self.borrowing,
            session_url="https://test2.com",
            session_id="test_session2",
            money_to_pay=100,
            type=Payment.Types.FINE,
            status=Payment.Statuses.PENDING,
            expiration_at=timezone.now() + timedelta(minutes=30)
        )
        self.assertEqual(
            Payment.objects.filter(borrowing=self.borrowing).count(),
            2
        )
        self.assertEqual(fine_payment.type, Payment.Types.FINE)

    def test_payment_expiration_edge_cases(self):
        """Test payment expiration edge cases."""
        # Test exact current time
        now = timezone.now()
        self.payment.expiration_at = now
        self.payment.save()
        self.assertTrue(self.payment.is_expired())

        # Test future time
        self.payment.expiration_at = now + timedelta(seconds=1)
        self.payment.save()
        self.assertFalse(self.payment.is_expired())

        # Test past time
        self.payment.expiration_at = now - timedelta(seconds=1)
        self.payment.save()
        self.assertTrue(self.payment.is_expired()) 