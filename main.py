import asyncio
import logging
import os
from pathlib import Path

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO)

BASE_DIR = Path(__file__).resolve().parent
ENV_FILE = BASE_DIR / ".env"
load_dotenv(ENV_FILE)

TOKEN = os.getenv("BOT_TOKEN")
print(f"✅ Токен загружен: {TOKEN[:10]}...")  # Показываем только первые 10 символов

if not TOKEN or TOKEN == "PUT_YOUR_TOKEN_HERE":
    print("❌ Ошибка: BOT_TOKEN не установлен!")
    exit(1)

# Создаем бота и диспетчер
bot = Bot(
    token=TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)

dp = Dispatcher()


async def main():
    try:
        # Импортируем роутеры внутри функции main, чтобы избежать циклических импортов
        from src.handlers import profile, browse, admin

        # Регистрируем все роутеры
        print("📋 Регистрирую роутеры...")
        dp.include_router(profile.router)
        dp.include_router(browse.router)
        dp.include_router(admin.router)
        print("✅ Роутеры зарегистрированы")

        print("\n🤖 Бот запущен!")
        print("📊 Данные хранятся в SQLite")
        print("👑 Доступна админ-панель: /admin")
        print("👤 Доступные команды для пользователей:")
        print("  /start - Начать работу с ботом")
        print("  /admin - Панель администратора (для админов)")
        print("  /adminhelp - Справка по админ-командам")

        print("\n⏳ Запускаю поллинг...")
        await dp.start_polling(bot)

    except Exception as e:
        print(f"❌ Критическая ошибка при запуске: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Бот остановлен пользователем")
    except Exception as e:
        print(f"\n❌ Неожиданная ошибка: {e}")
        import traceback

        traceback.print_exc()