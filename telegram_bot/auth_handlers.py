from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import requests
import logging

logger = logging.getLogger(__name__)
router = Router()


class AuthStates(StatesGroup):
    waiting_for_email = State()
    waiting_for_password = State()


@router.message(F.text == "/login")
async def login_start(message: types.Message, state: FSMContext):
    await message.answer("Enter your email:")
    await state.set_state(AuthStates.waiting_for_email)


@router.message(AuthStates.waiting_for_email)
async def get_email(message: types.Message, state: FSMContext):
    await state.update_data(email=message.text)
    await message.answer("Enter your password:")
    await state.set_state(AuthStates.waiting_for_password)


@router.message(AuthStates.waiting_for_password)
async def get_password(message: types.Message, state: FSMContext):
    data = await state.get_data()
    email = data["email"]
    password = message.text
    telegram_id = message.from_user.id

    try:
        resp = requests.post(
            "http://localhost:8000/api/v1/bots/register_user/",
            json={
                "email": email,
                "password": password,
                "telegram_id": telegram_id,
            },
            timeout=10,
        )
        if resp.content:
            try:
                resp_json = resp.json()
                if isinstance(resp_json, dict):
                    if resp.status_code == 200 and "access" in resp_json:
                        access_token = resp_json["access"]
                        await state.update_data(access_token=access_token)
                        await message.answer(
                            "You are successfully authenticated via Telegram!"
                        )
                        await state.set_state(None)
                    else:
                        error_msg = resp_json.get(
                            "error", "Invalid email or password"
                        )
                        await message.answer(f"Error: {error_msg}")
                        await state.clear()
                else:
                    logger.error(
                        f"Response from server is not dictionary: {resp_json}"
                    )
                    await message.answer(
                        "Error: Unexpected response from server."
                    )
                    await state.clear()
            except requests.exceptions.JSONDecodeError:
                logger.error(f"Response from server is not JSON: {resp.text}")
                await message.answer("Error: Server returned non-JSON.")
                await state.clear()
        else:
            logger.error("Server returned empty response")
            await message.answer("Error: Server returned empty response.")
            await state.clear()
    except requests.exceptions.RequestException as e:
        logger.error(f"Error connecting to backend: {e}")
        await message.answer(f"Error connecting to backend: {e}")
        await state.clear()
    except Exception as e:
        logger.error(f"Unexpected error in get_password: {e}", exc_info=True)
        await message.answer("Unexpected error. Try again later.")
        await state.clear()


@router.message(F.text == "/my_borrowings")
async def my_borrowings(message: types.Message, state: FSMContext):
    data = await state.get_data()
    access_token = data.get("access_token")
    if not access_token:
        await message.answer("Please login first via /login")
        return
    headers = {"Authorization": f"Bearer {access_token}"}
    try:
        resp = requests.get(
            "http://localhost:8000/api/v1/borrowings/",
            headers=headers,
            timeout=10,
        )
        if resp.status_code == 200:
            borrowings_data = resp.json()
            if not borrowings_data:
                await message.answer("You have no active borrowings.")
            else:
                text_parts = ["Your borrowings:"]
                for b in borrowings_data:
                    if not isinstance(b, dict):
                        logger.warning(
                            f"Skipped borrowing item (not a dictionary): {b}"
                        )
                        continue
                    book_id = b.get("book")
                    borrow_date = b.get("borrow_date")
                    expected_return_date = b.get("expected_return_date")
                    text_parts.append(
                        f"\n📚 Book ID: {book_id} | "
                        f"{borrow_date} — {expected_return_date}"
                    )
                if len(text_parts) > 1:
                    await message.answer("".join(text_parts))
                else:
                    await message.answer("Failed to process borrowing data.")
        elif resp.status_code == 401:
            await message.answer(
                "Token invalid or session expired. " "Please login via /login"
            )
            await state.clear()
        else:
            if resp.content:
                try:
                    resp_json = resp.json()
                    error_detail = resp_json.get("detail", "unknown")
                    await message.answer(f"Error: {error_detail}")
                except requests.exceptions.JSONDecodeError:
                    await message.answer(
                        f"Error: Server returned non-JSON: {resp.text}"
                    )
            else:
                await message.answer("Error: Server returned empty response.")
    except requests.exceptions.RequestException as e:
        logger.error(f"Error connecting to backend in my_borrowings: {e}")
        await message.answer(f"Error connecting to backend: {e}")
    except Exception as e:
        logger.error(f"Unexpected error in my_borrowings: {e}", exc_info=True)
        await message.answer("Unexpected error. Try again later.")
