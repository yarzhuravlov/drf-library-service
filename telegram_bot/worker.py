import json
import logging
import asyncio
import signal

import redis.asyncio as redis
from redis import exceptions as redis_exceptions

# Імпорти з поточного додатку telegram_bot
from telegram_bot.bot_core import send_messages_to_users, shutdown_bot_session
from telegram_bot.config import (
    REDIS_HOST,
    REDIS_PORT,
    REDIS_DB,
    REDIS_PASSWORD,
    NOTIFICATIONS_QUEUE,
    LOG_LEVEL,
)

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, "INFO"),  # Fallback to INFO
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)  # Використовуємо __name__ для логера


async def process_message(message_data_json):
    """
    Обробляє одне повідомлення з черги Redis.

    Args:
        message_data_json (str): JSON-рядок з повідомленням

    Returns:
        dict: Результат відправки повідомлень {telegram_id: success}
    """
    try:
        message_content = json.loads(message_data_json)
        telegram_ids = message_content.get("telegram_ids")
        text_message = message_content.get("text")

        if not isinstance(telegram_ids, list) or not telegram_ids:
            logger.warning(
                f"Неправильний формат telegram_ids: {telegram_ids}. "
                f"Очікується непустий список цілих чисел."
            )
            return {}

        if not text_message or not isinstance(text_message, str):
            logger.warning(
                f"Відсутній або неправильний формат тексту "
                f"повідомлення: {text_message}"
            )
            return {}

        logger.info(
            f"Обробка повідомлення для {len(telegram_ids)} отримувачів."
        )
        # Відправка повідомлень
        return await send_messages_to_users(telegram_ids, text_message)

    except json.JSONDecodeError:
        logger.error(
            f"Помилка декодування JSON з повідомлення: {message_data_json}"
        )
        return {}
    except Exception as e:
        logger.error(
            f'Непередбачена помилка при обробці повідомлення "'
            f'{message_data_json}": {e}',
            exc_info=True,
        )
        return {}


class TelegramWorker:
    def __init__(self):
        self.redis_client = None
        self.running = False
        self._setup_signal_handlers()

    def _setup_signal_handlers(self):
        """Налаштовує обробники сигналів для коректного завершення."""
        # Обробка SIGINT (Ctrl+C) та SIGTERM
        for sig in [signal.SIGINT, signal.SIGTERM]:
            signal.signal(sig, self._graceful_shutdown)

    def _graceful_shutdown(self, signum, frame):
        """Обробник сигналу для поступового завершення роботи."""
        logger.info(
            f"Отримано сигнал {signum}, починаю завершення роботи воркера..."
        )
        self.running = False
        # Тут можна додати додаткову логіку очищення, якщо потрібно

    async def connect_to_redis(self):
        """Встановлює з'єднання з Redis."""
        logger.info(
            f"Підключення до Redis: {REDIS_HOST}:{REDIS_PORT}, DB: {REDIS_DB}"
        )
        try:
            self.redis_client = redis.Redis(
                host=REDIS_HOST,
                port=REDIS_PORT,
                db=REDIS_DB,
                password=REDIS_PASSWORD,
                decode_responses=True,  # Важливо для рядків, не байтів
                socket_timeout=10,  # Таймаут для операцій з сокетом
                socket_connect_timeout=5,  # Таймаут на підключення
            )
            await self.redis_client.ping()  # Перевірка з'єднання
            logger.info("Успішно підключено до Redis.")
        except redis_exceptions.ConnectionError as e:
            logger.error(f"Помилка підключення до Redis: {e}")
            # В реальних умовах тут може бути логіка повторних спроб
            self.redis_client = None  # Скидаємо клієнт
            raise  # Перевикидаємо помилку для обробки в main циклі

    async def listen_for_messages(self):
        """Основний цикл прослуховування черги Redis та обробки повідомлень."""
        if not self.redis_client:
            logger.error(
                "Redis клієнт не ініціалізований. " "Неможливо слухати чергу."
            )
            return

        self.running = True
        logger.info(
            f"TelegramWorker почав слухати чергу: {NOTIFICATIONS_QUEUE}"
        )

        while self.running:
            try:
                # BLPOP блокує до появи елемента або таймауту (1 секунда)
                raw_message_tuple = await self.redis_client.blpop(
                    NOTIFICATIONS_QUEUE, timeout=1
                )

                if not raw_message_tuple:  # Таймаут, немає повідомлень
                    await asyncio.sleep(
                        0.1  # Невелике очікування, щоб не навантажувати CPU
                    )
                    continue

                _queue_name, message_data_json = raw_message_tuple
                logger.debug(
                    f"Отримано сире повідомлення з черги: {message_data_json}"
                )

                # Обробка повідомлення через виділену функцію
                await process_message(message_data_json)

            except redis_exceptions.ConnectionError as e:
                logger.error(
                    f"Помилка з'єднання з Redis під час прослуховування: {e}. "
                    f"Спроба перепідключення..."
                )
                await self.close_redis_connection()
                await asyncio.sleep(5)
                try:
                    await self.connect_to_redis()
                except Exception as recon_e:
                    logger.error(
                        f"Не вдалося перепідключитися до Redis: {recon_e}. "
                        "Завершення роботи воркера."
                    )
                    self.running = False
            except Exception as e:
                # Ловимо інші можливі помилки в головному циклі слухача
                logger.error(
                    f"Критична помилка в циклі слухача Redis: {e}",
                    exc_info=True,
                )
                # Тут можна додати логіку очікування перед наступною ітерацією,
                # щоб уникнути швидкого циклічного виникнення помилок
                await asyncio.sleep(5)

        logger.info("TelegramWorker завершив прослуховування черги.")

    async def close_redis_connection(self):
        """Закриває з'єднання з Redis, якщо воно активне."""
        if self.redis_client:
            logger.info("Закриття з'єднання з Redis...")
            await self.redis_client.aclose()
            self.redis_client = None
            logger.info("З'єднання з Redis закрито.")


async def main_worker_loop():
    """Головна функція для запуску воркера."""
    worker = TelegramWorker()
    try:
        await worker.connect_to_redis()
        if worker.redis_client:  # Переконуємось, що підключення успішне
            await worker.listen_for_messages()
    except redis_exceptions.ConnectionError:
        logger.critical(
            "Не вдалося підключитися до Redis при старті. "
            "Воркер не запущено."
        )
    except Exception as e:
        logger.critical(
            f"Непередбачена помилка під час запуску або роботи воркера: {e}",
            exc_info=True,
        )
    finally:
        logger.info("Завершення роботи TelegramWorker main_worker_loop.")
        await worker.close_redis_connection()
        await shutdown_bot_session()  # Закриваємо сесію aiogram бота
        logger.info("TelegramWorker повністю зупинено.")


if __name__ == "__main__":
    # Цей блок дозволяє запустити воркер як окремий скрипт
    # python -m telegram_bot.worker
    logger.info(
        "Запуск Telegram Worker для обробки повідомлень з черги Redis..."
    )
    try:
        asyncio.run(main_worker_loop())
    except KeyboardInterrupt:
        logger.info("Telegram Worker зупинено вручну (KeyboardInterrupt).")
    except Exception as e:
        logger.critical(
            f"Критична помилка на верхньому рівні asyncio.run: {e}",
            exc_info=True,
        )
