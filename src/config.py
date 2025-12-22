import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

ADMIN_IDS = os.getenv('ADMIN_IDS', '')
BOT_TOKEN = os.getenv('BOT_TOKEN', 'PUT_YOUR_TOKEN_HERE')

@dataclass
class Config:
    bot_token: str = BOT_TOKEN
    admin_ids: set[int] = field(default_factory=set)

    def __post_init__(self):
        # Парсим строку с ADMIN_IDS после инициализации
        if ADMIN_IDS:
            self.admin_ids = set(int(x) for x in ADMIN_IDS.split(',') if x.strip())

cfg = Config()
