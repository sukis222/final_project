import asyncio
from types import SimpleNamespace

import pytest

from src.handlers import browse, moderation, profile
from src.states import ProfileStates
from src.config import cfg


class FakeState:
    def __init__(self):
        self.data = {}
        self.state = None
        self.cleared = False

    async def update_data(self, **kwargs):
        self.data.update(kwargs)

    async def set_state(self, value):
        self.state = value

    async def get_data(self):
        return dict(self.data)

    async def clear(self):
        self.cleared = True
        self.data.clear()
        self.state = None


class FakeMessage:
    def __init__(self, user_id=1, text=""):
        self.from_user = SimpleNamespace(id=user_id)
        self.text = text
        self.answers = []
        self.photo_answers = []
        self.bot = DummyBot()

    async def answer(self, text, reply_markup=None):
        self.answers.append(text)

    async def answer_photo(self, photo, caption, reply_markup=None):
        self.photo_answers.append((photo, caption))


class DummyBot:
    def __init__(self):
        self.sent_messages = []
        self.sent_photos = []

    async def send_message(self, chat_id, text, reply_markup=None):
        self.sent_messages.append((chat_id, text))

    async def send_photo(self, chat_id, photo, caption=None, reply_markup=None):
        self.sent_photos.append((chat_id, caption or ""))


class FakeCallback:
    def __init__(self, data, user_id=1):
        self.data = data
        self.from_user = SimpleNamespace(id=user_id)
        self.message = FakeMessage(user_id=user_id)
        self.answers = []

    async def answer(self, text=None):
        self.answers.append(text or "")


@pytest.mark.asyncio
async def test_profile_creation_flow(handlers_storage, monkeypatch):
    fake_state = FakeState()
    create_msg = FakeMessage(user_id=500)

    await profile.start_profile(create_msg, fake_state)
    assert fake_state.data["editing"] is False

    await profile.name_step(FakeMessage(text="Алиса"), fake_state)
    await profile.age_step(FakeMessage(text="23"), fake_state)

    gender_msg = FakeMessage(text="👩 Женский")
    await profile.gender_step(gender_msg, fake_state)

    # имитируем, что фото уже прошло модерацию
    await fake_state.update_data(photo_file_id="file123")
    goal_msg = FakeMessage(text="❤️ Романтическое")
    await profile.goal_step(goal_msg, fake_state)

    desc_msg = FakeMessage(text="Люблю читать")
    await profile.description_step(desc_msg, fake_state)

    stored_user = await handlers_storage.get_user_by_tg(500)
    assert stored_user.name == "Алиса"
    assert stored_user.goal == "❤️ Романтическое"
    assert fake_state.cleared is True


@pytest.mark.asyncio
async def test_profile_edit_requires_active_user(handlers_storage):
    msg = FakeMessage(user_id=999)
    await profile.edit_profile(msg, FakeState())
    assert msg.answers, "Должно быть предупреждение об отсутствии анкеты"

# добавил новый тест ( Вдладимир)
@pytest.mark.asyncio
async def test_browse_flow_shows_candidate(handlers_storage):
    user = await handlers_storage.create_or_get_user(1)
    user.name = "Tester"
    user.gender = "Мужской"
    user.is_active = True
    await handlers_storage.save_user(user)

    candidate = await handlers_storage.create_or_get_user(2)
    candidate.name = "Candidate"
    candidate.age = 30
    candidate.gender = "Женский"
    candidate.goal = "Поиск"
    candidate.is_active = True
    await handlers_storage.save_user(candidate)

    message = FakeMessage(user_id=1)
    await browse.start_browsing_command(message)

    assert message.bot.sent_messages or message.bot.sent_photos


@pytest.mark.asyncio
async def test_browse_show_my_likes(handlers_storage):
    user = await handlers_storage.create_or_get_user(10)
    user.is_active = True
    await handlers_storage.save_user(user)

    liker = await handlers_storage.create_or_get_user(11)
    liker.is_active = True
    await handlers_storage.save_user(liker)

    await handlers_storage.add_like(liker.id, user.id)

    message = FakeMessage(user_id=10)
    await browse.show_my_likes(message)
    assert message.answers or message.photo_answers


@pytest.mark.asyncio
async def test_moderation_command_and_callback(handlers_storage, monkeypatch):
    cfg.admin_ids = {42}

    mod_user = await handlers_storage.create_or_get_user(100)
    await handlers_storage.add_moderation(mod_user.id, "photo")

    class FakeMsg(FakeMessage):
        def __init__(self):
            super().__init__(user_id=42)

    message = FakeMsg()
    await moderation.cmd_moderate(message)
    assert message.photo_answers or message.answers

    callback = FakeCallback("mod:approve:1", user_id=42)
    callback.message.bot = DummyBot()

    await moderation.cb_mod(callback)
    assert callback.answers


@pytest.mark.asyncio
async def test_browse_process_like(handlers_storage, monkeypatch):
    user = await handlers_storage.create_or_get_user(200)
    user.is_active = True
    await handlers_storage.save_user(user)

    target = await handlers_storage.create_or_get_user(201)
    target.is_active = True
    await handlers_storage.save_user(target)

    callback = FakeCallback(f"like:{target.id}", user_id=user.tg_id)
    callback.message.bot = DummyBot()

    await browse.process_like(callback)
    assert callback.answers[-1] is not None
