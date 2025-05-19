from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from borrowings.models import Borrowing
from payments.models import Payment
from books.models import Book, Author


class PaymentViewSetTests(TestCase):
    def setUp(self):
        self.client = APIClient()

        # Create users
        self.staff_user = get_user_model().objects.create_user(
            email="staff@example.com",
            password="testpassword",
            is_staff=True,
        )

        self.regular_user = get_user_model().objects.create_user(
            email="user@example.com",
            password="testpassword",
        )

        self.another_user = get_user_model().objects.create_user(
            email="another@example.com",
            password="testpassword",
        )

        # Create an author
        self.author = Author.objects.create(
            first_name="Test",
            last_name="Author",
        )

        # Create a book
        self.book = Book.objects.create(
            title="Test Book",
            author=self.author,
            cover=Book.Covers.HARD,
            inventory=5,
            daily_fee=10,
        )

        # Create borrowings
        self.borrowing_user = Borrowing.objects.create(
            user=self.regular_user,
            book=self.book,
            borrow_date="2023-01-01",
            expected_return="2023-01-10",
            actual_return="2023-01-08",
        )

        self.borrowing_another = Borrowing.objects.create(
            user=self.another_user,
            book=self.book,
            borrow_date="2023-01-01",
            expected_return="2023-01-10",
            actual_return="2023-01-09",
        )

        # Create payments
        self.payment_user = Payment.objects.create(
            borrowing=self.borrowing_user,
            session_url="https://example.com/session/1",
            session_id="session_1",
            money_to_pay=100,
            status=Payment.Statuses.PENDING,
            type=Payment.Types.PAYMENT,
        )

        self.payment_another = Payment.objects.create(
            borrowing=self.borrowing_another,
            session_url="https://example.com/session/2",
            session_id="session_2",
            money_to_pay=150,
            status=Payment.Statuses.PAID,
            type=Payment.Types.FINE,
        )

        # URLs
        self.payment_list_url = reverse("payments:payment-list")
        self.payment_detail_url = reverse(
            "payments:payment-detail",
            args=[self.payment_user.id],
        )
        self.another_payment_detail_url = reverse(
            "payments:payment-detail",
            args=[self.payment_another.id],
        )

    def test_list_payments_unauthenticated(self):
        """Test that unauthenticated users cannot access the payments list"""
        response = self.client.get(self.payment_list_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_payments_staff_user(self):
        """Test that staff users can see all payments"""
        self.client.force_authenticate(user=self.staff_user)
        response = self.client.get(self.payment_list_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)  # Staff can see all payments

    def test_list_payments_regular_user(self):
        """Test that regular users can only see their own payments"""
        self.client.force_authenticate(user=self.regular_user)
        response = self.client.get(self.payment_list_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            len(response.data), 1
        )  # Regular user can only see their payments
        self.assertEqual(response.data[0]["id"], self.payment_user.id)

    def test_retrieve_payment_unauthenticated(self):
        """Test that unauthenticated users cannot retrieve a payment"""
        response = self.client.get(self.payment_detail_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_retrieve_payment_staff_user(self):
        """Test that staff users can retrieve any payment"""
        self.client.force_authenticate(user=self.staff_user)

        # Staff can retrieve regular user's payment
        response = self.client.get(self.payment_detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], self.payment_user.id)

        # Staff can retrieve another user's payment
        response = self.client.get(self.another_payment_detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], self.payment_another.id)

    def test_retrieve_payment_regular_user(self):
        """Test that regular users can only retrieve their own payments"""
        self.client.force_authenticate(user=self.regular_user)

        # Regular user can retrieve their own payment
        response = self.client.get(self.payment_detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], self.payment_user.id)

        # Regular user cannot retrieve another user's payment
        response = self.client.get(self.another_payment_detail_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_create_payment_not_allowed(self):
        """Test that POST method is not allowed for payments endpoint"""
        self.client.force_authenticate(user=self.staff_user)
        response = self.client.post(
            self.payment_list_url,
            {
                "borrowing": self.borrowing_user.id,
                "session_url": "https://example.com/session/3",
                "session_id": "session_3",
                "money_to_pay": 200,
                "status": Payment.Statuses.PENDING,
                "type": Payment.Types.PAYMENT,
            },
        )
        self.assertEqual(
            response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED
        )

    def test_update_payment_not_allowed(self):
        """Test that PUT method is not allowed for payments endpoint"""
        self.client.force_authenticate(user=self.staff_user)
        response = self.client.put(
            self.payment_detail_url,
            {
                "borrowing": self.borrowing_user.id,
                "session_url": "https://example.com/session/updated",
                "session_id": "session_updated",
                "money_to_pay": 300,
                "status": Payment.Statuses.PAID,
                "type": Payment.Types.PAYMENT,
            },
        )
        self.assertEqual(
            response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED
        )

    def test_delete_payment_not_allowed(self):
        """Test that DELETE method is not allowed for payments endpoint"""
        self.client.force_authenticate(user=self.staff_user)
        response = self.client.delete(self.payment_detail_url)
        self.assertEqual(
            response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED
        )
