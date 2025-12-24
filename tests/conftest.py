import asyncio
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import sqlite3

from src.database import sqlite as sqlite_module  # noqa: E402
from src import storage as storage_module  # noqa: E402


def ensure_tables(db_path):
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tg_id INTEGER UNIQUE NOT NULL,
                name TEXT NOT NULL DEFAULT '',
                age INTEGER,
                gender TEXT,
                photo_file_id TEXT,
                goal TEXT,
                description TEXT,
                is_active BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS likes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                from_user_id INTEGER NOT NULL,
                to_user_id INTEGER NOT NULL,
                is_mutual BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (from_user_id) REFERENCES users (id),
                FOREIGN KEY (to_user_id) REFERENCES users (id),
                UNIQUE(from_user_id, to_user_id)
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS moderation (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                photo_file_id TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id),
                UNIQUE(user_id, photo_file_id)
            )
        ''')
        conn.commit()


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def temp_db(tmp_path):
    db_path = tmp_path / "test.db"
    db = sqlite_module.SQLiteDatabase(db_path)
    ensure_tables(db.db_path)
    return db


@pytest.fixture
def storage_with_db(monkeypatch, temp_db):
    monkeypatch.setattr(storage_module, "db", temp_db)
    return storage_module.storage


@pytest.fixture
def handlers_storage(monkeypatch, tmp_path):
    db = sqlite_module.SQLiteDatabase(tmp_path / "handlers.db")
    ensure_tables(db.db_path)
    monkeypatch.setattr(storage_module, "db", db)
    current_storage = storage_module.storage

    from src.handlers import browse, profile, admin  # noqa: E402

    monkeypatch.setattr(browse, "storage", current_storage)
    monkeypatch.setattr(profile, "storage", current_storage)
    monkeypatch.setattr(admin, "storage", current_storage)
    return current_storage
