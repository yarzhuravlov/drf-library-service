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


class BorrowingBusinessLogicTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email="user@example.com", password="userpass"
        )
        self.user_no_pending_payment = User.objects.create_user(
            email="no_pending@example.com", password="password123"
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
        self.borrowing_list_url = reverse("borrowings:borrowing-list")

    def test_cannot_borrow_if_inventory_zero(self):
        self.book.inventory = 0
        self.book.save()
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            self.borrowing_list_url,
            data={
                "book": self.book.id,
                "borrow_date": "2025-05-01",
                "expected_return": "2025-05-10",
            },
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("book", response.data)
        self.assertIn("not available", response.data["book"][0].lower())

    @patch("borrowings.views.create_payment")
    def test_inventory_decreases_on_borrow(self, mock_create_payment):
        mock_create_payment.return_value = MagicMock()
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            self.borrowing_list_url,
            data={
                "book": self.book.id,
                "borrow_date": "2025-05-01",
                "expected_return": "2025-05-10",
            },
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.book.refresh_from_db()
        self.assertEqual(self.book.inventory, 0)
