from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from borrowings.models import Borrowing
from books.models import Book, Author

User = get_user_model()


class BorrowingFiltersTests(TestCase):
    def setUp(self):
        self.client = APIClient()

        self.staff_user = User.objects.create_user(
            email="admin@example.com",
            password="adminpass",
            is_staff=True,
        )
        self.user1 = User.objects.create_user(
            email="user1@example.com",
            password="userpass1",
        )
        self.user2 = User.objects.create_user(
            email="user2@example.com",
            password="userpass2",
        )

        self.author = Author.objects.create(first_name="Test", last_name="Author")
        self.book = Book.objects.create(
            title="Sample Book",
            cover=Book.Covers.HARD,
            inventory=10,
            daily_fee=5,
        )
        self.book.authors.set([self.author])

        self.borrowing_active = Borrowing.objects.create(
            user=self.user1,
            book=self.book,
            borrow_date="2023-01-01",
            expected_return="2023-01-10",
            actual_return=None,
        )
        self.borrowing_returned = Borrowing.objects.create(
            user=self.user1,
            book=self.book,
            borrow_date="2023-01-05",
            expected_return="2023-01-15",
            actual_return="2023-01-12",
        )
        self.borrowing_user2 = Borrowing.objects.create(
            user=self.user2,
            book=self.book,
            borrow_date="2023-02-01",
            expected_return="2023-02-10",
            actual_return=None,
        )

        self.borrowing_list_url = reverse("borrowings:borrowing-list")

    def test_filter_is_active_true(self):
        self.client.force_authenticate(user=self.user1)
        response = self.client.get(self.borrowing_list_url + "?is_active=true")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["id"], self.borrowing_active.id)

    def test_filter_is_active_false(self):
        self.client.force_authenticate(user=self.user1)
        response = self.client.get(self.borrowing_list_url + "?is_active=false")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["id"], self.borrowing_returned.id)

    def test_admin_filter_by_user_id(self):
        self.client.force_authenticate(user=self.staff_user)
        response = self.client.get(self.borrowing_list_url + f"?user_id={self.user1.id}")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_regular_user_ignores_user_id(self):
        self.client.force_authenticate(user=self.user1)
        response = self.client.get(self.borrowing_list_url + f"?user_id={self.user2.id}")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
