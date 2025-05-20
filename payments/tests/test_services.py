<<<<<<< HEAD
from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import patch

import stripe
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIRequestFactory
from borrowings.models import Borrowing
from books.models import Book
from payments.models import Payment
from payments.services import (
    calc_borrowing_total_price,
    calc_borrowing_fine_price,
    create_stripe_session,
    create_payment,
    create_fine_payment,
    update_payment_by_session_id,
    renew_payment_session,
)


class PaymentServicesTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.request = self.factory.get("/")
        self.request.build_absolute_uri = lambda x: f"http://testserver{x}"

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
            expected_return=date(2024, 1, 10),
            actual_return=date(2024, 1, 15)
        )

    def test_calc_borrowing_total_price(self):
        price = calc_borrowing_total_price(self.borrowing)
        self.assertEqual(price, 90)  # 9 days * 10 daily fee

    def test_calc_borrowing_fine_price(self):
        fine = calc_borrowing_fine_price(self.borrowing)
        expected_fine = 5 * int(str(Decimal("10") * Decimal("0.3")).split(".")[0])
        self.assertEqual(fine, expected_fine)

    @patch("stripe.checkout.Session.create")
    def test_create_stripe_session(self, mock_create):
        mock_create.return_value.url = "https://test.com"
        mock_create.return_value.id = "test_session"

        session = create_stripe_session(self.borrowing, 100, self.request)

        self.assertEqual(session.url, "https://test.com")
        self.assertEqual(session.id, "test_session")

    @patch("stripe.checkout.Session.create")
    def test_create_payment(self, mock_create):
        mock_create.return_value.url = "https://test.com"
        mock_create.return_value.id = "test_session"

        payment = create_payment(self.borrowing, self.request)

        self.assertEqual(payment.borrowing, self.borrowing)
        self.assertEqual(payment.session_url, "https://test.com")
        self.assertEqual(payment.session_id, "test_session")
        self.assertEqual(payment.money_to_pay, 90)
        self.assertEqual(payment.type, Payment.Types.PAYMENT)
        self.assertEqual(payment.status, Payment.Statuses.PENDING)
        self.assertGreater(payment.expiration_at, timezone.now())

    @patch("stripe.checkout.Session.create")
    def test_create_fine_payment(self, mock_create):
        mock_create.return_value.url = "https://test.com"
        mock_create.return_value.id = "test_session"

        payment = create_fine_payment(self.borrowing, self.request)

        expected_fine = 5 * int(str(Decimal("10") * Decimal("0.3")).split(".")[0])
        self.assertEqual(payment.borrowing, self.borrowing)
        self.assertEqual(payment.session_url, "https://test.com")
        self.assertEqual(payment.session_id, "test_session")
        self.assertEqual(payment.money_to_pay, expected_fine)
        self.assertEqual(payment.type, Payment.Types.FINE)
        self.assertEqual(payment.status, Payment.Statuses.PENDING)
        self.assertGreater(payment.expiration_at, timezone.now())

    @patch("stripe.checkout.Session.retrieve")
    def test_update_payment_by_session_id_invalid_session(self, mock_retrieve):
        mock_retrieve.side_effect = stripe.error.InvalidRequestError(
            "No such session", "session_id"
        )

        result = update_payment_by_session_id("invalid_session")
        self.assertIsNone(result)

    @patch("stripe.checkout.Session.retrieve")
    def test_update_payment_by_session_id_not_paid(self, mock_retrieve):
        mock_retrieve.return_value.payment_status = "unpaid"

        result = update_payment_by_session_id("test_session")
        self.assertIsNone(result)

    @patch("stripe.checkout.Session.retrieve")
    def test_update_payment_by_session_id_success(self, mock_retrieve):
        mock_retrieve.return_value.payment_status = "paid"
        payment = Payment.objects.create(
            borrowing=self.borrowing,
            session_url="https://test.com",
            session_id="test_session",
            money_to_pay=100,
            type=Payment.Types.PAYMENT,
            status=Payment.Statuses.PENDING,
            expiration_at=timezone.now() + timedelta(minutes=30),
        )

        result = update_payment_by_session_id("test_session")
        payment.refresh_from_db()

        self.assertIsInstance(result, Payment)
        self.assertEqual(payment.status, Payment.Statuses.PAID)

    @patch("stripe.checkout.Session.create")
    def test_renew_payment_session_not_expired(self, mock_create):
        payment = Payment.objects.create(
            borrowing=self.borrowing,
            session_url="https://test.com",
            session_id="test_session",
            money_to_pay=100,
            type=Payment.Types.PAYMENT,
            status=Payment.Statuses.PENDING,
            expiration_at=timezone.now() + timedelta(minutes=30),
        )

        result = renew_payment_session(payment, self.request)

        self.assertIsInstance(result, Payment)
        self.assertEqual(result.status, Payment.Statuses.PENDING)
        mock_create.assert_not_called()

    @patch("stripe.checkout.Session.create")
    def test_renew_payment_session_success(self, mock_create):
        mock_create.return_value.url = "https://new-test.com"
        mock_create.return_value.id = "new_test_session"
        payment = Payment.objects.create(
            borrowing=self.borrowing,
            session_url="https://test.com",
            session_id="test_session",
            money_to_pay=100,
            type=Payment.Types.PAYMENT,
            status=Payment.Statuses.EXPIRED,
            expiration_at=timezone.now() - timedelta(minutes=1),
        )

        result = renew_payment_session(payment, self.request)

        self.assertEqual(result.session_url, "https://new-test.com")
        self.assertEqual(result.session_id, "new_test_session")
        self.assertEqual(result.status, Payment.Statuses.PENDING)
        self.assertGreater(result.expiration_at, timezone.now())
        mock_create.assert_called_once()


