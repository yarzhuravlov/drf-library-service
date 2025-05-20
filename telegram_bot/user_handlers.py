import logging
from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from telegram_bot.config import API_BASE_URL
import requests

logger = logging.getLogger(__name__)
router = Router()


@router.message(Command("profile"))
async def profile(message: types.Message, state: FSMContext):
    data = await state.get_data()
    access_token = data.get("access_token")
    if not access_token:
        await message.answer("/login")
        return
    headers = {"Authorization": f"Bearer {access_token}"}
    try:
        resp = requests.get(
            f"{API_BASE_URL}users/me/", headers=headers, timeout=10
        )
        if resp.status_code == 200:
            u = resp.json()
            text = f"👤 <b>Профіль</b>\nІм'я: {u.get('first_name','')} {u.get('last_name','')}\nEmail: {u.get('email','')}\nПідтверджено: {'✅' if u.get('is_verified') else '❌'}"
            builder = InlineKeyboardBuilder()
            builder.button(text="💰 Баланс", callback_data="show_balance")
            builder.button(text="📋 Оренди", callback_data="show_borrowings")
            builder.button(text="💳 Платежі", callback_data="show_payments")
            builder.adjust(2)
            await message.answer(text, reply_markup=builder.as_markup())
        else:
            await message.answer("Помилка отримання профілю.")
    except Exception as e:
        logger.error(f"Profile error: {e}")
        await message.answer("Помилка підключення до бекенду.")


@router.callback_query(F.data == "show_balance")
async def show_balance(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    access_token = data.get("access_token")
    if not access_token:
        await callback.answer("/login")
        return
    headers = {"Authorization": f"Bearer {access_token}"}
    try:
        resp = requests.get(
            f"{API_BASE_URL}payments/payment/balance/",
            headers=headers,
            timeout=10,
        )
        if resp.status_code == 200:
            balance = resp.json().get("balance", 0)
            await callback.message.answer(f"💰 <b>Баланс:</b> {balance} грн")
        else:
            await callback.message.answer("Помилка отримання балансу.")
    except Exception as e:
        logger.error(f"Balance error: {e}")
        await callback.message.answer("Помилка підключення до бекенду.")


@router.callback_query(F.data == "show_borrowings")
async def show_borrowings(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    access_token = data.get("access_token")
    if not access_token:
        await callback.answer("/login")
        return
    headers = {"Authorization": f"Bearer {access_token}"}
    try:
        resp = requests.get(
            f"{API_BASE_URL}borrowings/", headers=headers, timeout=10
        )
        if resp.status_code == 200:
            borrowings = resp.json()
            if not borrowings:
                await callback.message.answer("Оренд немає.")
                return
            text = "\n".join(
                [
                    f"{b['id']}. {b['book']} {b['borrow_date']} — {b['expected_return_date']}"
                    for b in borrowings
                ]
            )
            await callback.message.answer(f"📋 <b>Оренди:</b>\n{text}")
        else:
            await callback.message.answer("Помилка отримання оренд.")
    except Exception as e:
        logger.error(f"Borrowings error: {e}")
        await callback.message.answer("Помилка підключення до бекенду.")


@router.callback_query(F.data == "show_payments")
async def show_payments(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    access_token = data.get("access_token")
    if not access_token:
        await callback.answer("/login")
        return
    headers = {"Authorization": f"Bearer {access_token}"}
    try:
        resp = requests.get(
            f"{API_BASE_URL}payments/payment/", headers=headers, timeout=10
        )
        if resp.status_code == 200:
            payments = resp.json()
            if not payments:
                await callback.message.answer("Платежів немає.")
                return
            text = "\n".join(
                [
                    f"{p['id']}. {p['amount']} грн — {p['type']} — {p['status']}"
                    for p in payments
                ]
            )
            await callback.message.answer(f"💳 <b>Платежі:</b>\n{text}")
        else:
            await callback.message.answer("Помилка отримання платежів.")
    except Exception as e:
        logger.error(f"Payments error: {e}")
        await callback.message.answer("Помилка підключення до бекенду.")
