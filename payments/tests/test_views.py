from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from unittest.mock import patch, Mock
from datetime import date

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
        self.authors = [
            Author.objects.create(first_name="Test", last_name="Author")
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
            borrow_date=date(2024, 1, 1),
            expected_return=date(2024, 1, 10),
            actual_return=date(2024, 1, 8),
        )
        self.borrowing_another = Borrowing.objects.create(
            user=self.another_user,
            book=self.book,
            borrow_date=date(2024, 1, 1),
            expected_return=date(2024, 1, 10),
            actual_return=date(2024, 1, 9),
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
        self.payment_detail_url = reverse("payments:payment-detail", args=[self.payment_user.id])
        self.another_payment_detail_url = reverse("payments:payment-detail", args=[self.payment_another.id])
        self.payment_success_url = reverse("payments:payment-success")
        self.payment_cancel_url = reverse("payments:payment-cancel")

    def test_list_payments_unauthenticated(self):
        response = self.client.get(self.payment_list_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_payments_staff_user(self):
        self.client.force_authenticate(user=self.staff_user)
        response = self.client.get(self.payment_list_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        payment_ids = {payment["id"] for payment in response.data}
        self.assertSetEqual(payment_ids, {self.payment_user.id, self.payment_another.id})

    def test_list_payments_regular_user(self):
        self.client.force_authenticate(user=self.regular_user)
        response = self.client.get(self.payment_list_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["id"], self.payment_user.id)

    def test_retrieve_payment_unauthenticated(self):
        response = self.client.get(self.payment_detail_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_retrieve_payment_staff_user(self):
        self.client.force_authenticate(user=self.staff_user)
        response = self.client.get(self.payment_detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], self.payment_user.id)

        response = self.client.get(self.another_payment_detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], self.payment_another.id)

    def test_retrieve_payment_regular_user(self):
        self.client.force_authenticate(user=self.regular_user)
        response = self.client.get(self.payment_detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], self.payment_user.id)

        response = self.client.get(self.another_payment_detail_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_create_payment_not_allowed(self):
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
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_update_payment_not_allowed(self):
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
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_delete_payment_not_allowed(self):
        self.client.force_authenticate(user=self.staff_user)
        response = self.client.delete(self.payment_detail_url)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    @patch("payments.views.update_payment_by_session_id")
    def test_success_with_valid_session_id(self, mock_update):
        mock_update.return_value = self.payment_user

        response = self.client.get(f"{self.payment_success_url}?session_id=valid_session_id")

        mock_update.assert_called_once_with("valid_session_id")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get("message"), "Payment status changed to PAID")

    @patch("payments.views.update_payment_by_session_id")
    def test_success_with_invalid_session_id(self, mock_update):
        mock_update.return_value = None

        response = self.client.get(f"{self.payment_success_url}?session_id=invalid_session_id")

        mock_update.assert_called_once_with("invalid_session_id")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data, {"detail": "Paid session with such session_id not found"})

    def test_success_without_session_id(self):
        response = self.client.get(self.payment_success_url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data, {"detail": "session_id is required"})

    def test_cancel(self):
        response = self.client.get(self.payment_cancel_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {"message": "Payment can be completed later"})


class TestRenewPaymentView(TestCase):
    def setUp(self):
        self.client = APIClient()
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
            status=Payment.Statuses.EXPIRED,
            type=Payment.Types.PAYMENT
        )
        self.client.force_authenticate(user=self.user)

    @patch("stripe.checkout.Session.create")
    def test_renew_payment_session(self, mock_create):
        mock_session = Mock()
        mock_session.url = "https://new.test.com"
        mock_session.id = "new_test_session"
        mock_create.return_value = mock_session

        url = reverse("payments:payment-renew", args=[self.payment.id])
        response = self.client.put(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, Payment.Statuses.PENDING)
        self.assertEqual(self.payment.session_url, "https://new.test.com")
        self.assertEqual(self.payment.session_id, "new_test_session")

    def test_renew_payment_session_unauthorized(self):
        other_user = get_user_model().objects.create_user(
            email="other@test.com",
            password="testpass123"
        )
        self.client.force_authenticate(user=other_user)

        url = reverse("payments:payment-renew", args=[self.payment.id])
        response = self.client.put(url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_renew_nonexistent_payment(self):
        url = reverse("payments:payment-renew", args=[9999])
        response = self.client.put(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
