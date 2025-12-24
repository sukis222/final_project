import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

ADMIN_IDS = os.getenv('ADMIN_IDS1', 'ADMIN_IDS2')
BOT_TOKEN = os.getenv('BOT_TOKEN', 'PUT_YOUR_TOKEN_HERE')

@dataclass
class Config:
    bot_token: str = BOT_TOKEN
    admin_ids: set[int] = field(default_factory=set)
    # Словарь для хранения режима админа по ID пользователя
    admin_mode: dict[int, bool] = field(default_factory=dict)

    def __post_init__(self):
        # Парсим строку с ADMIN_IDS после инициализации
        if ADMIN_IDS:
            self.admin_ids = set(int(x) for x in ADMIN_IDS.split(',') if x.strip())
        # Инициализируем все админы в обычном режиме
        for admin_id in self.admin_ids:
            self.admin_mode[admin_id] = False

    def is_admin(self, user_id: int) -> bool:
        return user_id in self.admin_ids

    def toggle_admin_mode(self, user_id: int) -> bool:
        if self.is_admin(user_id):
            current_mode = self.admin_mode.get(user_id, False)
            self.admin_mode[user_id] = not current_mode
            return self.admin_mode[user_id]
        return False

    def get_admin_mode(self, user_id: int) -> bool:
        return self.admin_mode.get(user_id, False)

cfg = Config()