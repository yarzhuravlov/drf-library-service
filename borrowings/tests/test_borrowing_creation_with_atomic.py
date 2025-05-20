from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from django.utils.timezone import localdate, timedelta
from borrowings.models import Borrowing
from books.models import Book, Author
from django.contrib.auth import get_user_model
from unittest.mock import patch
from rest_framework.exceptions import ValidationError

User = get_user_model()


class BorrowingCreateAtomicTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(email="a@e.com", password="pass")
        author = Author.objects.create(first_name="X", last_name="Y")
        self.book = Book.objects.create(title="Z", cover=Book.Covers.SOFT, inventory=1, daily_fee=50)
        self.book.authors.add(author)
        self.url = reverse("borrowings:borrowing-list")

    @patch("borrowings.views.create_payment")
    def test_transaction_rollback_on_payment_error(self, mock_create_payment):

        mock_create_payment.side_effect = ValidationError("Simulated Stripe error")

        self.client.force_authenticate(user=self.user)
        data = {
            "book": self.book.id,
            "borrow_date": localdate(),
            "expected_return": localdate() + timedelta(days=3),
        }
        response = self.client.post(self.url, data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        self.assertFalse(Borrowing.objects.exists())

        self.book.refresh_from_db()
        self.assertEqual(self.book.inventory, 1)
