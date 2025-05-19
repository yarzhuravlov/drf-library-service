import json
import logging
import asyncio
import signal

import redis.asyncio as redis

from notifications.bot import send_messages, start_bot, stop_bot
from notifications.config import (
    REDIS_HOST,
    REDIS_PORT,
    REDIS_DB,
    REDIS_PASSWORD,
    NOTIFICATIONS_QUEUE,
    LOG_LEVEL,
)

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class RedisListener:
    def __init__(self):
        self.redis = None
        self.running = False
        self._setup_signal_handlers()

    def _setup_signal_handlers(self):
        for sig in [signal.SIGINT, signal.SIGTERM]:
            signal.signal(sig, self._signal_handler)

    def _signal_handler(self, sig, frame):
        logger.info(f"Отримано сигнал {sig}, завершення роботи...")
        self.running = False

    async def connect(self):
        logger.info(f"Підключення до Redis: {REDIS_HOST}:{REDIS_PORT}")
        self.redis = redis.Redis(
            host=REDIS_HOST,
            port=REDIS_PORT,
            db=REDIS_DB,
            password=REDIS_PASSWORD,
            decode_responses=True,
        )
        logger.info("Підключено до Redis")

    async def listen(self):
        if not self.redis:
            await self.connect()

        self.running = True
        logger.info(f"Почав слухати чергу: {NOTIFICATIONS_QUEUE}")

        while self.running:
            try:
                raw_message = await self.redis.blpop(
                    NOTIFICATIONS_QUEUE, timeout=1
                )
                if not raw_message:
                    continue

                _, message_data = raw_message
                try:
                    message = json.loads(message_data)
                    telegram_ids = message.get("telegram_ids", [])
                    text = message.get("text", "")

                    if not telegram_ids or not text:
                        logger.warning(
                            f"Неправильний формат повідомлення: {message}"
                        )
                        continue

                    await send_messages(telegram_ids, text)

                except json.JSONDecodeError:
                    logger.error(f"Не вдалося розпарсити JSON: {message_data}")
                except Exception as e:
                    logger.error(f"Помилка при обробці повідомлення: {e}")

            except Exception as e:
                logger.error(
                    f"Помилка при отриманні повідомлення з Redis: {e}"
                )
                await asyncio.sleep(1)

    async def close(self):
        if self.redis:
            await self.redis.close()
            logger.info("З'єднання з Redis закрито")


async def main():
    try:
        bot_task = asyncio.create_task(start_bot())
        listener = RedisListener()
        await listener.connect()
        await listener.listen()
        await asyncio.gather(bot_task)
    except Exception as e:
        logger.error(f"Помилка у головному циклі: {e}")
    finally:
        await stop_bot()
        if hasattr(listener, "close"):
            await listener.close()


if __name__ == "__main__":
    logger.info("Запуск worker для обробки повідомлень")
    asyncio.run(main())
