from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from unittest import mock

from borrowings.models import Borrowing
from payments.models import Payment
from payments.services import update_payment_by_session_id
from books.models import Book, Author


class PaymentViewSetTests(TestCase):
    def setUp(self):
        self.client = APIClient()

        # Create users
        self.staff_user = get_user_model().objects.create_user(
            username="staff@example.com",
            password="testpassword",
            is_staff=True,
        )

        self.regular_user = get_user_model().objects.create_user(
            username="user@example.com",
            password="testpassword",
        )

        self.another_user = get_user_model().objects.create_user(
            username="another@example.com",
            password="testpassword",
        )

        # Create an author
        self.authors = [
            Author.objects.create(
                first_name="Test",
                last_name="Author",
            )
        ]

        # Create a book
        self.book = Book.objects.create(
            title="Test Book",
            cover=Book.Covers.HARD,
            inventory=5,
            daily_fee=10,
        )

        self.book.authors.set(self.authors)

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
        self.payment_success_url = reverse("payments:payment-success")
        self.payment_cancel_url = reverse("payments:payment-cancel")

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

    @mock.patch("payments.views.update_payment_by_session_id")
    def test_success_with_valid_session_id(self, mock_update):
        """Test success action with a valid session_id"""
        mock_update.return_value = Payment

        response = self.client.get(
            f"{self.payment_success_url}?session_id=valid_session_id"
        )

        mock_update.assert_called_once_with("valid_session_id")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, "Payment status changed to PAID")

    @mock.patch("payments.views.update_payment_by_session_id")
    def test_success_with_invalid_session_id(self, mock_update):
        """Test success action with an invalid session_id"""
        mock_update.return_value = None

        response = self.client.get(
            f"{self.payment_success_url}?session_id=invalid_session_id"
        )

        mock_update.assert_called_once_with("invalid_session_id")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(
            response.data, "Paid session with such session_id not found"
        )

    def test_success_without_session_id(self):
        """Test success action without providing a session_id"""
        response = self.client.get(self.payment_success_url)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data, "session_id is required")

    def test_cancel(self):
        """Test cancel action"""
        response = self.client.get(self.payment_cancel_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, "Payment can be completed later")
