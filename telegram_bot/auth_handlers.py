import logging

from aiogram import Router, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.filters import Command

from telegram_bot.request_service import (
    get_me,
    register_telegram_user,
    refresh_token as api_refresh_token,
)
from telegram_bot.token_storage import (
    save_user_tokens,
    load_user_tokens,
    remove_user_tokens,
)

logger = logging.getLogger(__name__)
router = Router()


class AuthStates(StatesGroup):
    waiting_for_email = State()
    waiting_for_password = State()


@router.message(Command("login"))
async def login_start(message: types.Message, state: FSMContext):
    telegram_id = message.from_user.id
    await state.update_data(telegram_id=telegram_id)

    saved_tokens = load_user_tokens(telegram_id)

    if saved_tokens and saved_tokens.get("access_token"):
        access_token = saved_tokens.get("access_token")
        user = await get_me(access_token)

        if user:
            await state.update_data(
                access_token=access_token,
                refresh_token=saved_tokens.get("refresh_token"),
                user_id=saved_tokens.get("user_id") or user.get("id"),
            )

            await message.answer(
                f"✅ Automatic login successful! {user.get('email', '')}"
            )
            return

        refresh_token = saved_tokens.get("refresh_token")
        if refresh_token:
            success, result = await api_refresh_token(refresh_token)

            if success:
                new_access_token = result
                user = await get_me(new_access_token)

                if user:
                    user_id = user.get("id") or saved_tokens.get("user_id")
                    save_user_tokens(
                        telegram_id, new_access_token, refresh_token, user_id
                    )

                    await state.update_data(
                        access_token=new_access_token,
                        refresh_token=refresh_token,
                        user_id=user_id,
                    )

                    await message.answer(
                        f"✅ Login successful! {user.get('email', '')}"
                    )
                    return

    await message.answer("Enter email:")
    await state.set_state(AuthStates.waiting_for_email)


@router.message(AuthStates.waiting_for_email)
async def get_email(message: types.Message, state: FSMContext):
    await state.update_data(email=message.text)
    await message.answer("Enter password:")
    await state.set_state(AuthStates.waiting_for_password)


@router.message(AuthStates.waiting_for_password)
async def get_password(message: types.Message, state: FSMContext):
    data = await state.get_data()
    email = data["email"]
    password = message.text
    telegram_id = message.from_user.id
    try:
        success, result = await register_telegram_user(
            email, password, telegram_id
        )

        if success:
            access_token = result["access"]
            refresh_token = result.get("refresh")

            await state.update_data(access_token=access_token)

            if refresh_token:
                await state.update_data(refresh_token=refresh_token)

            await state.set_state(None)

            try:
                user = await get_me(access_token)
                if user and "id" in user:
                    user_id = user["id"]
                    await state.update_data(user_id=user_id)

                    # Save tokens for future use
                    save_user_tokens(
                        telegram_id, access_token, refresh_token, user_id
                    )

                    await message.answer(
                        f"✅ Login successful {user.get('email', '')}"
                    )
                else:
                    await message.answer(
                        "✅ Login successful! (Failed to retrieve user data)"
                    )
            except Exception as e:
                logger.error(f"User info error: {e}")
                await message.answer(
                    "✅ Login successful! (Failed to retrieve user data))"
                )
        else:
            await message.answer(f"❌ {result}")
            await state.clear()
    except Exception as e:
        logger.error(f"Login error: {e}")
        await message.answer("Error connecting to the backend.")
        await state.clear()


@router.message(Command("logout"))
async def logout(message: types.Message, state: FSMContext):
    telegram_id = message.from_user.id
    remove_user_tokens(telegram_id)

    await state.clear()
    await message.answer("You are logged out.")


async def get_valid_access_token(state: FSMContext, message=None):
    """
    Gets a valid access_token, or refreshes it via refresh_token

    Args:
        state: FSM context
        message: Optional message to get telegram_id

    Returns:
        str: Valid access_token or None if missing/cannot be updated
    """
    data = await state.get_data()
    access_token = data.get("access_token")
    refresh_token = data.get("refresh_token")
    user_id = data.get("user_id")
    telegram_id = data.get("telegram_id")

    if not access_token and telegram_id:
        saved_tokens = load_user_tokens(telegram_id)

        if saved_tokens:
            access_token = saved_tokens.get("access_token")
            refresh_token = saved_tokens.get("refresh_token")
            user_id = saved_tokens.get("user_id")

            if access_token:
                await state.update_data(
                    access_token=access_token,
                    refresh_token=refresh_token,
                    user_id=user_id,
                )
                logger.info("Loaded tokens from storage, validating...")

    if not access_token:
        logger.warning("Access token not found in state or storage")
        return None

    try:
        user = await get_me(access_token)
        if user:
            logger.debug("Access token is valid")
            return access_token

        logger.warning("Token validation failed (get_me returned None)")

        if refresh_token:
            logger.info("Trying to refresh access token")
            success, result = await api_refresh_token(refresh_token)

            if success:
                logger.info("Successfully refreshed access token")
                await state.update_data(access_token=result)

                if telegram_id:
                    save_user_tokens(
                        telegram_id, result, refresh_token, user_id
                    )

                return result
            else:
                logger.error(f"Failed to refresh token: {result}")
        else:
            logger.warning("No refresh token available")
    except Exception as e:
        logger.error(f"Token validation error: {e}")

    return access_token
