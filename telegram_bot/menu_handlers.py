import logging
from aiogram import Router, F, types
from aiogram.filters import Command, CommandStart
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from telegram_bot.auth_handlers import get_valid_access_token
from telegram_bot.request_service import get_user_borrowings
from telegram_bot.user_handlers import get_book_title, profile
from telegram_bot.token_storage import load_user_tokens

logger = logging.getLogger(__name__)
router = Router()


@router.message(CommandStart())
async def command_start(message: types.Message, state: FSMContext):
    telegram_id = message.from_user.id
    await state.update_data(telegram_id=telegram_id)

    data = await state.get_data()
    access_token = data.get("access_token")

    if not access_token:
        saved_tokens = load_user_tokens(telegram_id)

        if saved_tokens and saved_tokens.get("access_token"):
            from telegram_bot.auth_handlers import login_start

            await login_start(message, state)
        else:
            welcome_text = (
                f"👋 Welcome, {message.from_user.first_name}!\n\n"
                f"To use all bot features, please login /login"
            )
            await message.answer(welcome_text)

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


@router.callback_query(F.data == "auto_login")
async def auto_login(callback: types.CallbackQuery, state: FSMContext):
    from telegram_bot.auth_handlers import login_start

    await login_start(callback.message, state)

    await command_start(callback.message, state)


@router.callback_query(F.data == "new_login")
async def new_login(callback: types.CallbackQuery, state: FSMContext):
    from telegram_bot.auth_handlers import login_start  # noqa: F401

    await state.clear()
    await callback.message.answer("Enter email:")
    await state.set_state("AuthStates:waiting_for_email")


@router.message(Command("help"))
async def command_help(message: types.Message, state: FSMContext):
    telegram_id = message.from_user.id
    await state.update_data(telegram_id=telegram_id)

    help_text = (
        "📋 <b>Commands:</b>\n"
        "/start — Main Menu\n"
        "/login — Login\n"
        "/logout — Logout\n"
        "/books — Books\n"
        "/profile — Profile\n"
        "/help — Help\n"
        "\nUse the buttons to navigate"
    )
    await message.answer(help_text)


@router.message(F.text == "📚 Books")
async def books_button(message: types.Message, state: FSMContext):
    telegram_id = message.from_user.id
    await state.update_data(telegram_id=telegram_id)

    access_token = await get_valid_access_token(state)
    if not access_token:
        await message.answer("❗ First, log in via /login")
        return

    from telegram_bot.book_handlers import list_books

    await list_books(message, state)


@router.message(F.text == "📋 My Rentals")
async def borrowings_button(message: types.Message, state: FSMContext):
    telegram_id = message.from_user.id
    await state.update_data(telegram_id=telegram_id)

    try:
        data = await state.get_data()
        user_id = data.get("user_id")
        access_token = data.get("access_token")

        if not access_token:
            access_token = await get_valid_access_token(state)
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

        builder = InlineKeyboardBuilder()

        for b in borrowings:
            book_title = await get_book_title(b.get("book"), state)
            borrowing_text = (
                f"📖 <b>{book_title}</b>\n"
                f"   🆔 #{b['id']}\n"
                f"   📅 Borrowed: {b.get('borrow_date', 'No date')}\n"
                f"   🔄 Return by: {b.get('expected_return', 'Not specified')}"
            )
            borrowing_lines.append(borrowing_text)

        builder.adjust(1)

        text = "\n\n".join(borrowing_lines)

        info_text = (
            "ℹ️ <b>Note:</b> To return a book, please visit the library "
            "or contact the administrator."
        )

        await message.answer(
            f"📋 <b>Your active rentals:</b>\n\n{text}\n\n{info_text}",
            reply_markup=builder.as_markup(),
        )
    except Exception as e:
        logger.error(f"Borrowings error: {e}")
        await message.answer(
            "❌ Server connection error. Please try again later."
        )


@router.message(F.text == "👤 Profile")
async def profile_button(message: types.Message, state: FSMContext):
    telegram_id = message.from_user.id
    await state.update_data(telegram_id=telegram_id)

    access_token = await get_valid_access_token(state)
    if not access_token:
        await message.answer("❗ First, log in via /login")
        return

    await profile(message, state)


@router.message(F.text == "ℹ️ Help")
async def help_button(message: types.Message, state: FSMContext):
    telegram_id = message.from_user.id
    await state.update_data(telegram_id=telegram_id)

    await command_help(message)


@router.message()
async def unknown_message(message: types.Message):
    await message.answer(
        "I don't understand this command. Use the menu or /help."
    )
