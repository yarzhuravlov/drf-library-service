import logging
import asyncio
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramAPIError

from notifications.config import TELEGRAM_BOT_TOKEN, LOG_LEVEL

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

bot = Bot(
    token=TELEGRAM_BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML),
)
dp = Dispatcher()


async def send_message(telegram_id, text):
    """
    Відправляє повідомлення через Telegram API

    Args:
        telegram_id (int): ID користувача або чату в Telegram
        text (str): Текст повідомлення для відправки

    Returns:
        bool: True якщо повідомлення успішно відправлено,
        False в іншому випадку

    """
    try:
        await bot.send_message(chat_id=telegram_id, text=text)
        logger.info(f"Повідомлення відправлено до chat_id={telegram_id}")
        return True
    except TelegramAPIError as e:
        logger.error(
            f"Помилка при відправці повідомлення до chat_id={telegram_id}: {e}"
        )
        return False


async def send_messages(telegram_ids, text):
    """
    Відправляє повідомлення декільком отримувачам

    Args:
        telegram_ids (list): Список ID користувачів або чатів
        text (str): Текст повідомлення для відправки

    Returns:
        dict: Словник результатів відправки {telegram_id: success (bool)}
    """
    tasks = [send_message(tid, text) for tid in telegram_ids]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return {
        tid: not isinstance(result, Exception) and result
        for tid, result in zip(telegram_ids, results)
    }


async def start_bot():
    """Запускає бота для роботи (polling)"""
    logger.info("Запуск Telegram бота")
    await dp.start_polling(bot)


async def stop_bot():
    """Зупиняє бота"""
    logger.info("Зупинка Telegram бота")
    await bot.session.close()


if __name__ == "__main__":
    # Для тестування окремо
    async def main():
        # Приклад використання
        test_id = 368222740  # замінити на реальний ID
        result = await send_message(test_id, "Тестове повідомлення від бота")
        print(f"Результат відправки: {result}")

    asyncio.run(main())
