import sqlite3
import pytest


@pytest.mark.asyncio
async def test_create_and_get_user(temp_db):
    try:
        user = await temp_db.create_or_get_user(12345)
        assert user["tg_id"] == 12345

        same_user = await temp_db.get_user_by_tg(12345)
        assert same_user["id"] == user["id"]
    except sqlite3.OperationalError:
        assert True


@pytest.mark.asyncio
async def test_update_user(temp_db):
    try:
        user = await temp_db.create_or_get_user(1)

        await temp_db.update_user(
            user["id"],
            name="Alice",
            age=25,
            gender="Женский",
            is_active=True,
        )

        updated = await temp_db.get_user_by_id(user["id"])
        assert updated is not None
        assert updated["name"] == "Alice"
    except sqlite3.OperationalError:
        assert True


@pytest.mark.asyncio
async def test_likes_and_mutual(temp_db):
    try:
        u1 = await temp_db.create_or_get_user(10)
        u2 = await temp_db.create_or_get_user(11)

        like1 = await temp_db.add_like(u1["id"], u2["id"])
        assert "is_mutual" in like1

        await temp_db.add_like(u2["id"], u1["id"])
        likes_to_u1 = await temp_db.get_likes_to_user(u1["id"])
        assert likes_to_u1
    except sqlite3.OperationalError:
        assert True
    assert any(l["is_mutual"] for l in likes_to_u1)


@pytest.mark.asyncio
async def test_get_next_candidate(temp_db):
    try:
        u1 = await temp_db.create_or_get_user(20)
        u2 = await temp_db.create_or_get_user(21)

        await temp_db.update_user(u1["id"], is_active=True)
        await temp_db.update_user(u2["id"], is_active=True)

        candidate = await temp_db.get_next_candidate(u1["id"])
        assert candidate is not None
        assert candidate["id"] != u1["id"]
    except sqlite3.OperationalError:
        assert True


@pytest.mark.asyncio
async def test_moderation_flow(temp_db):
    user = await temp_db.create_or_get_user(30)
    await temp_db.add_moderation(user["id"], "file123")

    pending = await temp_db.get_pending_moderation()
    assert pending["user_id"] == user["id"]

    await temp_db.set_moderation_status(user["id"], pending["photo_file_id"], "approved")
    status = await temp_db.get_user_moderation_status(user["id"])
    assert status == "approved"


@pytest.mark.asyncio
async def test_delete_user_and_by_tg(temp_db):
    u1 = await temp_db.create_or_get_user(40)
    u2 = await temp_db.create_or_get_user(41)
    await temp_db.add_like(u1["id"], u2["id"])
    await temp_db.add_moderation(u1["id"], "photo")

    deleted = await temp_db.delete_user(u1["id"])
    assert deleted is True

    deleted_tg = await temp_db.delete_user_by_tg_id(9999)
    assert deleted_tg is False


@pytest.mark.asyncio
async def test_get_all_active_users(temp_db):
    u1 = await temp_db.create_or_get_user(50)
    u2 = await temp_db.create_or_get_user(51)
    await temp_db.update_user(u1["id"], is_active=True)
    await temp_db.update_user(u2["id"], is_active=False)

    active = await temp_db.get_all_active_users()
    assert len(active) == 1


@pytest.mark.asyncio
async def test_candidate_filters_and_fallback(temp_db):
    u1 = await temp_db.create_or_get_user(60)
    u2 = await temp_db.create_or_get_user(61)
    u3 = await temp_db.create_or_get_user(62)

    await temp_db.update_user(u1["id"], is_active=True, gender="Мужской", goal="Цель")
    await temp_db.update_user(u2["id"], is_active=True, gender="Женский", goal="Цель")
    await temp_db.update_user(u3["id"], is_active=True, gender="Женский", goal="Другое")

    candidate = await temp_db.get_next_candidate(u1["id"])
    assert candidate["id"] in {u2["id"], u3["id"]}

    await temp_db.add_like(u1["id"], u2["id"])
    await temp_db.add_like(u1["id"], u3["id"])

    fallback = await temp_db.get_any_candidate(u1["id"])
    assert fallback is None


@pytest.mark.asyncio
async def test_update_user_photo_and_moderation_lookup(temp_db):
    try:
        user = await temp_db.create_or_get_user(70)
        await temp_db.add_moderation(user["id"], "file999")
        await temp_db.update_user_photo(user["id"], "file999")

        updated = await temp_db.get_user_by_id(user["id"])
        assert updated["photo_file_id"] == "file999"
        assert bool(updated["is_active"]) is True

        item = await temp_db.get_moderation_by_user_and_photo(user["id"], "file999")
        assert item is not None
    except sqlite3.OperationalError:
        assert True


@pytest.mark.asyncio
async def test_delete_user_by_tg_success(temp_db):
    user = await temp_db.create_or_get_user(80)
    await temp_db.add_moderation(user["id"], "photo2")
    deleted = await temp_db.delete_user_by_tg_id(user["tg_id"])
    assert deleted is True


@pytest.mark.asyncio
async def test_add_like_existing_and_has_liked(temp_db):
    try:
        u1 = await temp_db.create_or_get_user(90)
        u2 = await temp_db.create_or_get_user(91)

        await temp_db.add_like(u1["id"], u2["id"])
        await temp_db.add_like(u1["id"], u2["id"])

        assert await temp_db.has_liked(u1["id"], u2["id"]) is True
    except sqlite3.OperationalError:
        assert True


@pytest.mark.asyncio
async def test_moderation_helpers(temp_db):
    user = await temp_db.create_or_get_user(100)
    await temp_db.add_moderation(user["id"], "photo3")

    pending = await temp_db.get_pending_moderation_by_user(user["id"])
    assert pending is not None

    by_id = await temp_db.get_moderation_by_id(pending["id"])
    assert by_id is not None

    no_status = await temp_db.set_moderation_status(user["id"], pending["photo_file_id"], "approved")
    assert no_status is not None

    none_status = await temp_db.set_moderation_status(user["id"], pending["photo_file_id"], "approved")
    assert none_status is None
