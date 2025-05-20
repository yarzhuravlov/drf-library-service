from unittest.mock import patch, MagicMock

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from django.test import TestCase
from books.models import Book, Author
from borrowings.models import Borrowing
from payments.models import Payment

User = get_user_model()

class BorrowingPendingPaymentTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user_with_pending_payment = User.objects.create_user(
            email="user_pending@example.com", password="userpass"
        )
        self.user_no_pending_payment = User.objects.create_user(
            email="user_no_pending@example.com", password="userpass"
        )
        self.author = Author.objects.create(
            first_name="Test", last_name="Author"
        )
        self.book = Book.objects.create(
            title="Sample Book",
            cover=Book.Covers.HARD,
            inventory=1,
            daily_fee=5,
        )
        self.book.authors.set([self.author])
        self.borrowing_for_pending = Borrowing.objects.create(
            user=self.user_with_pending_payment,
            book=self.book,
            borrow_date="2025-05-01",
            expected_return="2025-05-10",
        )
        self.pending_payment = Payment.objects.create(
            borrowing=self.borrowing_for_pending,
            status=Payment.Statuses.PENDING,
            type=Payment.Types.PAYMENT,
            money_to_pay=10.00,
        )
        self.borrowing_list_url = reverse("borrowings:borrowing-list")

    def test_cannot_borrow_with_pending_payments(self):
        self.client.force_authenticate(user=self.user_with_pending_payment)
        response = self.client.post(
            self.borrowing_list_url,
            data={
                "book": self.book.id,
                "borrow_date": "2025-05-15",
                "expected_return": "2025-05-25",
            },
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("detail", response.data)
        self.assertEqual(
            response.data["detail"],
            "You have pending payments. Please settle them before borrowing another book.",
        )
        self.book.refresh_from_db()
        self.assertEqual(self.book.inventory, 1)

    @patch("borrowings.views.create_payment")
    def test_can_borrow_without_pending_payments(self, mock_create_payment):
        mock_create_payment.return_value = MagicMock()
        self.client.force_authenticate(user=self.user_no_pending_payment)
        self.assertFalse(
            Payment.objects.filter(
                borrowing__user=self.user_no_pending_payment,
                status=Payment.Statuses.PENDING,
            ).exists()
        )
        prev_inventory = self.book.inventory
        response = self.client.post(
            self.borrowing_list_url,
            data={
                "book": self.book.id,
                "borrow_date": "2025-05-15",
                "expected_return": "2025-05-25",
            },
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.book.refresh_from_db()
        self.assertEqual(self.book.inventory, prev_inventory - 1)
