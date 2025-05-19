from django.test import TestCase, override_settings
from unittest.mock import patch, MagicMock, AsyncMock, call
import json
import asyncio
import pytest
import os


class TelegramBotCoreTests(TestCase):
    """Тести для телеграм бот-ядра (bot_core.py)"""

    @patch("telegram_bot.bot_core.bot", new_callable=AsyncMock)
    @pytest.mark.asyncio
    async def test_send_message_to_user_success(self, mock_bot):
        """Тест успішного відправлення повідомлення користувачу"""
        # Імпортуємо функцію
        from telegram_bot.bot_core import send_message_to_user

        # Патчимо бота, щоб він повертав успіх
        mock_bot.send_message.return_value = True

        # Виконуємо тестовану функцію
        result = await send_message_to_user(123456789, "Тестове повідомлення")

        # Перевірка результату і виклику
        self.assertTrue(result)
        mock_bot.send_message.assert_called_once_with(
            chat_id=123456789, text="Тестове повідомлення"
        )

    @patch("telegram_bot.bot_core.bot", None)
    @pytest.mark.asyncio
    async def test_send_message_no_bot(self):
        """Тест відправлення повідомлення без ініціалізованого бота"""
        # Імпортуємо функцію
        from telegram_bot.bot_core import send_message_to_user

        # Виконуємо тестовану функцію (бот = None)
        result = await send_message_to_user(123456789, "Тестове повідомлення")

        # Повинно повернути False, якщо бот не ініціалізовано
        self.assertFalse(result)

    @patch("telegram_bot.bot_core.bot", new_callable=AsyncMock)
    @pytest.mark.asyncio
    async def test_send_messages_to_users(self, mock_bot):
        """Тест відправлення повідомлень багатьом користувачам"""
        # Імпортуємо функцію
        from telegram_bot.bot_core import send_messages_to_users

        # Налаштовуємо імітацію: перше повідомлення успішне, друге - ні
        mock_bot.send_message.side_effect = [True, Exception("Помилка")]

        # Виконуємо тестовану функцію
        result = await send_messages_to_users(
            [123, 456], "Тестове повідомлення"
        )

        # Перевірка, що функція викликалася для обох користувачів
        self.assertEqual(mock_bot.send_message.call_count, 2)
        # Перевірка результатів
        self.assertEqual(result, {123: True, 456: False})


class TelegramWorkerTests(TestCase):
    """Тести для телеграм воркера (worker.py)"""

    @patch("telegram_bot.worker.send_messages_to_users")
    @pytest.mark.asyncio
    async def test_process_message_valid(self, mock_send_messages):
        """Тест обробки валідного повідомлення з черги"""
        # Створюємо тестове повідомлення в форматі JSON
        test_message = json.dumps(
            {"telegram_ids": [123456789], "text": "Тестове повідомлення"}
        )

        # Патчимо функцію відправки повідомлень
        mock_send_messages.return_value = {123456789: True}

        # Виконуємо процес обробки повідомлення
        from telegram_bot.worker import process_message

        await process_message(test_message)

        # Перевірка, що функція викликана з правильними аргументами
        mock_send_messages.assert_called_once_with(
            [123456789], "Тестове повідомлення"
        )

    @patch("telegram_bot.worker.send_messages_to_users")
    @pytest.mark.asyncio
    async def test_process_message_invalid_json(self, mock_send_messages):
        """Тест обробки невалідного JSON"""
        # Невалідний JSON
        test_message = "Це не JSON"

        # Виконуємо процес обробки повідомлення
        from telegram_bot.worker import process_message

        await process_message(test_message)

        # Перевірка, що функція не викликана
        mock_send_messages.assert_not_called()

    @patch("telegram_bot.worker.send_messages_to_users")
    @pytest.mark.asyncio
    async def test_process_message_missing_fields(self, mock_send_messages):
        """Тест обробки повідомлення з відсутніми полями"""
        # Відсутнє поле text
        test_message = json.dumps({"telegram_ids": [123456789]})

        # Виконуємо процес обробки повідомлення
        from telegram_bot.worker import process_message

        await process_message(test_message)

        # Перевірка, що функція не викликана
        mock_send_messages.assert_not_called()

        # Тест з відсутнім telegram_ids
        test_message = json.dumps({"text": "Тестове повідомлення"})
        await process_message(test_message)
        mock_send_messages.assert_not_called()

        # Тест з пустим списком telegram_ids
        test_message = json.dumps(
            {"telegram_ids": [], "text": "Тестове повідомлення"}
        )
        await process_message(test_message)
        mock_send_messages.assert_not_called()
