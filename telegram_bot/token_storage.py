import json
import os
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

TOKENS_FILE = Path(__file__).parent / "user_tokens.json"


def save_user_tokens(telegram_id, access_token, refresh_token, user_id=None):
    """
    Saves user tokens to a file

    Args:
        telegram_id: User's Telegram ID
        access_token: JWT access token
        refresh_token: JWT refresh token
        user_id: User ID in the API (optional)

    Returns:
        bool: True if saving was successful, False otherwise
    """
    try:
        tokens_data = {}

        if os.path.exists(TOKENS_FILE):
            with open(TOKENS_FILE, "r", encoding="utf-8") as f:
                try:
                    tokens_data = json.load(f)
                except json.JSONDecodeError:
                    logger.warning(
                        "Unable to read tokens file, creating a new one"
                    )
                    tokens_data = {}

        tokens_data[str(telegram_id)] = {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "user_id": user_id,
        }

        with open(TOKENS_FILE, "w", encoding="utf-8") as f:
            json.dump(tokens_data, f, indent=4)

        return True

    except Exception as e:
        logger.error(f"Error saving tokens: {e}")
        return False


def load_user_tokens(telegram_id):
    """
    Loads user tokens from file

    Args:
        telegram_id: User's Telegram ID

    Returns:
        dict: User data (access_token, refresh_token, user_id) or None
    """
    if not os.path.exists(TOKENS_FILE):
        return None

    try:
        with open(TOKENS_FILE, "r", encoding="utf-8") as f:
            tokens_data = json.load(f)

        user_data = tokens_data.get(str(telegram_id))
        return user_data

    except Exception as e:
        logger.error(f"Error loading tokens: {e}")
        return None


def remove_user_tokens(telegram_id):
    """
    Removes user tokens from file

    Args:
        telegram_id: User's Telegram ID

    Returns:
        bool: True if deletion was successful, False otherwise
    """
    if not os.path.exists(TOKENS_FILE):
        return True

    try:
        with open(TOKENS_FILE, "r", encoding="utf-8") as f:
            tokens_data = json.load(f)

        if str(telegram_id) in tokens_data:
            del tokens_data[str(telegram_id)]

            with open(TOKENS_FILE, "w", encoding="utf-8") as f:
                json.dump(tokens_data, f, indent=4)

        return True

    except Exception as e:
        logger.error(f"Error removing tokens: {e}")
        return False
