import json
import unittest
from unittest.mock import patch, MagicMock

from django.test import TestCase, override_settings

from notifications.handlers import (
    send_notification_redis,
)
from notifications.tasks import send_notification_celery
from notifications.daily_checks import (
    get_overdue_borrowings,
    check_overdue_borrowings,
)


class NotificationsHandlersTests(TestCase):
    """Тести для обробників повідомлень"""

    @patch("notifications.handlers.get_redis_connection")
    def test_send_notification_redis(self, mock_get_redis):
        """Тест відправки повідомлення через Redis"""
        # Підготовка
        mock_redis = MagicMock()
        mock_get_redis.return_value = mock_redis

        telegram_ids = [123456789]
        text = "Тестове повідомлення"

        # Виконання
        result = send_notification_redis(telegram_ids, text)

        # Перевірка
        self.assertTrue(result)
        mock_redis.rpush.assert_called_once()

        # Перевірка формату повідомлення
        args, _ = mock_redis.rpush.call_args
        queue_name, message_json = args
        message = json.loads(message_json)

        self.assertEqual(message["telegram_ids"], telegram_ids)
        self.assertEqual(message["text"], text)

    @patch("notifications.tasks.send_notification_redis")
    def test_send_notification_celery(self, mock_redis):
        """Тест Celery task для відправки повідомлення через Redis"""
        telegram_ids = [123456789]
        text = "Тестове повідомлення"
        send_notification_celery(telegram_ids, text)
        mock_redis.assert_called_once_with(telegram_ids, text)

    @override_settings(
        REDIS_HOST="test_host",
        REDIS_PORT=1234,
        REDIS_DB=5,
        REDIS_PASSWORD="test_pass",
        NOTIFICATIONS_QUEUE="test_queue",
    )
    @patch("notifications.handlers.redis.Redis")
    def test_redis_settings_from_django_settings(self, mock_redis_class):
        """Тест, що перевіряє використання налаштувань django.conf.settings"""
        # Підготовка
        mock_redis_instance = MagicMock()
        mock_redis_class.return_value = mock_redis_instance

        telegram_ids = [123456789]
        text = "Тест налаштувань"

        # Виконання
        send_notification_redis(telegram_ids, text)

        # Перевірка, що redis.Redis викликано з правильними параметрами
        mock_redis_class.assert_called_once_with(
            host="test_host",
            port=1234,
            db=5,
            password="test_pass",
            decode_responses=True,
        )

        # Перевірка використання правильної назви черги з settings
        args, _ = mock_redis_instance.rpush.call_args
        queue_name, _ = args
        self.assertEqual(queue_name, "test_queue")


class DailyChecksTests(TestCase):
    """Тести для щоденних перевірок"""

    @patch("notifications.daily_checks.requests.get")
    def test_get_overdue_borrowings(self, mock_get):
        """Тест отримання прострочених позичань"""
        # Підготовка
        mock_response = MagicMock()
        mock_response.json.return_value = [
            {
                "id": 1,
                "user": {"first_name": "Test"},
                "book": {"title": "Book"},
            }
        ]
        mock_get.return_value = mock_response

        api_url = "http://example.com/api/borrowings/overdue/"
        auth_token = "test_token"

        # Виконання
        result = get_overdue_borrowings(api_url, auth_token)

        # Перевірка
        self.assertEqual(len(result), 1)
        mock_get.assert_called_once_with(
            api_url, headers={"Authorization": f"Bearer {auth_token}"}
        )

    @patch("notifications.daily_checks.get_overdue_borrowings")
    @patch("notifications.daily_checks.send_telegram_notification_django")
    def test_check_overdue_borrowings_no_borrowings(
        self, mock_send, mock_get_borrowings
    ):
        """Тест перевірки при відсутності прострочених позичань"""
        # Підготовка
        mock_get_borrowings.return_value = []

        api_url = "http://example.com/api/borrowings/overdue/"
        admin_chat_ids = [123456789]

        # Виконання
        result = check_overdue_borrowings(api_url, admin_chat_ids)

        # Перевірка
        self.assertEqual(result, 0)
        mock_send.assert_called_once()
        # Перевіряємо, що відправлено повідомлення
        # з текстом "Немає прострочених позичань"

        _, kwargs = mock_send.call_args
        self.assertIn("Немає прострочених позичань", kwargs["text"])

    @patch("notifications.daily_checks.get_overdue_borrowings")
    @patch("notifications.daily_checks.send_telegram_notification_django")
    def test_check_overdue_borrowings_with_borrowings(
        self, mock_send, mock_get_borrowings
    ):
        """Тест перевірки при наявності прострочених позичань"""
        # Підготовка
        mock_get_borrowings.return_value = [
            {
                "id": 1,
                "user": {
                    "first_name": "John",
                    "last_name": "Doe",
                    "email": "john@example.com",
                },
                "book": {
                    "title": "Test Book",
                    "author": "Test Author",
                    "daily_fee": 1.5,
                },
                "borrow_date": "2023-01-01",
                "expected_return_date": "2023-01-10",
                "days_overdue": 5,
            }
        ]

        api_url = "http://example.com/api/borrowings/overdue/"
        admin_chat_ids = [123456789]

        # Виконання
        result = check_overdue_borrowings(api_url, admin_chat_ids)

        # Перевірка
        self.assertEqual(result, 1)
        # Викликається двічі: один раз для повідомлення
        # про прострочення і один раз для підсумкового повідомлення
        self.assertEqual(mock_send.call_count, 2)


if __name__ == "__main__":
    unittest.main()
