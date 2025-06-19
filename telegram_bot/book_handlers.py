import logging
from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from telegram_bot.auth_handlers import get_valid_access_token
from telegram_bot.request_service import (
    get_books,
    get_book_details,
    borrow_book as api_borrow_book,
)

logger = logging.getLogger(__name__)
router = Router()


def format_authors(authors):
    """Formats the list of authors into a string"""
    if not authors or not isinstance(authors, list):
        return "Unknown author"

    formatted_authors = []
    for author in authors:
        if isinstance(author, dict):
            first_name = author.get("first_name", "")
            last_name = author.get("last_name", "")
            if first_name or last_name:
                formatted_authors.append(f"{first_name} {last_name}".strip())

    if not formatted_authors:
        return "Unknown author"

    return ", ".join(formatted_authors)


class BookStates(StatesGroup):
    waiting_for_search = State()


@router.message(Command("books"))
async def list_books(message: types.Message, state: FSMContext):
    access_token = await get_valid_access_token(state)
    if not access_token:
        await message.answer("❗ First, log in via /login")
        return

    try:
        books = await get_books(access_token)
        if not books:
            await message.answer("📚 No books found.")
            return

        book_lines = []
        for b in books:
            book_lines.append(
                f"📕 <b>{b.get('title', 'Untitled')}</b>\n"
                f"   🆔 #{b['id']}\n"
                f"   ✍️ Author: {format_authors(b.get('authors', []))}\n"
                f"   💰 {b.get('daily_fee', 0)} UAH/DAY"
            )

        text = "\n\n".join(book_lines)

        builder = InlineKeyboardBuilder()
        for b in books:
            builder.button(
                text=f"📖 Details #{b['id']}", callback_data=f"book:{b['id']}"
            )
        builder.button(text="🔍 Search books", callback_data="search_books")
        builder.adjust(2)

        await message.answer(
            f"📚 <b>Available books:</b>\n\n{text}",
            reply_markup=builder.as_markup(),
        )
    except Exception as e:
        logger.error(f"Books error: {e}")
        await message.answer("❌ Error retrieving book list.")


@router.callback_query(F.data.startswith("book:"))
async def book_details(callback: types.CallbackQuery, state: FSMContext):
    book_id = callback.data.split(":")[1]
    access_token = await get_valid_access_token(state)
    if not access_token:
        await callback.answer("❗ First, log in via /login")
        return

    try:
        b = await get_book_details(access_token, book_id)
        if not b:
            await callback.message.answer("❌ Book not found.")
            return

        cover_type = b.get("cover", "").capitalize()
        if cover_type == "Hard":
            cover_emoji = "📔"
            cover_text = "Hard"
        elif cover_type == "Soft":
            cover_emoji = "📓"
            cover_text = "Soft"
        else:
            cover_emoji = "📖"
            cover_text = "Not specified"

        inventory = b.get("inventory", 0)
        if inventory > 0:
            availability = f"✅ In stock: {inventory} pcs."
        else:
            availability = "❌ Not available"

        text = (
            f"📕 <b>{b.get('title', 'Untitled')}</b>\n\n"
            f"🆔 <b>ID book:</b> #{book_id}\n"
            f"✍️ <b>Author:</b> {format_authors(b.get('authors', []))}\n"
            f"{cover_emoji} <b>Cover:</b> {cover_text}\n"
            f"💰 <b>Rental price:</b> {b.get('daily_fee', 0)} UAH/DAY\n"
            f"{availability}"
        )

        builder = InlineKeyboardBuilder()
        if b.get("inventory", 0) > 0:
            builder.button(text="📋 Rent", callback_data=f"borrow:{book_id}")
        builder.button(text="⬅️ Back to list", callback_data="back_books")

        await callback.message.answer(text, reply_markup=builder.as_markup())
    except Exception as e:
        logger.error(f"Book details error: {e}")
        await callback.message.answer("❌ Error retrieving book data.")


@router.callback_query(F.data == "search_books")
async def search_books_start(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("🔍 Enter a title or author to search:")
    await state.set_state(BookStates.waiting_for_search)


@router.message(BookStates.waiting_for_search)
async def search_books(message: types.Message, state: FSMContext):
    query = message.text.strip()
    access_token = await get_valid_access_token(state)
    if not access_token:
        await message.answer("❗ First, log in via /login")
        await state.clear()
        return

    try:
        books = await get_books(access_token, query)
        if not books:
            await message.answer("🔍 Nothing found for your query..")
            await state.clear()
            return

        book_lines = []
        for b in books:
            book_lines.append(
                f"📕 <b>{b.get('title', 'Untitle')}</b>\n"
                f"   🆔 #{b['id']}\n"
                f"   ✍️ Author: {format_authors(b.get('authors', []))}\n"
                f"   💰 {b.get('daily_fee', 0)} UAH/DAY"
            )

        text = "\n\n".join(book_lines)

        builder = InlineKeyboardBuilder()
        for b in books:
            builder.button(
                text=f"📖 Detail #{b['id']}", callback_data=f"book:{b['id']}"
            )

        builder.button(text="⬅️ Back to the books", callback_data="back_books")
        builder.adjust(2)

        search_text = f"🔍 <b>Results by query:</b> '{query}'"
        await message.answer(
            f"{search_text}\n\n{text}",
            reply_markup=builder.as_markup(),
        )
        await state.clear()
    except Exception as e:
        logger.error(f"Search error: {e}")
        await message.answer("❌ Error while searching for books.")
        await state.clear()


@router.callback_query(F.data == "back_books")
async def back_books(callback: types.CallbackQuery, state: FSMContext):
    await list_books(callback.message, state)


@router.callback_query(F.data.startswith("borrow:"))
async def borrow_book(callback: types.CallbackQuery, state: FSMContext):
    book_id = callback.data.split(":")[1]
    access_token = await get_valid_access_token(state)
    if not access_token:
        await callback.answer("❗ First, log in via /login")
        return

    try:
        book = await get_book_details(access_token, book_id)
        if book:
            book_title = book.get("title", f"Book #{book_id}")
        else:
            book_title = f"Book #{book_id}"

        success, result = await api_borrow_book(access_token, book_id)
        if success:
            from datetime import date, timedelta

            today = date.today()
            expected_return = today + timedelta(days=14)

            message_text = (
                f"✅ <b>Book successfully rented!</b>\n\n"
                f"📕 <b>{book_title}</b>\n"
                f"📅 Date of lease: {today.strftime('%Y-%m-%d')}\n"
                f"🔄 Return to: {expected_return.strftime('%Y-%m-%d')}\n\n"
                f"Good reading! 📚"
            )
            await callback.message.answer(message_text)
        else:
            message_text = (
                f"❌ <b>Unable to rent book:</b>\n\n"
                f"📕 <b>{book_title}</b>\n"
                f"❗ Reason: {result}"
            )
            await callback.message.answer(message_text)
    except Exception as e:
        logger.error(f"Borrow error: {e}")
        msg = "❌ Server connection failed. Please try again later..."
        await callback.message.answer(msg)
