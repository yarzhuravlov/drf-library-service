import logging
import asyncio
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramAPIError

# Імпортуємо конфігурацію з поточного додатку telegram_bot
from telegram_bot.config import TELEGRAM_BOT_TOKEN, LOG_LEVEL

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, "INFO"),  # Додано fallback до INFO
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(
    __name__
)  # Використовуємо __name__ для іменування логера

# Перевіряємо, чи є токен, перш ніж створювати об'єкт бота
if not TELEGRAM_BOT_TOKEN:
    logger.critical(
        "Не вдалося ініціалізувати бота: TELEGRAM_BOT_TOKEN не знайдено!"
    )
    # У цьому випадку, можливо, варто не створювати бота взагалі
    # або мати "dummy" бота, який не робить нічого, але не викликає помилок.
    # Для простоти, залишимо як є, але в реальному воркері це треба обробити.
    bot = None
else:
    bot = Bot(
        token=TELEGRAM_BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

dp = (
    Dispatcher()
)  # Dispatcher може бути не потрібен, якщо бот тільки відправляє


async def send_message_to_user(telegram_id: int, text: str) -> bool:
    """
    Відправляє повідомлення одному користувачу через Telegram API.

    Args:
        telegram_id: ID користувача або чату в Telegram.
        text: Текст повідомлення для відправки.

    Returns:
        True якщо повідомлення успішно відправлено, False в іншому випадку.
    """
    if not bot:
        logger.error(
            f"Спроба відправити повідомлення, але бот не ініціалізований "
            f"(немає токена). Chat_id={telegram_id}"
        )
        return False
    try:
        await bot.send_message(chat_id=telegram_id, text=text)
        logger.info(f"Повідомлення відправлено до chat_id={telegram_id}")
        return True
    except TelegramAPIError as e:
        logger.error(
            f"Помилка Telegram API при відправці до chat_id={telegram_id}: {e}"
        )
        return False
    except Exception as e:
        logger.error(
            f"Невідома помилка при відправці до chat_id={telegram_id}: {e}"
        )
        return False


async def send_messages_to_users(
    telegram_ids: list[int], text: str
) -> dict[int, bool]:
    """
    Відправляє повідомлення декільком отримувачам.

    Args:
        telegram_ids: Список ID користувачів або чатів.
        text: Текст повідомлення для відправки.

    Returns:
        Словник результатів відправки {telegram_id: success (bool)}.
    """
    if not bot:
        logger.error(
            "Спроба відправити повідомлення, але бот не ініціалізований "
            "(немає токена)."
        )
        return {tid: False for tid in telegram_ids}

    # Використовуємо asyncio.gather для паралельної відправки
    tasks = [send_message_to_user(tid, text) for tid in telegram_ids]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Формуємо результат
    final_results = {}
    for i, tid in enumerate(telegram_ids):
        result = results[i]
        if isinstance(result, Exception):
            logger.error(f"Помилка при відправці до {tid} в gather: {result}")
            final_results[tid] = False
        else:
            final_results[tid] = result
    return final_results


async def shutdown_bot_session():
    """Коректно закриває сесію бота."""
    if bot and bot.session:
        logger.info("Закриття сесії Telegram бота...")
        await bot.session.close()
        logger.info("Сесію Telegram бота закрито.")


# Блок if __name__ == "__main__" для тестування можна залишити або адаптувати
if __name__ == "__main__":
    # Приклад використання для тестування:
    async def main_test():
        # Важливо: для локального тестування переконайтеся, що .env файл з
        # TELEGRAM_BOT_TOKEN знаходиться в корені проєкту, щоб
        # telegram_bot.config міг його завантажити.
        if not bot:
            print("Бот не ініціалізований. Перевірте TELEGRAM_BOT_TOKEN.")
            return

        test_user_id = (
            123456789  # Замініть на реальний Telegram User ID для тесту
        )
        test_message = "Це тестове повідомлення від bot_core.py!"

        print(f"Надсилаю повідомлення до {test_user_id}...")
        success = await send_message_to_user(test_user_id, test_message)
        print(f"Результат відправки одному користувачу: {success}")

        test_user_ids = [
            test_user_id,
            987654321,
        ]  # Другий ID - неіснуючий для тесту помилки
        print(f"Надсилаю повідомлення до {test_user_ids}...")
        results_multiple = await send_messages_to_users(
            test_user_ids, test_message
        )
        print(f"Результати відправки декільком: {results_multiple}")

        await shutdown_bot_session()  # Закриваємо сесію після тестів

    asyncio.run(main_test())
