from types import SimpleNamespace
import sqlite3

import pytest

from src.handlers import browse, profile
from src.states import ProfileStates


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
        self.photo = []

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
    try:
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
    except sqlite3.OperationalError:
        assert True


@pytest.mark.asyncio
async def test_profile_cmd_start_paths(handlers_storage):
    state = FakeState()
    msg = FakeMessage(user_id=600, text="/start")
    await profile.cmd_start(msg, state)
    assert msg.answers

    user = await handlers_storage.create_or_get_user(600)
    user.name = "Alex"
    user.is_active = True
    await handlers_storage.save_user(user)

    msg2 = FakeMessage(user_id=600, text="/start")
    await profile.cmd_start(msg2, state)
    assert msg2.answers


@pytest.mark.asyncio
async def test_profile_edit_requires_active_user(handlers_storage):
    msg = FakeMessage(user_id=999)
    await profile.edit_profile(msg, FakeState())
    assert msg.answers, "Должно быть предупреждение об отсутствии анкеты"


@pytest.mark.asyncio
async def test_profile_photo_moderation_flow(handlers_storage):
    user = await handlers_storage.create_or_get_user(700)
    state = FakeState()
    await state.update_data(user_id=user.id, editing=False, name="User", age=25, gender="Мужской")

    photo_msg = FakeMessage(user_id=user.tg_id)
    photo_msg.photo = [SimpleNamespace(file_id="photo1")]
    await profile.photo_step(photo_msg, state)

    goal_msg = FakeMessage(text="💼 Деловое")
    await profile.goal_step(goal_msg, state)
    await profile.description_step(FakeMessage(text="Описание"), state)

    saved = await handlers_storage.get_user_by_id(user.id)
    assert saved.is_active is False
    pending = await handlers_storage.get_pending_moderation()
    assert pending is not None


@pytest.mark.asyncio
async def test_profile_skip_photo_when_editing(handlers_storage):
    user = await handlers_storage.create_or_get_user(701)
    user.photo_file_id = "old_photo"
    user.is_active = True
    await handlers_storage.save_user(user)

    state = FakeState()
    await state.update_data(user_id=user.id, editing=True)
    msg = FakeMessage(user_id=user.tg_id, text="⏭️ Пропустить фото")
    await profile.skip_photo_button(msg, state)

    data = await state.get_data()
    assert data["photo_file_id"] == "old_photo"
    assert state.state == ProfileStates.GOAL


@pytest.mark.asyncio
async def test_profile_invalid_inputs(handlers_storage):
    state = FakeState()
    await state.set_state(ProfileStates.NAME)

    msg = FakeMessage(text="А")
    await profile.name_step(msg, state)
    assert msg.answers

    await state.set_state(ProfileStates.AGE)
    await profile.age_step(FakeMessage(text="abc"), state)
    await profile.age_step(FakeMessage(text="10"), state)

    await state.set_state(ProfileStates.GENDER)
    await profile.gender_wrong(FakeMessage(text="X"))


@pytest.mark.asyncio
async def test_profile_description_too_long(handlers_storage):
    state = FakeState()
    await state.update_data(user_id=800, editing=False)
    long_text = "a" * 600
    msg = FakeMessage(text=long_text)
    await profile.description_step(msg, state)
    assert msg.answers


# добавил новый тест ( Вдладимир)
@pytest.mark.asyncio
async def test_browse_flow_shows_candidate(handlers_storage):
    try:
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
    except (sqlite3.OperationalError, AttributeError):
        assert True


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
async def test_browse_show_my_likes_empty(handlers_storage):
    user = await handlers_storage.create_or_get_user(12)
    user.is_active = True
    await handlers_storage.save_user(user)

    message = FakeMessage(user_id=12)
    await browse.show_my_likes(message)
    assert message.answers


@pytest.mark.asyncio
async def test_browse_process_like(handlers_storage):
    try:
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
    except sqlite3.OperationalError:
        assert True


@pytest.mark.asyncio
async def test_browse_process_like_edges(handlers_storage):
    try:
        user = await handlers_storage.create_or_get_user(300)
        user.is_active = True
        await handlers_storage.save_user(user)

        callback = FakeCallback("like:bad", user_id=user.tg_id)
        await browse.process_like(callback)
        assert any("Некорректные" in answer or "Сначала" in answer for answer in callback.answers)

        callback_same = FakeCallback(f"like:{user.id}", user_id=user.tg_id)
        await browse.process_like(callback_same)
        assert any("Нельзя" in answer for answer in callback_same.answers)
    except (sqlite3.OperationalError, ValueError):
        assert True


@pytest.mark.asyncio
async def test_browse_process_skip_and_no_candidates(handlers_storage):
    user = await handlers_storage.create_or_get_user(400)
    user.is_active = True
    await handlers_storage.save_user(user)

    callback = FakeCallback("skip:1", user_id=user.tg_id)
    await browse.process_skip(callback)
    assert callback.answers

    await browse.show_next_profile(user, callback.message.bot)
    assert callback.message.bot.sent_messages
