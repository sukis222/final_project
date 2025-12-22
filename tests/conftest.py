import asyncio
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.database import sqlite as sqlite_module  # noqa: E402
from src import storage as storage_module  # noqa: E402


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def temp_db(tmp_path):
    db_path = tmp_path / "test.db"
    return sqlite_module.SQLiteDatabase(db_path)


@pytest.fixture
def storage_with_db(monkeypatch, temp_db):
    monkeypatch.setattr(storage_module, "db", temp_db)
    return storage_module.storage


@pytest.fixture
def handlers_storage(monkeypatch, tmp_path):
    db = sqlite_module.SQLiteDatabase(tmp_path / "handlers.db")
    monkeypatch.setattr(storage_module, "db", db)
    current_storage = storage_module.storage

    from src.handlers import browse, profile, moderation  # noqa: E402

    monkeypatch.setattr(browse, "storage", current_storage)
    monkeypatch.setattr(profile, "storage", current_storage)
    monkeypatch.setattr(moderation, "storage", current_storage)
    return current_storage
