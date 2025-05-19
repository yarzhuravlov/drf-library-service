import os
from dotenv import load_dotenv

load_dotenv()

# Налаштування для Telegram
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TELEGRAM_BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN не встановлено в .env файлі")

# Налаштування для Redis
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_DB = int(os.getenv("REDIS_DB", 0))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", None)

# Налаштування для Celery
CELERY_BROKER_URL = os.getenv(
    "CELERY_BROKER_URL", f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"
)

# Назва черги для повідомлень
NOTIFICATIONS_QUEUE = os.getenv("NOTIFICATIONS_QUEUE", "notifications")

# Налаштування логування
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
