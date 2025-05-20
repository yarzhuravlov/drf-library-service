from datetime import timedelta
from unittest.mock import patch

from django.urls import reverse
from django.utils.timezone import now
from rest_framework.test import APITestCase
from django.contrib.auth import get_user_model

from books.models import Book, Author
from borrowings.models import Borrowing
from payments.models import Payment

User = get_user_model()


class PaymentViewSetTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="user@example.com", password="pass1234")
        self.other_user = User.objects.create_user(email="other@example.com", password="pass1234")

        self.author = Author.objects.create(first_name="John", last_name="Doe")
        self.book = Book.objects.create(
            title="Sample Book",
            cover=Book.Covers.HARD,
            inventory=5,
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
            session_url="https://example.com/session/1",
            session_id="session_1",
            money_to_pay=1000,
            status=Payment.Statuses.PAID,
            type=Payment.Types.PAYMENT,
        )

    @patch("payments.views.send_notification_to_all_admin_users")
    @patch("payments.views.update_payment_by_session_id")
    def test_success_payment_sends_notification(self, mock_update, mock_notify):
        payment = Payment.objects.select_related("borrowing__user").get(id=self.payment.id)
        mock_update.return_value = payment

        url = reverse("payments:payment-success")
        response = self.client.get(url, {"session_id": payment.session_id})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, {"message": "Payment status changed to PAID"})

        mock_notify.assert_called_once()
        message = mock_notify.call_args[0][0]

        self.assertIn(str(payment.id), message)
        self.assertIn(payment.borrowing.user.email, message)
        self.assertIn(str(payment.money_to_pay), message)

    def test_success_payment_missing_session_id(self):
        url = reverse("payments:payment-success")
        response = self.client.get(url)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data, {"detail": "session_id is required"})

    @patch("payments.views.update_payment_by_session_id")
    def test_success_payment_not_found(self, mock_update):
        mock_update.return_value = None

        url = reverse("payments:payment-success")
        response = self.client.get(url, {"session_id": "invalid_session"})

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.data, {"detail": "Paid session with such session_id not found"})

    def test_cancel_payment(self):
        url = reverse("payments:payment-cancel")
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, {"message": "Payment can be completed later"})

    def test_list_payments_requires_authentication(self):
        url = reverse("payments:payment-list")
        response = self.client.get(url)

        self.assertEqual(response.status_code, 401)

    def test_list_payments_for_authenticated_user(self):
        self.client.force_authenticate(user=self.user)
        url = reverse("payments:payment-list")
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(all(p["borrowing"] == self.borrowing.id for p in response.data))

    def test_list_payments_excludes_others(self):
        other_borrowing = Borrowing.objects.create(
            user=self.other_user,
            book=self.book,
            borrow_date=now().date(),
            expected_return=(now() + timedelta(days=5)).date(),
        )
        Payment.objects.create(
            borrowing=other_borrowing,
            session_url="https://example.com/session/2",
            session_id="session_2",
            money_to_pay=500,
            status=Payment.Statuses.PAID,
            type=Payment.Types.PAYMENT,
        )

        self.client.force_authenticate(user=self.user)
        url = reverse("payments:payment-list")
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(all(p["borrowing"] == self.borrowing.id for p in response.data))

    @patch("payments.services.renew_payment_session")
    def test_renew_payment_authorized(self, mock_renew):
        self.client.force_authenticate(user=self.user)
        url = reverse("payments:payment-renew", kwargs={"pk": self.payment.pk})

        mock_renew.return_value = self.payment

        response = self.client.put(url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["session_id"], self.payment.session_id)

    def test_renew_payment_forbidden_for_other_user(self):
        self.client.force_authenticate(user=self.other_user)
        url = reverse("payments:payment-renew", kwargs={"pk": self.payment.pk})

        response = self.client.put(url)

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.data["detail"], "Not authorized to renew this payment.")
