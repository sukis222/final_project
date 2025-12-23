import asyncio
from src.main import main, dp
# main.py
from src.handlers import admin

# И регистрируете роутер
dp.include_router(admin.router)

if __name__ == "__main__":
    asyncio.run(main())
