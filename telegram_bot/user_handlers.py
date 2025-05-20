import logging
from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from telegram_bot.config import API_BASE_URL
from telegram_bot.request_service import (
    get_me,
    get_user_borrowings,
    get_book_details,
)
import httpx

logger = logging.getLogger(__name__)
router = Router()


async def get_book_title(book_id, state: FSMContext):
    """Gets the book title by ID"""
    if not book_id:
        return "Unknown book"

    try:
        data = await state.get_data()
        access_token = data.get("access_token")

        if not access_token:
            return f"Book #{book_id}"

        book = await get_book_details(access_token, book_id)
        if not book:
            return f"Book #{book_id}"

        return book.get("title", f"Book #{book_id}")
    except Exception as e:
        logger.error(f"Error getting book title: {e}")
        return f"Book #{book_id}"


@router.message(Command("profile"))
async def profile(message: types.Message, state: FSMContext):
    data = await state.get_data()
    access_token = data.get("access_token")
    if not access_token:
        await message.answer("❗ First, log in via /login")
        return

    try:
        user = await get_me(access_token)
        if not user:
            await message.answer(
                "❌ Error getting profile. Try to log in via /login"
            )
            return

        user_id = user.get("id")
        if user_id and not data.get("user_id"):
            await state.update_data(user_id=user_id)

        email = user.get("email", "")
        if email == "admin@admin.com":
            verification_status = "✅ Admin"
        else:
            verification_status = (
                "✅ Verified" if user.get("is_verified") else "❌ Not verified"
            )

        first_name = user.get("first_name", "")
        last_name = user.get("last_name", "")
        full_name = f"{first_name} {last_name}".strip()
        if not full_name:
            full_name = "Not specified"

        text = (
            f"👤 <b>USER PROFILE</b>\n\n"
            f"🆔 <b>ID:</b> #{user.get('id', 'Unknown')}\n"
            f"👨‍💼 <b>Name:</b> {full_name}\n"
            f"✉️ <b>Email:</b> {user.get('email', 'Not specified')}\n"
            f"🔐 <b>Status:</b> {verification_status}\n"
        )

        builder = InlineKeyboardBuilder()
        builder.button(text="📋 My Rentals", callback_data="show_borrowings")
        builder.button(text="💳 My Payments", callback_data="show_payments")
        builder.adjust(2)

        await message.answer(text, reply_markup=builder.as_markup())
    except Exception as e:
        logger.error(f"Profile error: {e}")
        await message.answer("❌ Error retrieving profile.")


@router.callback_query(F.data == "show_borrowings")
async def show_borrowings(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    user_id = data.get("user_id")
    access_token = data.get("access_token")

    if not access_token:
        await callback.answer("❗ First, log in via /login")
        return

    if not user_id:
        await callback.message.answer("No user ID. Try to log in via /login")
        return

    try:
        borrowings = await get_user_borrowings(user_id)

        if not borrowings:
            await callback.message.answer("You don't have any active rentals.")
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

        builder.button(
            text="⬅️ Back to Profile", callback_data="back_to_profile"
        )

        builder.adjust(1)

        text = "\n\n".join(borrowing_lines)

        info_text = (
            "ℹ️ <b>Note:</b> To return a book, please visit the library "
            "or contact the administrator. Online return via bot is "
            "currently not available."
        )

        await callback.message.answer(
            f"📋 <b>Your active rentals:</b>\n\n{text}\n\n{info_text}",
            reply_markup=builder.as_markup(),
        )
    except Exception as e:
        logger.error(f"Borrowings error: {e}")
        await callback.message.answer("Error retrieving rentals.")


@router.callback_query(F.data == "back_to_profile")
async def back_to_profile(callback: types.CallbackQuery, state: FSMContext):
    await profile(callback.message, state)


@router.callback_query(F.data == "show_payments")
async def show_payments(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    access_token = data.get("access_token")

    if not access_token:
        await callback.answer("❗ First, log in via /login")
        return

    try:
        async with httpx.AsyncClient() as client:
            try:
                resp = await client.get(
                    f"{API_BASE_URL}payments/payment/",
                    headers={"Authorization": f"Bearer {access_token}"},
                    timeout=10.0,
                )
                resp.raise_for_status()
                payments = resp.json()

                if not payments:
                    await callback.message.answer(
                        "💳 You don't have any payments yet."
                    )
                    return

                def get_status_emoji(status):
                    status_map = {
                        "PENDING": "⏳ Awaiting payment",
                        "PAID": "✅ Paid",
                        "CANCELED": "❌ Canceled",
                        "FAILED": "❌ Payment error",
                    }
                    return status_map.get(status, f"❓ {status}")

                def get_type_emoji(payment_type):
                    type_map = {
                        "PAYMENT": "💵 Rental fee",
                        "FINE": "💸 Late return fine",
                    }
                    return type_map.get(payment_type, f"❓ {payment_type}")

                payment_lines = []
                for p in payments:
                    payment_id = p.get("id", "#")
                    amount = p.get("amount", "0")
                    payment_type = get_type_emoji(p.get("type", "Unknown"))
                    status = get_status_emoji(p.get("status", "Unknown"))

                    payment_text = (
                        f"🧾 <b>Payment #{payment_id}</b>\n"
                        f"   💰 Amount: {amount} UAH\n"
                        f"   📋 Type: {payment_type}\n"
                        f"   🔄 Status: {status}"
                    )
                    payment_lines.append(payment_text)

                text = "\n\n".join(payment_lines)
                await callback.message.answer(
                    f"💳 <b>Your payments:</b>\n\n{text}"
                )
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    logger.warning("Payments endpoint not found")
                    await callback.message.answer(
                        "ℹ️ Payment function is not available"
                    )
                else:
                    logger.error(f"Payments error: {e.response.status_code}")
                    error_code = e.response.status_code
                    error_msg = f"❌ Error retrieving payments: {error_code}"
                    await callback.message.answer(error_msg)
    except Exception as e:
        logger.error(f"Payments error: {e}")
        error_msg = "❌ Server connection error. Please try again later."
        await callback.message.answer(error_msg)
