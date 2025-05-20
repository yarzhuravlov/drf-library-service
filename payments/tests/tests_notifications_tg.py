from unittest.mock import patch
from django.urls import reverse
from rest_framework.test import APITestCase
from django.contrib.auth import get_user_model
from django.utils.timezone import now
from datetime import timedelta
from borrowings.models import Borrowing
from books.models import Book, Author
from payments.models import Payment

User = get_user_model()


class PaymentViewSetTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="test@example.com", password="password123")
        self.other_user = User.objects.create_user(email="other@example.com", password="password123")

        self.author = Author.objects.create(first_name="John", last_name="Doe")
        self.book = Book.objects.create(
            title="Test Book",
            cover=Book.Covers.HARD,
            inventory=10,
            daily_fee=5,
        )
        self.book.authors.add(self.author)

        self.borrowing = Borrowing.objects.create(
            user=self.user,
            book=self.book,
            borrow_date=now().date(),
            expected_return=(now() + timedelta(days=7)).date(),
        )

        self.payment = Payment.objects.create(
            borrowing=self.borrowing,
            session_url="http://example.com/session/1",
            session_id="valid_session_id",
            money_to_pay=1000,
            status=Payment.Statuses.PAID,
            type=Payment.Types.PAYMENT,
        )

    @patch("payments.views.send_notification_to_all_admin_users")
    @patch("payments.views.update_payment_by_session_id")
    def test_success_payment_sends_notification(self, mock_update_payment, mock_send_notification):
        mock_update_payment.return_value = self.payment

        url = reverse("payments:payment-success")
        response = self.client.get(url, {"session_id": "valid_session_id"})

        self.assertEqual(response.status_code, 200)
        self.assertIn("message", response.data)
        self.assertEqual(response.data["message"], "Payment status changed to PAID")

        mock_send_notification.assert_called_once()
        sent_message = mock_send_notification.call_args[0][0]
        self.assertIn(str(self.payment.money_to_pay), sent_message)
        self.assertIn(str(self.payment.id), sent_message)
        self.assertIn(self.user.email, sent_message)

    def test_success_payment_missing_session_id(self):
        url = reverse("payments:payment-success")
        response = self.client.get(url)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data, {"detail": "session_id is required"})

    @patch("payments.views.update_payment_by_session_id")
    def test_success_payment_not_found(self, mock_update_payment):
        mock_update_payment.return_value = None

        url = reverse("payments:payment-success")
        response = self.client.get(url, {"session_id": "nonexistent"})

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.data, {"detail": "Paid session with such session_id not found"})

    def test_cancel_payment(self):
        url = reverse("payments:payment-cancel")
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, {"message": "Payment can be completed later"})

    def test_list_payments_requires_auth(self):
        url = reverse("payments:payment-list")

        response = self.client.get(url)
        self.assertEqual(response.status_code, 401)

        self.client.force_authenticate(user=self.user)
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        for item in response.data:
            self.assertEqual(item["borrowing"], self.borrowing.id)

    def test_list_payments_filters_non_staff(self):
        other_borrowing = Borrowing.objects.create(
            user=self.other_user,
            book=self.book,
            borrow_date=now().date(),
            expected_return=(now() + timedelta(days=7)).date(),
        )
        Payment.objects.create(
            borrowing=other_borrowing,
            session_url="http://example.com/session/2",
            session_id="other_session_id",
            money_to_pay=500,
            status=Payment.Statuses.PAID,
            type=Payment.Types.PAYMENT,
        )

        self.client.force_authenticate(user=self.user)
        url = reverse("payments:payment-list")
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        for item in response.data:
            self.assertEqual(item["borrowing"], self.borrowing.id)

    def test_renew_payment_authorized(self):
        self.client.force_authenticate(user=self.user)
        url = reverse("payments:payment-renew", kwargs={"pk": self.payment.pk})

        with patch("payments.services.renew_payment_session") as mock_renew:
            mock_renew.return_value = self.payment

            response = self.client.put(url, {})

            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.data["session_id"], self.payment.session_id)

    def test_renew_payment_not_authorized(self):
        self.client.force_authenticate(user=self.other_user)
        url = reverse("payments:payment-renew", kwargs={"pk": self.payment.pk})

        response = self.client.put(url, {})

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.data["detail"], "Not authorized to renew this payment.")
