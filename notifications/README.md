# Notifications Service

Сервіс сповіщень через Telegram для системи управління бібліотекою.

## Опис

Цей сервіс слухає чергу повідомлень (Redis) та надсилає сповіщення через Telegram бота. Інтеграція з основним Django-додатком відбувається через Celery (рекомендовано) або напряму через Redis.

### Основні компоненти

- `bot.py`: Логіка взаємодії з Telegram API за допомогою `aiogram`.
- `worker.py`: Асинхронний воркер, який слухає чергу Redis (`NOTIFICATIONS_QUEUE`) і викликає `bot.py` для відправки повідомлень.
- `handlers.py`: Містить функції для надсилання повідомлень у чергу з Django (через Celery або напряму в Redis).
- `tasks.py`: Celery-завдання, яке викликає відповідний хендлер для постановки повідомлення в Redis.
- `config.py`: Завантаження конфігурацій (токени, налаштування Redis) з `.env` файлу.
- `daily_checks.py`: Приклад логіки для періодичних завдань (наприклад, перевірка прострочених боргів), які можуть надсилати сповіщення.

## Встановлення і налаштування

### Вимоги

- Python 3.8+
- Redis (локально або в Docker)
- Запущений Django-проєкт з налаштованим Celery (якщо використовується Celery для відправки).
- Telegram Bot (створений через @BotFather).

### Локальне встановлення

1.  Переконайтеся, що ви перебуваєте в кореневій директорії Django-проєкту.
2.  Встановіть залежності для сервісу сповіщень (також переконайтеся, що основні залежності Django-проєкту встановлені):
    ```bash
    pip install -r notifications/requirements.txt
    ```
3.  Створіть файл `.env` у директорії `notifications` на основі файлу `notifications/.env.sample`.
4.  Заповніть файл `notifications/.env`:
    - `TELEGRAM_BOT_TOKEN`: Ваш токен Telegram бота, отриманий від @BotFather.
    - `REDIS_HOST`, `REDIS_PORT`, `REDIS_DB`, `REDIS_PASSWORD`: Параметри підключення до вашого Redis сервера.
    - `CELERY_BROKER_URL`: URL брокера Celery (має вказувати на той самий Redis, якщо Celery використовує Redis).
    - `NOTIFICATIONS_QUEUE`: Назва черги Redis, яку буде слухати `notifications/worker.py`.
    - `LOG_LEVEL`: Рівень логування (INFO, DEBUG тощо).

## Інтеграція з Django

Для надсилання сповіщень з вашого Django-коду використовуйте функцію `send_telegram_notification_django` з `notifications.handlers`.

````python
from notifications.handlers import send_telegram_notification_django

# Приклад відправки (за замовчуванням використовує Celery)
send_telegram_notification_django(
    telegram_ids=[123456789],  # список ID користувачів або чатів Telegram
    text="Ваше HTML-форматоване повідомлення тут"
)

**Важливо:**


- Ви використовуєте Celery, переконайтеся, що Celery правильно налаштовано у вашому Django-проєкті (має бути файл `your_project_name/celery.py` та відповідні налаштування в `settings.py`).

## Формат повідомлень у черзі Redis

Скрипт `notifications/worker.py` очікує з черги Redis (`NOTIFICATIONS_QUEUE`) повідомлення у форматі JSON:

