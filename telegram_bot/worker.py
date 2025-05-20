import json
import logging
import asyncio
import signal

import redis.asyncio as redis
from redis import exceptions as redis_exceptions

# Imports from current telegram_bot app
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
logger = logging.getLogger(__name__)  # Use __name__ for logger


async def process_message(message_data_json):
    """
    Processes one message from the Redis queue.

    Args:
        message_data_json (str): JSON string with message

    Returns:
        dict: Result of sending messages {telegram_id: success}
    """
    try:
        message_content = json.loads(message_data_json)
        telegram_ids = message_content.get("telegram_ids")
        text_message = message_content.get("text")

        if not isinstance(telegram_ids, list) or not telegram_ids:
            logger.warning(
                f"Invalid format for telegram_ids: {telegram_ids}. "
                f"Expected a non-empty list of integers."
            )
            return {}

        if not text_message or not isinstance(text_message, str):
            logger.warning(
                f"Missing or invalid format for "
                f"message text: {text_message}"
            )
            return {}

        logger.info(f"Processing message for {len(telegram_ids)} recipients.")
        # Send messages
        return await send_messages_to_users(telegram_ids, text_message)

    except json.JSONDecodeError:
        logger.error(f"Error decoding JSON from message: {message_data_json}")
        return {}
    except Exception as e:
        logger.error(
            f'Unexpected error processing message "'
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
        """Sets up signal handlers for proper shutdown."""
        # Handle SIGINT (Ctrl+C) and SIGTERM
        for sig in [signal.SIGINT, signal.SIGTERM]:
            signal.signal(sig, self._graceful_shutdown)

    def _graceful_shutdown(self, signum, frame):
        """Signal handler for graceful shutdown."""
        logger.info(f"Received signal {signum}, starting worker shutdown...")
        self.running = False
        # Additional cleanup logic can be added here if needed

    async def connect_to_redis(self):
        """Establishes connection to Redis."""
        logger.info(
            f"Connecting to Redis: {REDIS_HOST}:{REDIS_PORT}, DB: {REDIS_DB}"
        )
        try:
            self.redis_client = redis.Redis(
                host=REDIS_HOST,
                port=REDIS_PORT,
                db=REDIS_DB,
                password=REDIS_PASSWORD,
                decode_responses=True,  # Important for strings, not bytes
                socket_timeout=10,  # Socket operation timeout
                socket_connect_timeout=5,  # Connection timeout
            )
            await self.redis_client.ping()  # Check connection
            logger.info("Successfully connected to Redis.")
        except redis_exceptions.ConnectionError as e:
            logger.error(f"Error connecting to Redis: {e}")
            # In real conditions, retry logic could be added here
            self.redis_client = None  # Reset client
            raise  # Re-raise error for handling in main loop

    async def listen_for_messages(self):
        """Main loop for listening to Redis queue and processing messages."""
        if not self.redis_client:
            logger.error(
                "Redis client not initialized. " "Cannot listen to queue."
            )
            return

        self.running = True
        logger.info(
            f"TelegramWorker started listening to queue: {NOTIFICATIONS_QUEUE}"
        )

        while self.running:
            try:
                # BLPOP blocks until an element appears or timeout (1 second)
                raw_message_tuple = await self.redis_client.blpop(
                    NOTIFICATIONS_QUEUE, timeout=1
                )

                if not raw_message_tuple:  # Timeout, no messages
                    await asyncio.sleep(
                        0.1  # Small wait to avoid CPU overload
                    )
                    continue

                _queue_name, message_data_json = raw_message_tuple
                logger.debug(
                    f"Received raw message from queue: {message_data_json}"
                )

                # Process message through dedicated function
                await process_message(message_data_json)

            except redis_exceptions.ConnectionError as e:
                logger.error(
                    f"Redis connection error during listening: {e}. "
                    f"Attempting to reconnect..."
                )
                await self.close_redis_connection()
                await asyncio.sleep(5)
                try:
                    await self.connect_to_redis()
                except Exception as recon_e:
                    logger.error(
                        f"Failed to reconnect to Redis: {recon_e}. "
                        "Stopping worker."
                    )
                    self.running = False
            except Exception as e:
                # Catch other possible errors in the main listener loop
                logger.error(
                    f"Critical error in Redis listener loop: {e}",
                    exc_info=True,
                )
                # Add logic to wait before next iteration
                # to avoid rapid cycling of errors
                await asyncio.sleep(5)

        logger.info("TelegramWorker finished listening to queue.")

    async def close_redis_connection(self):
        """Closes the Redis connection if active."""
        if self.redis_client:
            logger.info("Closing Redis connection...")
            await self.redis_client.aclose()
            self.redis_client = None
            logger.info("Redis connection closed.")


async def main_worker_loop():
    """Main function to start the worker."""
    worker = TelegramWorker()
    try:
        await worker.connect_to_redis()
        if worker.redis_client:  # Ensure connection is successful
            await worker.listen_for_messages()
    except redis_exceptions.ConnectionError:
        logger.critical(
            "Failed to connect to Redis at startup. " "Worker not started."
        )
    except Exception as e:
        logger.critical(
            f"Unexpected error during worker startup or operation: {e}",
            exc_info=True,
        )
    finally:
        logger.info("Finishing TelegramWorker main_worker_loop.")
        await worker.close_redis_connection()
        await shutdown_bot_session()  # Close aiogram bot session
        logger.info("TelegramWorker fully stopped.")


if __name__ == "__main__":
    # This block allows running the worker as a separate script
    # python -m telegram_bot.worker
    logger.info(
        "Starting Telegram Worker to process messages from Redis queue..."
    )
    try:
        asyncio.run(main_worker_loop())
    except KeyboardInterrupt:
        logger.info("Telegram Worker stopped manually (KeyboardInterrupt).")
    except Exception as e:
        logger.critical(
            f"Critical error at the top level of asyncio.run: {e}",
            exc_info=True,
        )
