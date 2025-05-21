from unittest.mock import patch, call
from datetime import date, timedelta
from contextlib import contextmanager

from django.test import TestCase
from django.contrib.auth import get_user_model

from borrowings.models import Borrowing
from books.models import Book
from borrowings.tasks import check_overdue_borrowings

User = get_user_model()


class CheckOverdueBorrowingsTaskTests(TestCase):
    BASE_DATE = date(2024, 5, 15)

    def setUp(self):
        self.user1 = User.objects.create_user(
            email="user1@example.com", password="password123"
        )
        self.user2 = User.objects.create_user(
            email="user2@example.com", password="password123"
        )
        self.book1 = Book.objects.create(
            title="The Great Gatsby", inventory=5, daily_fee=0.50
        )
        self.book2 = Book.objects.create(
            title="1984", inventory=3, daily_fee=0.75
        )

    @contextmanager
    def mock_date_and_notification(self, fixed_date=BASE_DATE):
        with patch("borrowings.tasks.date") as mock_date, patch(
            "borrowings.tasks.send_notification_to_all_admin_users"
        ) as mock_send:
            mock_date.today.return_value = fixed_date
            yield mock_date, mock_send

    def create_borrowing(
        self, book, user, borrow_date, expected_return, actual_return=None
    ):
        return Borrowing.objects.create(
            book=book,
            user=user,
            borrow_date=borrow_date,
            expected_return=expected_return,
            actual_return=actual_return,
        )

    def get_expected_message(self, borrowing, today):
        days_overdue = (today - borrowing.expected_return).days
        return (
            f"<b>Overdue Borrowing</b>\n"
            f"ID: {borrowing.id}\n"
            f"User: {borrowing.user.email}\n"
            f"Book: {borrowing.book.title}\n"
            f"Expected Return: {borrowing.expected_return}\n"
            f"Days Overdue: {days_overdue}"
        )

    def test_single_overdue_borrowing_sends_notification(self):
        with self.mock_date_and_notification() as (
            mock_date,
            mock_send_notification,
        ):
            fixed_today = self.BASE_DATE
            borrowing_overdue = self.create_borrowing(
                book=self.book1,
                user=self.user1,
                borrow_date=fixed_today - timedelta(days=10),
                expected_return=fixed_today - timedelta(days=3),
            )
            self.create_borrowing(
                book=self.book2,
                user=self.user2,
                borrow_date=fixed_today - timedelta(days=1),
                expected_return=fixed_today + timedelta(days=5),
            )
            self.create_borrowing(
                book=self.book1,
                user=self.user2,
                borrow_date=fixed_today - timedelta(days=12),
                expected_return=fixed_today - timedelta(days=5),
                actual_return=fixed_today - timedelta(days=1),
            )
            check_overdue_borrowings()
            expected_message = self.get_expected_message(
                borrowing_overdue, fixed_today
            )
            mock_send_notification.assert_called_once_with(expected_message)

    def test_multiple_overdue_borrowings_sends_notifications(self):
        with self.mock_date_and_notification(fixed_date=date(2024, 5, 20)) as (
            mock_date,
            mock_send_notification,
        ):
            fixed_today = date(2024, 5, 20)
            borrowing1 = self.create_borrowing(
                book=self.book1,
                user=self.user1,
                borrow_date=fixed_today - timedelta(days=15),
                expected_return=fixed_today - timedelta(days=5),
            )
            borrowing2 = self.create_borrowing(
                book=self.book2,
                user=self.user2,
                borrow_date=fixed_today - timedelta(days=7),
                expected_return=fixed_today - timedelta(days=1),
            )
            check_overdue_borrowings()
            message1 = self.get_expected_message(borrowing1, fixed_today)
            message2 = self.get_expected_message(borrowing2, fixed_today)
            self.assertEqual(mock_send_notification.call_count, 2)
            mock_send_notification.assert_has_calls(
                [call(message1), call(message2)], any_order=True
            )

    def test_no_overdue_borrowings_sends_correct_message(self):
        with self.mock_date_and_notification() as (
            mock_date,
            mock_send_notification,
        ):
            fixed_today = self.BASE_DATE
            self.create_borrowing(
                book=self.book1,
                user=self.user1,
                borrow_date=fixed_today - timedelta(days=2),
                expected_return=fixed_today + timedelta(days=7),
            )
            self.create_borrowing(
                book=self.book2,
                user=self.user2,
                borrow_date=fixed_today - timedelta(days=10),
                expected_return=fixed_today - timedelta(days=3),
                actual_return=fixed_today - timedelta(days=3),
            )
            check_overdue_borrowings()
            mock_send_notification.assert_called_once_with(
                "<b>No borrowings overdue today!</b>"
            )

    def test_borrowing_due_today_is_overdue(self):
        with self.mock_date_and_notification(fixed_date=date(2024, 6, 1)) as (
            mock_date,
            mock_send_notification,
        ):
            fixed_today = date(2024, 6, 1)
            borrowing = self.create_borrowing(
                book=self.book1,
                user=self.user1,
                borrow_date=fixed_today - timedelta(days=7),
                expected_return=fixed_today,
            )
            check_overdue_borrowings()
            expected_message = self.get_expected_message(
                borrowing, fixed_today
            )
            mock_send_notification.assert_called_once_with(expected_message)

    def test_no_borrowings_sends_no_overdue_message(self):
        with self.mock_date_and_notification() as (
            mock_date,
            mock_send_notification,
        ):
            check_overdue_borrowings()
            mock_send_notification.assert_called_once_with(
                "<b>No borrowings overdue today!</b>"
            )

    def test_returned_borrowings_are_not_overdue(self):
        with self.mock_date_and_notification() as (
            mock_date,
            mock_send_notification,
        ):
            fixed_today = self.BASE_DATE
            self.create_borrowing(
                book=self.book1,
                user=self.user1,
                borrow_date=fixed_today - timedelta(days=10),
                expected_return=fixed_today - timedelta(days=3),
                actual_return=fixed_today - timedelta(days=2),
            )
            check_overdue_borrowings()
            mock_send_notification.assert_called_once_with(
                "<b>No borrowings overdue today!</b>"
            )

    def test_future_borrowings_are_not_overdue(self):
        with self.mock_date_and_notification() as (
            mock_date,
            mock_send_notification,
        ):
            fixed_today = self.BASE_DATE
            self.create_borrowing(
                book=self.book1,
                user=self.user1,
                borrow_date=fixed_today - timedelta(days=1),
                expected_return=fixed_today + timedelta(days=5),
            )
            check_overdue_borrowings()
            mock_send_notification.assert_called_once_with(
                "<b>No borrowings overdue today!</b>"
            )

    def test_large_number_of_borrowings(self):
        with self.mock_date_and_notification() as (
            mock_date,
            mock_send_notification,
        ):
            fixed_today = self.BASE_DATE
            overdue_borrowings = [
                Borrowing(
                    book=self.book1,
                    user=self.user1,
                    borrow_date=fixed_today - timedelta(days=10 + i),
                    expected_return=fixed_today - timedelta(days=3 + i),
                )
                for i in range(10)
            ]
            future_borrowings = [
                Borrowing(
                    book=self.book2,
                    user=self.user2,
                    borrow_date=fixed_today - timedelta(days=1 + i),
                    expected_return=fixed_today + timedelta(days=5 + i),
                )
                for i in range(10)
            ]
            Borrowing.objects.bulk_create(
                overdue_borrowings + future_borrowings
            )
            check_overdue_borrowings()
            self.assertEqual(mock_send_notification.call_count, 10)

    def test_notification_failure(self):
        with self.mock_date_and_notification() as (
            mock_date,
            mock_send_notification,
        ):
            fixed_today = self.BASE_DATE
            mock_send_notification.side_effect = ValueError("Some value error")
            self.create_borrowing(
                book=self.book1,
                user=self.user1,
                borrow_date=fixed_today - timedelta(days=10),
                expected_return=fixed_today - timedelta(days=3),
            )
            with self.assertRaises(ValueError):
                check_overdue_borrowings()

    def test_no_admins_with_telegram(self):
        with self.mock_date_and_notification() as (
            mock_date,
            mock_send_notification,
        ):
            fixed_today = self.BASE_DATE
            mock_send_notification.return_value = False
            self.create_borrowing(
                book=self.book1,
                user=self.user1,
                borrow_date=fixed_today - timedelta(days=10),
                expected_return=fixed_today - timedelta(days=3),
            )
            check_overdue_borrowings()
            self.assertTrue(mock_send_notification.called)