```json
{
  "telegram_ids": [123456789, 987654321],
  "text": "Текст повідомлення (може містити HTML-теги для форматування)"
}
````

## Ручне тестування сповіщень

Щоб протестувати весь ланцюжок надсилання сповіщень вручну:

1.  **Запустіть Redis сервер.** Переконайтеся, що він доступний за адресою та портом, вказаними у `notifications/.env`.

2.  **Запустіть Celery Worker** (якщо плануєте тестувати через Celery):
    Відкрийте термінал у кореневій директорії Django-проєкту, активуйте віртуальне середовище та виконайте:

    ```bash
    celery -A <your_project_name> worker -l info --pool=solo
    ```

    Замініть `<your_project_name>` на назву вашої папки з конфігурацією Django (наприклад, `config`, якщо у вас `config/settings.py` та `config/celery.py`).
    Прапор `--pool=solo` рекомендується для Windows, якщо не налаштовані інші пули.
    Слідкуйте за логами цього воркера.

3.  **Запустіть Telegram Worker (`notifications/worker.py`):**
    Відкрийте **другий** термінал, також у кореневій директорії проєкту, активуйте віртуальне середовище та виконайте:

    ```bash
    python -m notifications.worker
    ```

    Цей скрипт підключиться до Redis, почне слухати чергу `NOTIFICATIONS_QUEUE` та ініціалізує Telegram-бота. Слідкуйте за його логами.

4.  **Надішліть тестове повідомлення з Django Shell:**
    Відкрийте **третій** термінал, у кореневій директорії проєкту, активуйте середовище та запустіть Django shell:

    ```bash
    python manage.py shell
    ```

    У shell виконайте:

    ```python
    from notifications.handlers import send_telegram_notification_django

    # Замініть TELEGRAM_CHAT_ID на ID вашого реального чату/користувача в Telegram,
    # якому бот має право писати.
    # Щоб отримати свій ID, можна написати боту @userinfobot (після того, як ви хоча б раз написали вашому боту).
    TELEGRAM_CHAT_ID = Your_Actual_Chat_ID

    # Тестування через Celery (якщо Celery worker запущений)
    result_celery = send_telegram_notification_django(
        telegram_ids=[TELEGRAM_CHAT_ID],
        text="👋 <b>Тест Celery:</b> Повідомлення надіслано через Django shell!"
    )
    print(f"Результат Celery: {'Успішно поставлено в чергу' if result_celery else 'Помилка постановки в чергу'}")

    # Тестування напряму через Redis (notifications/worker.py має бути запущений)
    result_redis = send_telegram_notification_django(
        telegram_ids=[TELEGRAM_CHAT_ID],
        text=" bezpośrednio przez Redis!",
        use_celery=False
    )
    print(f"Результат Redis: {'Успішно поставлено в чергу' if result_redis else 'Помилка постановки в чергу'}")
    ```

5.  **Перевірка результату:**
    - Ви маєте отримати два повідомлення у вашому Telegram-клієнті на вказаний `TELEGRAM_CHAT_ID`.
    - Логи Celery worker (термінал 2) мають показати обробку завдання.
    - Логи `notifications/worker.py` (термінал 3) мають показати отримання повідомлень з Redis та їх відправку через Telegram.

### Моніторинг черг Redis (опціонально)

Для спостереження за активністю в чергах Redis можна використати команду `MONITOR` в `redis-cli` (використовуйте обережно, може вплинути на продуктивність) або перевіряти довжину черг командою `LLEN <queue_name>`.

## Розгортання через Docker Compose

Для запуску сервісу сповіщень разом з іншими компонентами вашого проєкту (Redis, Django, Celery worker) через Docker Compose, ви можете додати наступну конфігурацію до вашого основного файлу `docker-compose.yml`:

```yaml
version: "3.8"

services:
  redis:
    image: redis:alpine
    ports:
      - "6379:6379"
    # Інші налаштування Redis...

  django_app: # Ваша основна Django-аплікація
    build: .
    # ... інші налаштування ...
    depends_on:
      - redis

  celery_worker: # Celery worker для Django
    build: .
    command: celery -A <your_project_name> worker -l info --pool=solo
    # ... інші налаштування ...
    depends_on:
      - redis
      - django_app

  notifications_worker:
    build:
      context: . # Якщо Dockerfile для notifications_worker в корені
      dockerfile: notifications/Dockerfile # Або вкажіть шлях до Dockerfile
    # Якщо notifications/Dockerfile очікує .env файл в своїй директорії збірки:
    # env_file:
    #   - ./notifications/.env
    # Або передавайте змінні середовища напряму:
    environment:
      - TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN}
      - REDIS_HOST=redis # Використовуємо назву сервісу Redis з Docker Compose
      - REDIS_PORT=6379
      # ... інші змінні з notifications/.env ...
    depends_on:
      - redis
    restart: always
# volumes:
#   redis_data:
```

**Примітка:** Docker-конфігурація вище є прикладом і може потребувати адаптації до структури вашого проєкту та вмісту `notifications/Dockerfile`.

## Масштабування

Скрипт `notifications/worker.py` можна масштабувати горизонтально, запускаючи кілька його екземплярів. Кожен екземпляр буде незалежно слухати чергу Redis. Це може бути корисно при великому потоці сповіщень.

## Тестування (автоматичне)

Для запуску автоматичних тестів, що знаходяться в `notifications/tests.py`:

```bash
python manage.py test notifications
```
