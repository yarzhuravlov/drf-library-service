import asyncio
from telegram_bot.bot_core import dp, bot

if __name__ == "__main__":
    asyncio.run(dp.start_polling(bot))
