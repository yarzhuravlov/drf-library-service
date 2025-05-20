import os
from dotenv import load_dotenv
from pathlib import Path

# Визначаємо шлях до директорії, де знаходиться цей config.py
current_dir = Path(__file__).resolve().parent
# Формуємо шлях до файлу .env у цій же директорії
dotenv_path = current_dir / ".env"

# Завантажуємо змінні з .env файлу, що знаходиться поруч з config.py
if dotenv_path.exists():
    load_dotenv(dotenv_path=dotenv_path)
else:
    # Якщо локального .env немає, спробуємо завантажити з кореня проєкту
    load_dotenv()

# Налаштування для Telegram
TELEGRAM_BOT_TOKEN = (
    os.getenv("TELEGRAM_BOT_TOKEN")
    or os.getenv("BOT_TOKEN")
    or os.getenv("TELEGRAM_TOKEN")
)
if not TELEGRAM_BOT_TOKEN:
    print(
        "CRITICAL: Токен бота не знайдено. "
        "Перевірте наявність змінної TELEGRAM_TOKEN в .env файлі."
    )

# Налаштування для Redis (для підключення воркера до черги)
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_DB = int(os.getenv("REDIS_DB", 0))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", None)

# Назва черги, яку буде слухати цей воркер
NOTIFICATIONS_QUEUE = os.getenv("NOTIFICATIONS_QUEUE", "notifications")

# Налаштування логування
LOG_LEVEL = os.getenv("LOG_LEVEL_TELEGRAM_BOT", "INFO")

# URL для запитів до Django API
API_BASE_URL = os.getenv("API_BASE_URL", "http://app:8000/api/")
