from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from django.utils.timezone import localdate, timedelta
from borrowings.models import Borrowing
from books.models import Book, Author
from payments.models import Payment
from django.contrib.auth import get_user_model
from unittest.mock import patch, MagicMock

User = get_user_model()

class BorrowingCreatePaymentTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(email="u@e.com", password="p")
        author = Author.objects.create(first_name="A", last_name="B")
        self.book = Book.objects.create(title="T", cover=Book.Covers.HARD, inventory=2, daily_fee=50)
        self.book.authors.add(author)
        self.url = reverse("borrowings:borrowing-list")

    @patch("payments.services.create_stripe_session")
    def test_borrowing_create_triggers_payment(self, mock_session):
        fake = MagicMock(url="u", id="i")
        mock_session.return_value = fake

        self.client.force_authenticate(user=self.user)
        data = {
            "book": self.book.id,
            "borrow_date": localdate(),
            "expected_return": localdate() + timedelta(days=3)}
        resp = self.client.post(self.url, data)
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

        borrowing = Borrowing.objects.get(id=resp.data["id"])
        payments = Payment.objects.filter(borrowing=borrowing)
        self.assertEqual(payments.count(), 1)
        payment = payments.first()
        self.assertEqual(payment.session_url, fake.url)
        self.assertEqual(payment.session_id, fake.id)
        self.assertEqual(payment.money_to_pay, 3 * 50)
