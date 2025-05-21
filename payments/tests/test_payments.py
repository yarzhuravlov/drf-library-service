from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase
from unittest.mock import patch

from borrowings.models import Borrowing
from books.models import Book, Author
from payments.models import Payment
from payments.serializers import PaymentSerializer


class PaymentViewSetTests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email="test@test.com",
            password="testpass123"
        )
        self.staff_user = get_user_model().objects.create_user(
            email="staff@test.com",
            password="staffpass123",
            is_staff=True
        )
        self.author = Author.objects.create(
            first_name="Test",
            last_name="Author"
        )
        self.book = Book.objects.create(
            title="Test Book",
            cover="HARD",
            inventory=1,
            daily_fee=10
        )
        self.book.authors.add(self.author)
        self.borrowing = Borrowing.objects.create(
            user=self.user,
            book=self.book,
            borrow_date="2024-01-01",
            expected_return="2024-12-31"
        )
        self.payment = Payment.objects.create(
            borrowing=self.borrowing,
            status="PENDING",
            type="PAYMENT",
            session_url="https://test.com",
            session_id="test_session_id",
            money_to_pay=15.00
        )
        self.client.force_authenticate(user=self.user)

    def test_list_payments_user(self):
        """Test that users can only see their own payments"""
        url = reverse("payments:payment-list")
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["id"], self.payment.id)

    def test_list_payments_staff(self):
        """Test that staff can see all payments"""
        self.client.force_authenticate(user=self.staff_user)
        url = reverse("payments:payment-list")
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_retrieve_payment(self):
        """Test retrieving a payment detail"""
        url = reverse("payments:payment-detail", args=[self.payment.id])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], self.payment.id)

    def test_retrieve_other_user_payment_forbidden(self):
        """Test that users cannot retrieve other users' payments"""
        other_user = get_user_model().objects.create_user(
            email="other@test.com",
            password="otherpass123"
        )
        self.client.force_authenticate(user=other_user)
        
        url = reverse("payments:payment-detail", args=[self.payment.id])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_payment_success(self):
        """Test successful payment completion."""
        with patch("payments.views.update_payment_by_session_id") as mock_update:
            mock_update.return_value = self.payment
            url = reverse("payments:payment-success")
            response = self.client.get(url, {"session_id": "test_session_id"})
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.data, {"message": "Payment status changed to PAID"})

    def test_payment_success_no_session_id(self):
        """Test payment success endpoint without session_id"""
        url = reverse("payments:payment-success")
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_payment_cancel(self):
        """Test payment cancellation"""
        url = reverse("payments:payment-cancel")
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class RenewPaymentViewTests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email="test@test.com",
            password="testpass123"
        )
        self.author = Author.objects.create(
            first_name="Test",
            last_name="Author"
        )
        self.book = Book.objects.create(
            title="Test Book",
            cover="HARD",
            inventory=1,
            daily_fee=10
        )
        self.book.authors.add(self.author)
        self.borrowing = Borrowing.objects.create(
            user=self.user,
            book=self.book,
            borrow_date="2024-01-01",
            expected_return="2024-12-31"
        )
        self.payment = Payment.objects.create(
            borrowing=self.borrowing,
            status="PENDING",
            type="PAYMENT",
            session_url="https://test.com",
            session_id="test_session_id",
            money_to_pay=15.00
        )
        self.client.force_authenticate(user=self.user)

    def test_renew_payment(self):
        """Test renewing a payment session."""
        with patch("payments.views.renew_payment_session") as mock_renew:
            mock_renew.return_value = self.payment
            url = reverse("payments:payment-renew", args=[self.payment.id])
            response = self.client.put(url)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            mock_renew.assert_called_once()

    def test_renew_other_user_payment_forbidden(self):
        """Test that users cannot renew other users' payments"""
        self.payment.status = "EXPIRED"
        self.payment.save()
        other_user = get_user_model().objects.create_user(
            email="other@test.com",
            password="otherpass123"
        )
        self.client.force_authenticate(user=other_user)
        
        url = reverse("payments:payment-renew", args=[self.payment.id])
        response = self.client.put(url)
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class WebhookTests(APITestCase):
    @patch("stripe.Webhook.construct_event")
    def test_webhook_successful_payment(self, mock_construct_event):
        """Test webhook handling for successful payment"""
        mock_event = type("Event", (), {
            "type": "checkout.session.completed",
            "data": type("Data", (), {
                "object": type("Session", (), {"id": "test_session_id"})
            })
        })
        mock_construct_event.return_value = mock_event
        
        url = reverse("payments:stripe-webhook")
        response = self.client.post(
            url,
            data={},
            HTTP_STRIPE_SIGNATURE="test_signature"
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @patch("stripe.Webhook.construct_event")
    def test_webhook_invalid_signature(self, mock_construct_event):
        """Test webhook handling with invalid signature"""
        mock_construct_event.side_effect = ValueError("Invalid payload")
        
        url = reverse("payments:stripe-webhook")
        response = self.client.post(
            url,
            data={},
            HTTP_STRIPE_SIGNATURE="invalid_signature"
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST) 