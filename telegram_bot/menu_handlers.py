import logging
from aiogram import Router, F, types
from aiogram.filters import Command, CommandStart
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from aiogram.fsm.context import FSMContext
from telegram_bot.auth_handlers import get_valid_access_token
from telegram_bot.request_service import get_user_borrowings
from telegram_bot.user_handlers import get_book_title

logger = logging.getLogger(__name__)
router = Router()


@router.message(CommandStart())
async def command_start(message: types.Message):
    welcome_text = (
        f"👋 Greetings, {message.from_user.first_name}!\n\n"
        f"I am a library bot. Features:\n"
        f"📚 Books | 📋 Rentals | 👤 Profile | ℹ️ Help"
    )
    builder = ReplyKeyboardBuilder()
    builder.button(text="📚 Books")
    builder.button(text="📋 My Rentals")
    builder.button(text="👤 Profile")
    builder.button(text="ℹ️ Help")
    builder.adjust(2)
    await message.answer(
        welcome_text, reply_markup=builder.as_markup(resize_keyboard=True)
    )


@router.message(Command("help"))
async def command_help(message: types.Message):
    help_text = (
        "📋 <b>Commands:</b>\n"
        "/start — Main Menu\n"
        "/login — Login\n"
        "/logout — Logout\n"
        "/books — Books\n"
        "/my_borrowings — Rentals\n"
        "/profile — Profile\n"
        "/help — Help\n"
        "\nUse the buttons to navigate"
    )
    await message.answer(help_text)


@router.message(F.text == "📚 Books")
async def books_button(message: types.Message, state: FSMContext):
    access_token = await get_valid_access_token(state)
    if not access_token:
        await message.answer("❗ First, log in via /login")
        return

    from telegram_bot.book_handlers import list_books

    await list_books(message, state)


@router.message(F.text == "📋 My Rentals")
async def borrowings_button(message: types.Message, state: FSMContext):
    try:
        data = await state.get_data()
        user_id = data.get("user_id")

        if not user_id:
            await message.answer("❗ First, log in via /login")
            return

        borrowings = await get_user_borrowings(user_id)

        if not borrowings:
            await message.answer("You don't have any active rentals.")
            return

        borrowing_lines = []

        for b in borrowings:
            book_title = await get_book_title(b.get("book"), state)
            borrowing_text = (
                f"📖 <b>{book_title}</b>\n"
                f"   🆔 #{b['id']}\n"
                f"   📅 Borrowed: {b.get('borrow_date', 'No date')}\n"
                f"   🔄 Return by: {b.get('expected_return', 'Not specified')}"
            )
            borrowing_lines.append(borrowing_text)

        text = "\n\n".join(borrowing_lines)
        await message.answer(f"📋 <b>Your active rentals:</b>\n\n{text}")
    except Exception as e:
        logger.error(f"Borrowings error: {e}")
        await message.answer(
            "❌ Server connection error. Please try again later."
        )


@router.message(F.text == "👤 Profile")
async def profile_button(message: types.Message, state: FSMContext):
    access_token = await get_valid_access_token(state)
    if not access_token:
        await message.answer("❗ First, log in via /login")
        return

    from telegram_bot.user_handlers import profile

    await profile(message, state)


@router.message(F.text == "ℹ️ Help")
async def help_button(message: types.Message):
    await command_help(message)


@router.message()
async def unknown_message(message: types.Message):
    await message.answer(
        "I don't understand this command. Use the menu or /help."
    )
