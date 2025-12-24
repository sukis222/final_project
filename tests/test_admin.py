from types import SimpleNamespace

import pytest

from src.handlers import admin
from src.config import cfg


class DummyMessage:
    def __init__(self, user_id=1, text=""):
        self.from_user = SimpleNamespace(id=user_id)
        self.text = text
        self.answers = []
        self.photo_answers = []

    async def answer(self, text, reply_markup=None):
        self.answers.append(text)

    async def answer_photo(self, photo, caption, reply_markup=None):
        self.photo_answers.append((photo, caption))

    async def edit_reply_markup(self, reply_markup=None):
        return None


class DummyCallback:
    def __init__(self, data, user_id=1):
        self.data = data
        self.from_user = SimpleNamespace(id=user_id)
        self.message = DummyMessage(user_id=user_id)
        self.answers = []

    async def answer(self, text=None):
        self.answers.append(text or "")


class DummyConnection:
    def __init__(self):
        self.row_factory = None
        self._cursor = self

    def cursor(self):
        return self

    def execute(self, *args, **kwargs):
        pass

    def fetchone(self):
        return (0,)

    def fetchall(self):
        return []

    def commit(self):
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


class FakeStorage:
    def __init__(self):
        self._users = {}
        self._pending = SimpleNamespace(
            id=1,
            user_id=1,
            photo_file_id="photo123",
            status="pending",
            created_at="now"
        )

    async def get_pending_moderation(self):
        return self._pending

    async def get_user_by_id(self, user_id):
        return SimpleNamespace(
            id=user_id,
            tg_id=user_id,
            name="User",
            age=20,
            gender="Мужской",
            goal="Цель",
            description="Desc",
            is_active=True,
            photo_file_id="photo123"
        )

    async def get_user_by_tg(self, tg_id):
        return SimpleNamespace(
            id=tg_id,
            tg_id=tg_id,
            name="Viewer",
            age=20,
            gender="Женский",
            goal="Цель",
            description="Desc",
            is_active=True,
            photo_file_id="photo123"
        )

    async def delete_user_by_tg(self, tg_id):
        return True

    async def set_moderation_status(self, user_id, file_id, status):
        return SimpleNamespace(
            id=1,
            user_id=user_id,
            photo_file_id=file_id,
            status=status,
            created_at="now"
        )

    async def update_user_photo(self, user_id, photo_file_id):
        return None

    async def save_user(self, user):
        self._users[user.tg_id] = user

    async def delete_user(self, user_id):
        return True


@pytest.mark.asyncio
async def test_admin_stats_and_users(monkeypatch):
    cfg.admin_ids = {2}
    cfg.admin_mode = {2: True}
    monkeypatch.setattr(admin, "sqlite3", SimpleNamespace(connect=lambda _path: DummyConnection()))
    msg = DummyMessage(user_id=2)

    await admin.admin_stats(msg)
    assert isinstance(msg.answers, list)

    await admin.admin_users_management(msg)
    assert isinstance(msg.answers, list)

@pytest.mark.asyncio
async def test_admin_view_and_delete_user(monkeypatch):
    cfg.admin_ids = {6}
    cfg.admin_mode = {6: True}
    fake_storage = FakeStorage()
    monkeypatch.setattr(admin, "storage", fake_storage)
    msg_view = DummyMessage(user_id=6, text="/viewuser 123")
    await admin.cmd_viewuser(msg_view)
    assert isinstance(msg_view.answers, list)

    msg_delete = DummyMessage(user_id=6, text="/deleteuser 123")
    await admin.cmd_deleteuser(msg_delete)
    assert isinstance(msg_delete.answers, list)


@pytest.mark.asyncio
async def test_admin_quick_delete(monkeypatch):
    cfg.admin_ids = {7}
    cfg.admin_mode = {7: True}
    fake_storage = FakeStorage()
    monkeypatch.setattr(admin, "storage", fake_storage)

    callback = DummyCallback("admin:quick_delete:1", user_id=7)
    await admin.admin_quick_delete(callback)
    assert isinstance(callback.answers, list)
