import json
import unittest
from unittest.mock import patch, MagicMock

from django.test import TestCase, override_settings
from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from notifications.handlers import (
    send_notification_redis,
    send_admin_notification,
    send_notification_to_all_admin_users,
    send_user_notification,
    send_notification_to_user,
    send_telegram_notification_django,
)
from notifications.tasks import send_notification_celery
from notifications.models import TelegramUser


User = get_user_model()


class NotificationsHandlersTests(TestCase):
    """Tests for notification handlers"""

    def setUp(self):
        """Set up test data for user notification tests"""
        self.user = User.objects.create_user(
            email="testuser@example.com", password="password123"
        )

        self.telegram_user = TelegramUser.objects.create(
            user=self.user, telegram_id=123456789
        )

    @patch("notifications.handlers.get_redis_connection")
    def test_send_notification_redis(self, mock_get_redis):
        """Test sending notification via Redis"""
        # Setup
        mock_redis = MagicMock()
        mock_get_redis.return_value = mock_redis

        telegram_ids = [123456789]
        text = "Test message"

        # Execute
        result = send_notification_redis(telegram_ids, text)

        # Assert
        self.assertTrue(result)
        mock_redis.rpush.assert_called_once()

        # Check message format
        args, _ = mock_redis.rpush.call_args
        queue_name, message_json = args
        message = json.loads(message_json)

        self.assertEqual(message["telegram_ids"], telegram_ids)
        self.assertEqual(message["text"], text)

    @patch("notifications.tasks.send_notification_redis")
    def test_send_notification_celery(self, mock_redis_send_func):
        """Test Celery task for sending notification via Redis"""
        telegram_ids = [123456789]
        text = "Test message"
        send_notification_celery(telegram_ids, text)
        mock_redis_send_func.assert_called_once_with(telegram_ids, text)

    @override_settings(
        REDIS_HOST="test_host",
        REDIS_PORT=1234,
        REDIS_DB=5,
        REDIS_PASSWORD="test_pass",
        NOTIFICATIONS_QUEUE="test_queue",
    )
    @patch("notifications.handlers.redis.Redis")
    def test_redis_settings_from_django_settings(self, mock_redis_class):
        """Test checking usage of django.conf.settings for Redis"""
        # Setup
        mock_redis_instance = MagicMock()
        mock_redis_class.return_value = mock_redis_instance

        telegram_ids = [123456789]
        text = "Settings test message"

        # Execute
        send_notification_redis(telegram_ids, text)

        # Assert that redis.Redis was called with correct parameters
        mock_redis_class.assert_called_once_with(
            host="test_host",
            port=1234,
            db=5,
            password="test_pass",
            decode_responses=True,
        )

        # Assert usage of correct queue name from settings
        args, _ = mock_redis_instance.rpush.call_args
        queue_name, _ = args
        self.assertEqual(queue_name, "test_queue")

    @patch("notifications.handlers.send_telegram_notification_django")
    @override_settings(TELEGRAM_ADMIN_CHAT_ID=12345)
    def test_send_admin_notification_success(self, mock_send):
        """Test sending notification to admin with chat_id in settings"""
        mock_send.return_value = True

        result = send_admin_notification("Admin message")

        self.assertTrue(result)
        mock_send.assert_called_once_with([12345], "Admin message", True)

    @patch("notifications.handlers.send_telegram_notification_django")
    @override_settings(TELEGRAM_ADMIN_CHAT_ID=None)
    def test_send_admin_notification_no_chat_id(self, mock_send):
        """Test sending notification to admin with no chat_id in settings"""
        result = send_admin_notification("Admin message")

        self.assertFalse(result)  # Should fail without admin chat_id
        mock_send.assert_not_called()

    @patch("notifications.handlers.send_telegram_notification_django")
    @patch("notifications.handlers.TelegramUser.objects.filter")
    def test_send_notification_to_all_admin_users_success(
        self, mock_filter, mock_send
    ):
        """Test sending notification to all admin users with telegram profile"""
        # Mock for admin telegram ids
        mock_filter.return_value.values_list.return_value = [123, 456]
        mock_send.return_value = True

        result = send_notification_to_all_admin_users("Admin message")

        self.assertTrue(result)
        mock_filter.assert_called_once_with(user__is_staff=True)
        mock_filter.return_value.values_list.assert_called_once_with(
            "telegram_id", flat=True
        )
        mock_send.assert_called_once_with([123, 456], "Admin message", True)

    @patch("notifications.handlers.send_telegram_notification_django")
    @patch("notifications.handlers.TelegramUser.objects.filter")
    def test_send_notification_to_all_admin_users_no_admins(
        self, mock_filter, mock_send
    ):
        """Test sending notification when no admin users have telegram profiles"""
        # Mock for empty admin telegram ids
        mock_filter.return_value.values_list.return_value = []

        result = send_notification_to_all_admin_users("Admin message")

        self.assertFalse(result)  # Should fail when no admins have telegram
        mock_filter.assert_called_once_with(user__is_staff=True)
        mock_filter.return_value.values_list.assert_called_once_with(
            "telegram_id", flat=True
        )
        mock_send.assert_not_called()

    @patch("notifications.handlers.send_telegram_notification_django")
    def test_send_user_notification_success(self, mock_send):
        """Test sending notification to a specific user by telegram_id"""
        mock_send.return_value = True

        result = send_user_notification(123456789, "User message")

        self.assertTrue(result)
        mock_send.assert_called_once_with([123456789], "User message", True)

    @patch("notifications.handlers.send_telegram_notification_django")
    def test_send_user_notification_no_id(self, mock_send):
        """Test sending notification with no telegram_id"""
        result = send_user_notification(None, "User message")

        self.assertFalse(result)  # Should fail without telegram_id
        mock_send.assert_not_called()

    @patch("notifications.handlers.send_user_notification")
    def test_send_notification_to_user_success(self, mock_send_user):
        """Test sending notification to Django user with telegram profile"""
        mock_send_user.return_value = True

        result = send_notification_to_user(self.user, "User message")

        self.assertTrue(result)
        mock_send_user.assert_called_once_with(123456789, "User message", True)

    @patch("notifications.handlers.send_user_notification")
    def test_send_notification_to_user_no_telegram(self, mock_send_user):
        """Test sending notification to user without a telegram profile"""
        # Create user without telegram profile
        user_no_telegram = User.objects.create_user(
            email="notelegram@example.com", password="password123"
        )

        result = send_notification_to_user(user_no_telegram, "User message")

        self.assertFalse(result)  # Should fail without telegram profile
        mock_send_user.assert_not_called()

    @patch("notifications.tasks.send_notification_celery")
    def test_send_telegram_notification_django_with_celery(self, mock_celery):
        """Test sending telegram notification via Celery"""
        result = send_telegram_notification_django(
            [123, 456], "Test message", use_celery=True
        )

        self.assertTrue(result)
        mock_celery.delay.assert_called_once_with([123, 456], "Test message")

    @patch("notifications.handlers.send_notification_redis")
    def test_send_telegram_notification_django_without_celery(
        self, mock_redis
    ):
        """Test sending telegram notification directly via Redis"""
        mock_redis.return_value = True

        result = send_telegram_notification_django(
            [123, 456], "Test message", use_celery=False
        )

        self.assertTrue(result)
        mock_redis.assert_called_once_with([123, 456], "Test message")


