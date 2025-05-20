import logging
from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from telegram_bot.config import API_BASE_URL
from telegram_bot.auth_handlers import get_valid_access_token
import requests

logger = logging.getLogger(__name__)
router = Router()


class BookStates(StatesGroup):
    waiting_for_search = State()


@router.message(Command("books"))
async def list_books(message: types.Message, state: FSMContext):
    access_token = await get_valid_access_token(state)
    if not access_token:
        await message.answer("Спочатку увійдіть через /login")
        return
    headers = {"Authorization": f"Bearer {access_token}"}
    try:
        resp = requests.get(
            f"{API_BASE_URL}books/", headers=headers, timeout=10
        )
        if resp.status_code == 200:
            books = resp.json().get("results", [])
            if not books:
                await message.answer("Книг не знайдено.")
                return
            text = "\n".join(
                [
                    f"{b['id']}. <b>{b['title']}</b> — {b['author']}"
                    for b in books
                ]
            )
            builder = InlineKeyboardBuilder()
            for b in books:
                builder.button(
                    text=f"Деталі {b['id']}", callback_data=f"book:{b['id']}"
                )
            builder.button(text="🔍 Пошук", callback_data="search_books")
            builder.adjust(2)
            await message.answer(
                f"📚 <b>Книги:</b>\n{text}", reply_markup=builder.as_markup()
            )
        else:
            await message.answer("Помилка отримання списку книг.")
    except Exception as e:
        logger.error(f"Books error: {e}")
        await message.answer("Помилка підключення до бекенду.")


@router.callback_query(F.data.startswith("book:"))
async def book_details(callback: types.CallbackQuery, state: FSMContext):
    book_id = callback.data.split(":")[1]
    access_token = await get_valid_access_token(state)
    if not access_token:
        await callback.answer("Спочатку увійдіть через /login")
        return
    headers = {"Authorization": f"Bearer {access_token}"}
    try:
        resp = requests.get(
            f"{API_BASE_URL}books/{book_id}/", headers=headers, timeout=10
        )
        if resp.status_code == 200:
            b = resp.json()
            text = f"<b>{b['title']}</b>\nАвтор: {b['author']}\nДоступно: {b['inventory']}\nЦіна/день: {b['daily_fee']}"
            builder = InlineKeyboardBuilder()
            if b["inventory"] > 0:
                builder.button(
                    text="Орендувати", callback_data=f"borrow:{book_id}"
                )
            builder.button(text="⬅️ Назад", callback_data="back_books")
            await callback.message.answer(
                text, reply_markup=builder.as_markup()
            )
        else:
            await callback.message.answer("Книгу не знайдено.")
    except Exception as e:
        logger.error(f"Book details error: {e}")
        await callback.message.answer("Помилка підключення до бекенду.")


@router.callback_query(F.data == "search_books")
async def search_books_start(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("Введіть назву або автора для пошуку:")
    await state.set_state(BookStates.waiting_for_search)


@router.message(BookStates.waiting_for_search)
async def search_books(message: types.Message, state: FSMContext):
    query = message.text.strip()
    access_token = await get_valid_access_token(state)
    if not access_token:
        await message.answer("Спочатку увійдіть через /login")
        await state.clear()
        return
    headers = {"Authorization": f"Bearer {access_token}"}
    try:
        resp = requests.get(
            f"{API_BASE_URL}books/?search={query}", headers=headers, timeout=10
        )
        if resp.status_code == 200:
            books = resp.json().get("results", [])
            if not books:
                await message.answer("Нічого не знайдено.")
                await state.clear()
                return
            text = "\n".join(
                [
                    f"{b['id']}. <b>{b['title']}</b> — {b['author']}"
                    for b in books
                ]
            )
            builder = InlineKeyboardBuilder()
            for b in books:
                builder.button(
                    text=f"Деталі {b['id']}", callback_data=f"book:{b['id']}"
                )
            builder.button(text="⬅️ Назад", callback_data="back_books")
            builder.adjust(2)
            await message.answer(
                f"🔍 <b>Результати:</b>\n{text}",
                reply_markup=builder.as_markup(),
            )
        else:
            await message.answer("Помилка пошуку.")
        await state.clear()
    except Exception as e:
        logger.error(f"Search error: {e}")
        await message.answer("Помилка підключення до бекенду.")
        await state.clear()


@router.callback_query(F.data == "back_books")
async def back_books(callback: types.CallbackQuery, state: FSMContext):
    await list_books(callback.message, state)


@router.callback_query(F.data.startswith("borrow:"))
async def borrow_book(callback: types.CallbackQuery, state: FSMContext):
    book_id = callback.data.split(":")[1]
    access_token = await get_valid_access_token(state)
    if not access_token:
        await callback.answer("Спочатку увійдіть через /login")
        return
    headers = {"Authorization": f"Bearer {access_token}"}
    try:
        resp = requests.post(
            f"{API_BASE_URL}borrowings/",
            json={"book": book_id},
            headers=headers,
            timeout=10,
        )
        if resp.status_code == 201:
            await callback.message.answer("✅ Книгу орендовано!")
        else:
            await callback.message.answer("❌ Не вдалося орендувати книгу.")
    except Exception as e:
        logger.error(f"Borrow error: {e}")
        await callback.message.answer("Помилка підключення до бекенду.")
