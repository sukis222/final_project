import asyncio
import logging
import os
from pathlib import Path

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from dotenv import load_dotenv

from .handlers.browse import router as browse_router
from .handlers.moderation import router as moderation_router
from .handlers.profile import router as profile_router

logging.basicConfig(level=logging.INFO)

BASE_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = BASE_DIR / ".env"
load_dotenv(ENV_FILE)

TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN or TOKEN == "PUT_YOUR_TOKEN_HERE":
    print("❌ Ошибка: BOT_TOKEN не установлен!")
    print("Создайте файл .env с содержимым:")
    print("BOT_TOKEN=ваш_токен_бота")
    print("ADMIN_IDS=ваш_telegram_id")
    print("MONGODB_URL=mongodb://localhost:27017")
    print("MONGODB_DATABASE=dating_bot")
    exit(1)

# Проверяем наличие MongoDB
mongodb_url = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
print(f"📦 Подключение к MongoDB: {mongodb_url}")

# Правильное создание бота для aiogram 3.7+
bot = Bot(
    token=TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)

dp = Dispatcher()

# Регистрируем все роутеры
dp.include_router(profile_router)
dp.include_router(browse_router)
dp.include_router(moderation_router)

async def main():
    print("🤖 Бот запущен!")
    print("📊 Данные хранятся в MongoDB")
    print("Доступные команды:")
    print("/start - Начать работу с ботом")
    print("/moderate - Модерация фото (для админов)")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Бот остановлен")
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        print("Проверьте, запущен ли MongoDB сервер")
