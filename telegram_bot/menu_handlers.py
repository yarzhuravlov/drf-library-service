import logging
from aiogram import Router, F, types
from aiogram.filters import Command, CommandStart
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from aiogram.fsm.context import FSMContext
import requests
from telegram_bot.config import API_BASE_URL
from telegram_bot.auth_handlers import get_valid_access_token

logger = logging.getLogger(__name__)
router = Router()


@router.message(CommandStart())
async def command_start(message: types.Message):
    welcome_text = (
        f"👋 Привіт, {message.from_user.first_name}!\n\n"
        f"Я бот бібліотеки. Можливості:\n"
        f"📚 Книги | 📋 Оренди | 👤 Профіль | 💰 Баланс | ℹ️ Допомога"
    )
    builder = ReplyKeyboardBuilder()
    builder.button(text="📚 Книги")
    builder.button(text="📋 Мої оренди")
    builder.button(text="👤 Профіль")
    builder.button(text="💰 Баланс")
    builder.button(text="ℹ️ Допомога")
    builder.adjust(2)
    await message.answer(
        welcome_text, reply_markup=builder.as_markup(resize_keyboard=True)
    )


@router.message(Command("help"))
async def command_help(message: types.Message):
    help_text = (
        "📋 <b>Команди:</b>\n"
        "/start — Головне меню\n"
        "/login — Вхід\n"
        "/logout — Вихід\n"
        "/books — Книги\n"
        "/my_borrowings — Оренди\n"
        "/profile — Профіль\n"
        "/help — Допомога\n"
        "\nВикористовуйте кнопки для навігації."
    )
    await message.answer(help_text)


# Хендлери для кнопок меню
@router.message(F.text == "📚 Книги")
async def books_button(message: types.Message, state: FSMContext):
    # Отримуємо валідний токен з можливим автооновленням
    access_token = await get_valid_access_token(state)
    if not access_token:
        await message.answer("Спочатку увійдіть через /login")
        return

    # Перенаправляємо на хендлер команди /books з book_handlers.py
    from telegram_bot.book_handlers import list_books

    await list_books(message, state)


@router.message(F.text == "📋 Мої оренди")
async def borrowings_button(message: types.Message, state: FSMContext):
    # Отримуємо валідний токен з можливим автооновленням
    access_token = await get_valid_access_token(state)
    if not access_token:
        await message.answer("Спочатку увійдіть через /login")
        return

    # Показуємо список орендованих книг користувача
    headers = {"Authorization": f"Bearer {access_token}"}
    try:
        resp = requests.get(
            f"{API_BASE_URL}borrowings/", headers=headers, timeout=10
        )
        if resp.status_code == 200:
            borrowings = resp.json()
            if not borrowings:
                await message.answer("У вас немає активних оренд.")
                return
            text = "\n".join(
                [
                    f"{b['id']}. {b['book']} {b['borrow_date']} — {b['expected_return_date']}"
                    for b in borrowings
                ]
            )
            await message.answer(f"📋 <b>Ваші оренди:</b>\n{text}")
        else:
            await message.answer("Помилка отримання оренд.")
    except Exception as e:
        logger.error(f"Borrowings error: {e}")
        await message.answer("Помилка підключення до бекенду.")


@router.message(F.text == "👤 Профіль")
async def profile_button(message: types.Message, state: FSMContext):
    # Отримуємо валідний токен з можливим автооновленням
    access_token = await get_valid_access_token(state)
    if not access_token:
        await message.answer("Спочатку увійдіть через /login")
        return

    # Перенаправляємо на хендлер команди /profile з user_handlers.py
    from telegram_bot.user_handlers import profile

    await profile(message, state)


@router.message(F.text == "💰 Баланс")
async def balance_button(message: types.Message, state: FSMContext):
    # Отримуємо валідний токен з можливим автооновленням
    access_token = await get_valid_access_token(state)
    if not access_token:
        await message.answer("Спочатку увійдіть через /login")
        return

    # Показуємо баланс користувача
    headers = {"Authorization": f"Bearer {access_token}"}
    try:
        resp = requests.get(
            f"{API_BASE_URL}payments/payment/balance/",
            headers=headers,
            timeout=10,
        )
        if resp.status_code == 200:
            balance = resp.json().get("balance", 0)
            await message.answer(f"💰 <b>Ваш баланс:</b> {balance} грн")
        else:
            await message.answer("Помилка отримання балансу.")
    except Exception as e:
        logger.error(f"Balance error: {e}")
        await message.answer("Помилка підключення до бекенду.")


@router.message(F.text == "ℹ️ Допомога")
async def help_button(message: types.Message):
    # Перенаправляємо на хендлер команди /help
    await command_help(message)


@router.message()
async def unknown_message(message: types.Message):
    await message.answer(
        "Я не розумію цю команду. Скористайся меню або /help."
    )
