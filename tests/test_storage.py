import pytest


@pytest.mark.asyncio
async def test_storage_create_and_save(storage_with_db):
    user = await storage_with_db.create_or_get_user(111)
    assert user.tg_id == 111

    user.name = "Bob"
    user.age = 28
    user.is_active = True
    await storage_with_db.save_user(user)

    loaded = await storage_with_db.get_user_by_tg(111)
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
    user = await storage_with_db.create_or_get_user(300)

    await storage_with_db.add_moderation(user.id, "photo")
    item = await storage_with_db.get_pending_moderation()
    assert item is not None

    await storage_with_db.set_moderation_status(user.id, "approved")
    status = await storage_with_db.get_user_moderation_status(user.id)
    assert status == "approved"
