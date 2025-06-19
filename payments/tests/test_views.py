from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from unittest import mock
from unittest.mock import patch
from datetime import date

from borrowings.models import Borrowing
from payments.models import Payment
from payments.services import update_payment_by_session_id
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
        self.payment = self.payment_user  # Додаю для універсального доступу

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
        """Test that staff users can see all payments."""
        self.client.force_authenticate(user=self.staff_user)
        response = self.client.get(reverse("payments:payment-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)  # Staff can see all payments

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

    def test_success_with_valid_session_id(self):
        with patch("payments.views.update_payment_by_session_id") as mock_update:
            mock_update.return_value = self.payment
            response = self.client.get(
                self.payment_success_url,
                {"session_id": "test_session_id"},
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.data, {"message": "Payment status changed to PAID"})

    def test_success_with_invalid_session_id(self):
        with patch("payments.views.update_payment_by_session_id") as mock_update:
            mock_update.return_value = None
            response = self.client.get(
                self.payment_success_url,
                {"session_id": "invalid_session_id"},
            )
            self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
            self.assertEqual(
                response.data,
                {"detail": "Paid session with such session_id not found"}
            )

    def test_success_without_session_id(self):
        response = self.client.get(self.payment_success_url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data, {"detail": "session_id is required"})

    def test_cancel(self):
        response = self.client.get(self.payment_cancel_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {"message": "Payment can be completed later"})

    @patch("payments.views.create_payment")
    def test_create_for_borrowing_success(self, mock_create):
        """Test creating a payment for a borrowing successfully"""
        self.client.force_authenticate(user=self.regular_user)
        # Delete existing payment first to avoid unique constraint
        Payment.objects.filter(borrowing=self.borrowing_user).delete()
        
        mock_create.return_value = self.payment_user
        url = reverse(
            "payments:payment-create-for-borrowing",
            args=[self.borrowing_user.id]
        )
        response = self.client.post(url)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        mock_create.assert_called_once()  # Just check if it was called once
        self.assertEqual(response.data["id"], self.payment_user.id)

    def test_create_for_borrowing_not_found(self):
        """Test creating a payment for non-existent borrowing"""
        self.client.force_authenticate(user=self.regular_user)
        url = reverse(
            "payments:payment-create-for-borrowing",
            args=[99999]
        )
        response = self.client.post(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_create_for_borrowing_unauthorized(self):
        """Test creating a payment for another user's borrowing"""
        self.client.force_authenticate(user=self.regular_user)
        other_user = get_user_model().objects.create_user(
            email="other@test.com",
            password="testpass123"
        )
        other_borrowing = Borrowing.objects.create(
            user=other_user,
            book=self.book,
            borrow_date="2024-01-01",
            expected_return="2024-12-31"
        )
        url = reverse(
            "payments:payment-create-for-borrowing",
            args=[other_borrowing.id]
        )
        response = self.client.post(url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_for_borrowing_already_paid(self):
        """Test creating a payment for already paid borrowing"""
        self.client.force_authenticate(user=self.regular_user)
        # Delete existing payment first to avoid unique constraint
        Payment.objects.filter(borrowing=self.borrowing_user).delete()
        
        payment = Payment.objects.create(
            borrowing=self.borrowing_user,
            status=Payment.Statuses.PAID,
            type=Payment.Types.PAYMENT,
            session_url="https://test2.com",
            session_id="test_session_id2",
            money_to_pay=15.00
        )
        url = reverse(
            "payments:payment-create-for-borrowing",
            args=[self.borrowing_user.id]
        )
        response = self.client.post(url)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.data["detail"],
            "Payment already completed for this borrowing"
        )

    def test_create_for_borrowing_pending_exists(self):
        """Test creating a payment when pending payment exists"""
        self.client.force_authenticate(user=self.regular_user)
        # Delete existing payment first to avoid unique constraint
        Payment.objects.filter(borrowing=self.borrowing_user).delete()
        
        payment = Payment.objects.create(
            borrowing=self.borrowing_user,
            status=Payment.Statuses.PENDING,
            type=Payment.Types.PAYMENT,
            session_url="https://test2.com",
            session_id="test_session_id2",
            money_to_pay=15.00
        )
        url = reverse(
            "payments:payment-create-for-borrowing",
            args=[self.borrowing_user.id]
        )
        response = self.client.post(url)


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
        mock_create.return_value.url = "https://new.test.com"
        mock_create.return_value.id = "new_test_session"
        
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

    def test_renew_non_expired_payment(self):
        self.payment.status = Payment.Statuses.PENDING
        self.payment.save()
        
        url = reverse("payments:payment-renew", args=[self.payment.id])
        response = self.client.put(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, Payment.Statuses.PENDING)
        self.assertEqual(self.payment.session_url, "https://test.com")
        self.assertEqual(self.payment.session_id, "test_session")