class RegisterTelegramUserViewTests(TestCase):
    """Tests for RegisterTelegramUserWithJWTView"""

    def setUp(self):
        """Set up test data for each test"""
        self.client = APIClient()
        self.register_url = reverse("register_telegram_user")

        # Create a test user
        self.user = User.objects.create_user(
            email="testuser@example.com", password="testpassword123"
        )

        # Data for API requests
        self.valid_data = {
            "email": "testuser@example.com",
            "password": "testpassword123",
            "telegram_id": 123456789,
        }

    def test_register_telegram_user_success(self):
        """Test successful registration of telegram user"""
        # Execute
        response = self.client.post(
            self.register_url, self.valid_data, format="json"
        )

        # Assert
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["success"])
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)

        # Check that TelegramUser was created
        telegram_user = TelegramUser.objects.get(user=self.user)
        self.assertEqual(
            telegram_user.telegram_id, self.valid_data["telegram_id"]
        )

    def test_register_telegram_user_missing_fields(self):
        """Test registration with missing fields"""
        # Test without email
        data_without_email = {
            "password": "testpassword123",
            "telegram_id": 123456789,
        }
        response = self.client.post(
            self.register_url, data_without_email, format="json"
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.data)

        # Test without password
        data_without_password = {
            "email": "testuser@example.com",
            "telegram_id": 123456789,
        }
        response = self.client.post(
            self.register_url, data_without_password, format="json"
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.data)

        # Test without telegram_id
        data_without_telegram_id = {
            "email": "testuser@example.com",
            "password": "testpassword123",
        }
        response = self.client.post(
            self.register_url, data_without_telegram_id, format="json"
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.data)

    def test_register_telegram_user_invalid_credentials(self):
        """Test registration with invalid user credentials"""
        # Wrong password
        data_wrong_password = {
            "email": "testuser@example.com",
            "password": "wrongpassword",
            "telegram_id": 123456789,
        }
        response = self.client.post(
            self.register_url, data_wrong_password, format="json"
        )
        self.assertEqual(response.status_code, 401)
        self.assertIn("error", response.data)

        # Non-existent user
        data_nonexistent_user = {
            "email": "nonexistent@example.com",
            "password": "testpassword123",
            "telegram_id": 123456789,
        }
        response = self.client.post(
            self.register_url, data_nonexistent_user, format="json"
        )
        self.assertEqual(response.status_code, 401)
        self.assertIn("error", response.data)

    def test_register_telegram_user_duplicate_telegram_id(self):
        """Test registration with already used telegram_id"""
        # Create first user with telegram_id
        TelegramUser.objects.create(user=self.user, telegram_id=123456789)

        # Create second user
        user2 = User.objects.create_user(
            email="user2@example.com", password="testpassword123"
        )

        # Try to use the same telegram_id for second user
        data_for_user2 = {
            "email": "user2@example.com",
            "password": "testpassword123",
            "telegram_id": 123456789,
        }
        response = self.client.post(
            self.register_url, data_for_user2, format="json"
        )
        self.assertEqual(response.status_code, 409)
        self.assertIn("error", response.data)
        self.assertIn("already in use", response.data["error"])

    def test_register_telegram_user_update_existing(self):
        """Test updating telegram_id for a user that already has one"""
        # Create user with telegram_id
        TelegramUser.objects.create(user=self.user, telegram_id=123456789)

        # Update to new telegram_id
        update_data = {
            "email": "testuser@example.com",
            "password": "testpassword123",
            "telegram_id": 987654321,
        }
        response = self.client.post(
            self.register_url, update_data, format="json"
        )
        self.assertEqual(response.status_code, 200)

        # Check that telegram_id was updated
        telegram_user = TelegramUser.objects.get(user=self.user)
        self.assertEqual(telegram_user.telegram_id, 987654321)


if __name__ == "__main__":
    unittest.main()
