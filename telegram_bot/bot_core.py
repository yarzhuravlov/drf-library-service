import logging
import asyncio
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramAPIError

# Import configuration from current telegram_bot app
from telegram_bot.config import TELEGRAM_BOT_TOKEN, LOG_LEVEL
from telegram_bot.auth_handlers import router as auth_router
from telegram_bot.menu_handlers import router as menu_router
from telegram_bot.book_handlers import router as book_router
from telegram_bot.user_handlers import router as user_router

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)  # Use __name__ for logger naming

# Check if token exists before creating bot object
if not TELEGRAM_BOT_TOKEN:
    logger.critical("Failed to initialize bot: TELEGRAM_BOT_TOKEN not found!")
    raise ValueError("TELEGRAM_BOT_TOKEN not set. Bot cannot be initialized.")
else:
    bot = Bot(
        token=TELEGRAM_BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

dp = Dispatcher()
dp.include_router(auth_router)
dp.include_router(book_router)
dp.include_router(user_router)
dp.include_router(menu_router)


async def send_message_to_user(telegram_id: int, text: str) -> bool:
    """
    Sends a message to a single user via Telegram API.

    Args:
        telegram_id: User's or chat's ID in Telegram.
        text: Message text to send.

    Returns:
        True if the message was successfully sent, False otherwise.
    """
    if not bot:
        logger.error(
            f"Attempt to send a message, but bot is not initialized "
            f"(no token). Chat_id={telegram_id}"
        )
        return False
    try:
        await bot.send_message(chat_id=telegram_id, text=text)
        logger.info(f"Message sent to chat_id={telegram_id}")
        return True
    except TelegramAPIError as e:
        logger.error(
            f"Telegram API error when sending to chat_id={telegram_id}: {e}"
        )
        return False
    except Exception as e:
        logger.error(
            f"Unknown error when sending to chat_id={telegram_id}: {e}"
        )
        return False


async def send_messages_to_users(
    telegram_ids: list[int], text: str
) -> dict[int, bool]:
    """
    Sends messages to multiple recipients.

    Args:
        telegram_ids: List of user or chat IDs.
        text: Message text to send.

    Returns:
        Dictionary of send results {telegram_id: success (bool)}.
    """
    if not bot:
        logger.error(
            "Attempt to send a message, but bot is not initialized "
            "(no token)."
        )
        return {tid: False for tid in telegram_ids}

    # Use asyncio.gather for parallel sending
    tasks = [send_message_to_user(tid, text) for tid in telegram_ids]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Format the result
    final_results = {}
    for i, tid in enumerate(telegram_ids):
        result = results[i]
        if isinstance(result, Exception):
            logger.error(f"Error when sending to {tid} in gather: {result}")
            final_results[tid] = False
        else:
            final_results[tid] = result
    return final_results


async def shutdown_bot_session():
    """Properly closes the bot session."""
    if bot and bot.session:
        logger.info("Closing Telegram bot session...")
        await bot.session.close()
        logger.info("Telegram bot session closed.")
