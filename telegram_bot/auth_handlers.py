import logging
import os

from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.filters import Command
from telegram_bot.config import API_BASE_URL
import requests

from telegram_bot.request_service import get_me

logger = logging.getLogger(__name__)
router = Router()


class AuthStates(StatesGroup):
    waiting_for_email = State()
    waiting_for_password = State()


@router.message(Command("login"))
async def login_start(message: types.Message, state: FSMContext):
    await message.answer("Введіть email:")
    await state.set_state(AuthStates.waiting_for_email)


@router.message(AuthStates.waiting_for_email)
async def get_email(message: types.Message, state: FSMContext):
    await state.update_data(email=message.text)
    await message.answer("Введіть пароль:")
    await state.set_state(AuthStates.waiting_for_password)


@router.message(AuthStates.waiting_for_password)
async def get_password(message: types.Message, state: FSMContext):
    data = await state.get_data()
    email = data["email"]
    password = message.text
    telegram_id = message.from_user.id
    try:
        resp = requests.post(
            f"{API_BASE_URL}bots/register_user/",
            json={
                "email": email,
                "password": password,
                "telegram_id": telegram_id,
            },
            timeout=10,
        )
        response_data = resp.json()
        if (
            resp.status_code == 200
            and "access" in response_data
            and "refresh" in response_data
        ):
            access_token = response_data["access"]
            refresh_token = response_data["refresh"]
            await state.update_data(
                access_token=access_token, refresh_token=refresh_token
            )
            await state.set_state(None)

            user = get_me(access_token)
            await state.update_data(
                user_id=user["id"]
            )

            await message.answer("✅ Успішний вхід!")
        elif resp.status_code == 200 and "access" in response_data:
            access_token = response_data["access"]
            await state.update_data(access_token=access_token)
            await state.set_state(None)
            await message.answer(
                "✅ Успішний вхід! (Refresh token не отримано)"
            )
        else:
            error_message = response_data.get(
                "error", "Невірний email або пароль."
            )
            await message.answer(f"❌ {error_message}")
            await state.clear()
    except Exception as e:
        logger.error(f"Login error: {e}")
        await message.answer("Помилка підключення до бекенду.")
        await state.clear()


@router.message(Command("logout"))
async def logout(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("Ви вийшли з системи.")


async def get_valid_access_token(state: FSMContext):
    """
    Отримує дійсний access_token, при необхідності оновлює його через refresh_token

    Args:
        state: FSM контекст

    Returns:
        str: Валідний access_token або None, якщо його немає чи не можна оновити
    """
    data = await state.get_data()
    access_token = data.get("access_token")
    refresh_token = data.get("refresh_token")

    if not access_token:
        return None

    try:
        resp = requests.get(
            f"{API_BASE_URL}users/me/",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=10,
        )

        if resp.status_code == 200:
            return access_token

        if resp.status_code == 401 and refresh_token:
            try:
                refresh_resp = requests.post(
                    f"{API_BASE_URL}token/refresh/",
                    json={"refresh": refresh_token},
                    timeout=10,
                )

                if refresh_resp.status_code == 200:
                    new_access = refresh_resp.json().get("access")
                    if new_access:
                        await state.update_data(access_token=new_access)
                        return new_access
            except Exception as e:
                logger.error(f"Refresh token error: {e}")

    except Exception as e:
        logger.error(f"Token validation error: {e}")

    return access_token
