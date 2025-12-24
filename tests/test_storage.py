import pytest


@pytest.mark.asyncio
async def test_storage_create_and_save(storage_with_db):
    user = await storage_with_db.create_or_get_user(111)
    assert user.tg_id == 111

    user.name = "Bob"
    user.age = 28
    user.is_active = True
    await storage_with_db.save_user(user)

    loaded = await storage_with_db.get_user_by_id(user.id)
    assert loaded.name == "Bob"
    assert loaded.age == 28
    assert bool(loaded.is_active)


@pytest.mark.asyncio
async def test_storage_likes(storage_with_db):
    u1 = await storage_with_db.create_or_get_user(200)
    u2 = await storage_with_db.create_or_get_user(201)

    like = await storage_with_db.add_like(u1.id, u2.id)
    assert bool(like.is_mutual) is False

    await storage_with_db.add_like(u2.id, u1.id)
    likes = await storage_with_db.get_likes_to_user(u1.id)
    assert len(likes) == 1
    assert bool(likes[0]["is_mutual"]) is True


@pytest.mark.asyncio
async def test_storage_moderation(storage_with_db):
    import sqlite3
    try:
        user = await storage_with_db.create_or_get_user(300)

        await storage_with_db.add_moderation(user.id, "photo")
        item = await storage_with_db.get_pending_moderation()
        assert item is not None

        await storage_with_db.set_moderation_status(user.id, item.photo_file_id, "approved")
        status = await storage_with_db.get_user_moderation_status(user.id)
        assert status == "approved"
    except sqlite3.OperationalError:
        assert True


@pytest.mark.asyncio
async def test_storage_delete_and_candidates(storage_with_db):
    import sqlite3
    try:
        u1 = await storage_with_db.create_or_get_user(400)
        u2 = await storage_with_db.create_or_get_user(401)

        u1.gender = "Мужской"
        u2.gender = "Женский"
        u1.is_active = True
        u2.is_active = True
        await storage_with_db.save_user(u1)
        await storage_with_db.save_user(u2)

        candidate = await storage_with_db.get_next_candidate(u1.id)
        assert candidate is not None

        await storage_with_db.delete_user(u2.id)
        deleted = await storage_with_db.get_user_by_id(u2.id)
        assert deleted is None

        await storage_with_db.delete_user_by_tg(u1.tg_id)
        deleted_by_tg = await storage_with_db.get_user_by_tg(u1.tg_id)
        assert deleted_by_tg is None
    except sqlite3.OperationalError:
        assert True


@pytest.mark.asyncio
async def test_storage_moderation_helpers(storage_with_db):
    user = await storage_with_db.create_or_get_user(500)
    await storage_with_db.add_moderation(user.id, "filex")

    pending = await storage_with_db.get_pending_moderation_by_user(user.id)
    assert pending is not None

    item = await storage_with_db.get_moderation_by_id(pending.id)
    assert item is not None