class CheckExpiredSessionsTaskTests(TestCase):
    def setUp(self):
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
            status=Payment.Statuses.PENDING,
            type=Payment.Types.PAYMENT,
            expiration_at=timezone.now() - timedelta(minutes=1),
        )

    @patch("stripe.checkout.Session.retrieve")
    def test_check_expired_sessions(self, mock_retrieve):
        from payments.tasks import check_expired_sessions

        mock_retrieve.return_value.status = "expired"

        check_expired_sessions()

        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, Payment.Statuses.EXPIRED)

    @patch("stripe.checkout.Session.retrieve")
    def test_check_expired_sessions_not_expired(self, mock_retrieve):
        from payments.tasks import check_expired_sessions

        mock_retrieve.side_effect = stripe.error.StripeError("Test error")

        self.payment.expiration_at = timezone.now() + timedelta(minutes=30)
        self.payment.save()

=======
from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import patch

import stripe
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIRequestFactory

from borrowings.models import Borrowing
from books.models import Book
from payments.models import Payment
from payments.services import (
    calc_borrowing_total_price,
    calc_borrowing_fine_price,
    create_stripe_session,
    create_payment,
    create_fine_payment,
    update_payment_by_session_id,
    renew_payment_session,
)


class PaymentServicesTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.request = self.factory.get("/")
        self.request.build_absolute_uri = lambda x: f"http://testserver{x}"

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
            expected_return=date(2024, 1, 10),
            actual_return=date(2024, 1, 15)
        )

    def test_calc_borrowing_total_price(self):
        price = calc_borrowing_total_price(self.borrowing)
        self.assertEqual(price, 9000)  # 9 days * 10 daily fee * 100 (cents)

    def test_calc_borrowing_fine_price(self):
        fine = calc_borrowing_fine_price(self.borrowing)
        daily_fee = Decimal("10")
        fine_rate = Decimal("0.3")
        fine_multiplier = int(str(daily_fee * fine_rate).split(".")[0])
        expected_fine = 5 * fine_multiplier * 100  # Convert to cents
        self.assertEqual(fine, expected_fine)

    @patch("stripe.checkout.Session.create")
    def test_create_stripe_session(self, mock_create):
        mock_create.return_value.url = "https://test.com"
        mock_create.return_value.id = "test_session"

        session = create_stripe_session(self.borrowing, 100, self.request)

        self.assertEqual(session.url, "https://test.com")
        self.assertEqual(session.id, "test_session")

    @patch("stripe.checkout.Session.create")
    def test_create_payment(self, mock_create):
        mock_create.return_value.url = "https://test.com"
        mock_create.return_value.id = "test_session"

        payment = create_payment(self.borrowing, self.request)

        self.assertEqual(payment.borrowing, self.borrowing)
        self.assertEqual(payment.session_url, "https://test.com")
        self.assertEqual(payment.session_id, "test_session")
        self.assertEqual(payment.money_to_pay, 9000)
        self.assertEqual(payment.type, Payment.Types.PAYMENT)
        self.assertEqual(payment.status, Payment.Statuses.PENDING)
        self.assertGreater(payment.expiration_at, timezone.now())

    @patch("stripe.checkout.Session.create")
    def test_create_fine_payment(self, mock_create):
        mock_create.return_value.url = "https://test.com"
        mock_create.return_value.id = "test_session"

        payment = create_fine_payment(self.borrowing, self.request)

        daily_fee = Decimal("10")
        fine_rate = Decimal("0.3")
        fine_multiplier = int(str(daily_fee * fine_rate).split(".")[0])
        expected_fine = 5 * fine_multiplier * 100

        self.assertEqual(payment.borrowing, self.borrowing)
        self.assertEqual(payment.session_url, "https://test.com")
        self.assertEqual(payment.session_id, "test_session")
        self.assertEqual(payment.money_to_pay, expected_fine)
        self.assertEqual(payment.type, Payment.Types.FINE)
        self.assertEqual(payment.status, Payment.Statuses.PENDING)
        self.assertGreater(payment.expiration_at, timezone.now())

    @patch("stripe.checkout.Session.retrieve")
    def test_update_payment_by_session_id_invalid_session(self, mock_retrieve):
        mock_retrieve.side_effect = stripe.error.InvalidRequestError(
            "No such session", "session_id"
        )

        result = update_payment_by_session_id("invalid_session")
        self.assertIsNone(result)

    @patch("stripe.checkout.Session.retrieve")
    def test_update_payment_by_session_id_not_paid(self, mock_retrieve):
        mock_retrieve.return_value.payment_status = "unpaid"

        result = update_payment_by_session_id("test_session")
        self.assertIsNone(result)

    @patch("stripe.checkout.Session.retrieve")
    def test_update_payment_by_session_id_success(self, mock_retrieve):
        mock_retrieve.return_value.payment_status = "paid"
        payment = Payment.objects.create(
            borrowing=self.borrowing,
            session_url="https://test.com",
            session_id="test_session",
            money_to_pay=100,
            type=Payment.Types.PAYMENT,
            status=Payment.Statuses.PENDING,
            expiration_at=timezone.now() + timedelta(minutes=30),
        )

        result = update_payment_by_session_id("test_session")
        payment.refresh_from_db()

        self.assertIsInstance(result, Payment)
        self.assertEqual(payment.status, Payment.Statuses.PAID)

    @patch("stripe.checkout.Session.create")
    def test_renew_payment_session_not_expired(self, mock_create):
        payment = Payment.objects.create(
            borrowing=self.borrowing,
            session_url="https://test.com",
            session_id="test_session",
            money_to_pay=100,
            type=Payment.Types.PAYMENT,
            status=Payment.Statuses.PENDING,
            expiration_at=timezone.now() + timedelta(minutes=30),
        )

        result = renew_payment_session(payment, self.request)

        self.assertIsInstance(result, Payment)
        self.assertEqual(result.status, Payment.Statuses.PENDING)
        mock_create.assert_not_called()

    @patch("stripe.checkout.Session.create")
    def test_renew_payment_session_success(self, mock_create):
        mock_create.return_value.url = "https://new-test.com"
        mock_create.return_value.id = "new_test_session"
        payment = Payment.objects.create(
            borrowing=self.borrowing,
            session_url="https://test.com",
            session_id="test_session",
            money_to_pay=100,
            type=Payment.Types.PAYMENT,
            status=Payment.Statuses.EXPIRED,
            expiration_at=timezone.now() - timedelta(minutes=1),
        )

        result = renew_payment_session(payment, self.request)

        self.assertEqual(result.session_url, "https://new-test.com")
        self.assertEqual(result.session_id, "new_test_session")
        self.assertEqual(result.status, Payment.Statuses.PENDING)
        self.assertGreater(result.expiration_at, timezone.now())
        mock_create.assert_called_once()


class CheckExpiredSessionsTaskTests(TestCase):
    def setUp(self):
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
            status=Payment.Statuses.PENDING,
            type=Payment.Types.PAYMENT,
            expiration_at=timezone.now() - timedelta(minutes=1),
        )

    @patch("stripe.checkout.Session.retrieve")
    def test_check_expired_sessions(self, mock_retrieve):
        from payments.tasks import check_expired_sessions

        mock_retrieve.return_value.status = "expired"

        check_expired_sessions()

        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, Payment.Statuses.EXPIRED)

    @patch("stripe.checkout.Session.retrieve")
    def test_check_expired_sessions_not_expired(self, mock_retrieve):
        from payments.tasks import check_expired_sessions

        mock_retrieve.side_effect = stripe.error.StripeError("Test error")

        self.payment.expiration_at = timezone.now() + timedelta(minutes=30)
        self.payment.save()

        check_expired_sessions()

        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, Payment.Statuses.PENDING)
>>>>>>> 3ad0cfb (Fix all flake8 errors, update tests)
