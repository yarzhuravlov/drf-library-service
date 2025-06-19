from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from unittest.mock import patch, MagicMock

from borrowings.models import Borrowing
from books.models import Book, Author

User = get_user_model()


class BorrowingReturnTests(TestCase):
    def setUp(self):
        self.client = APIClient()

        self.staff_user = User.objects.create_user(
            email="admin@example.com",
            password="adminpass",
            is_staff=True,
        )
        self.regular_user = User.objects.create_user(
            email="user@example.com",
            password="userpass",
        )

        self.author = Author.objects.create(
            first_name="Test", last_name="Author"
        )
        self.book = Book.objects.create(
            title="Sample Book",
            cover=Book.Covers.HARD,
            inventory=10,
            daily_fee=5,
        )
        self.book.authors.set([self.author])

        self.borrowing = Borrowing.objects.create(
            user=self.regular_user,
            book=self.book,
            borrow_date="2025-05-18",
            expected_return="2025-05-20",
            actual_return=None,
        )

        self.return_url = reverse(
            "borrowings:borrowing-return-borrowing", args=[self.borrowing.id]
        )

    @patch("payments.services.create_stripe_session")
    def test_admin_can_return_borrowing(self, mock_session):
        mock_session.return_value = MagicMock(url="test_url", id="test_id")
        self.client.force_authenticate(user=self.staff_user)
        prev_inventory = self.book.inventory

        response = self.client.post(self.return_url)

        self.borrowing.refresh_from_db()
        self.book.refresh_from_db()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNotNone(self.borrowing.actual_return)
        self.assertEqual(self.book.inventory, prev_inventory + 1)

    def test_regular_user_cannot_return_borrowing(self):
        self.client.force_authenticate(user=self.regular_user)
        response = self.client.post(self.return_url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @patch("payments.services.create_stripe_session")
    def test_cannot_return_twice(self, mock_session):
        mock_session.return_value = MagicMock(url="test_url", id="test_id")
        self.client.force_authenticate(user=self.staff_user)
        self.client.post(self.return_url)

        response2 = self.client.post(self.return_url)
        self.assertEqual(response2.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response2.data["non_field_errors"][0],
            "This borrowing is already returned.",
        )
