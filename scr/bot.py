import asyncio
import os
import yaml
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types, Router, html
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import CommandStart, Command

#  Load environment variables (.env)
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN is not set in .env file")

#  Load YAML config
with open("config.yaml", "r") as f:
    config = yaml.safe_load(f)

MESSAGES = config["messages"]

#  Initialize bot & dispatcher
bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode="HTML")
)
dp = Dispatcher()
router = Router()
dp.include_router(router)

#  Handlers
@router.message(CommandStart())
async def start_handler(message: types.Message):
    text = MESSAGES["start"].format(user=html.bold(message.from_user.full_name))
    await message.answer(text)


@router.message(Command("help"))
async def help_handler(message: types.Message):
    await message.answer(MESSAGES["help"])


# 🔹 Unknown commands (ex: /abc)
@router.message(lambda msg: msg.text.startswith("/") and " " not in msg.text)
async def unknown_command(message: types.Message):
    await message.answer(MESSAGES["unknown_command"])


# 🔹 Default message handler
@router.message()
async def text_handler(message: types.Message):
    await message.answer(MESSAGES["processing"])
    await asyncio.sleep(1)

    await message.answer(
        "Demo mode: music search not implemented yet 🎵\n"
        "But your message was:\n\n"
        f"<i>{html.quote(message.text)}</i>"
    )

#  Run bot
async def main():
    print("Bot is running...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
