from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from django.test import TestCase
from unittest.mock import patch, MagicMock

from books.models import Book, Author
from borrowings.models import Borrowing

User = get_user_model()


class BorrowingConcurrencyTests(TestCase):
    def setUp(self):
        self.client = APIClient()

        self.staff_user = User.objects.create_user(
            email="admin@example.com", password="adminpass", is_staff=True
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
            user=self.staff_user,
            book=self.book,
            borrow_date="2025-05-18",
            expected_return="2025-05-20",
            actual_return=None,
        )

        self.return_url = reverse(
            "borrowings:borrowing-return-borrowing",
            args=[self.borrowing.id],
        )

    @patch("payments.services.create_stripe_session")
    def test_concurrent_return_attempts_only_one_successful(self, mock_session):
        mock_session.return_value = MagicMock(url="test_url", id="test_id")
        self.client.force_authenticate(user=self.staff_user)

        response1 = self.client.post(self.return_url)
        response2 = self.client.post(self.return_url)

        self.assertEqual(response1.status_code, status.HTTP_200_OK)
        self.assertEqual(response2.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn(
            "already returned",
            response2.data.get("non_field_errors", [""])[0].lower(),
        )
