import pytest


@pytest.mark.asyncio
async def test_create_and_get_user(temp_db):
    user = await temp_db.create_or_get_user(12345)
    assert user["tg_id"] == 12345

    same_user = await temp_db.get_user_by_tg(12345)
    assert same_user["id"] == user["id"]


@pytest.mark.asyncio
async def test_update_user(temp_db):
    user = await temp_db.create_or_get_user(1)

    await temp_db.update_user(
        user["id"],
        name="Alice",
        age=25,
        gender="Женский",
        is_active=True,
    )

    updated = await temp_db.get_user_by_id(user["id"])
    assert updated["name"] == "Alice"
    assert updated["age"] == 25
    assert bool(updated["is_active"]) is True


@pytest.mark.asyncio
async def test_likes_and_mutual(temp_db):
    u1 = await temp_db.create_or_get_user(10)
    u2 = await temp_db.create_or_get_user(11)

    like1 = await temp_db.add_like(u1["id"], u2["id"])
    assert bool(like1["is_mutual"]) is False

    like2 = await temp_db.add_like(u2["id"], u1["id"])
    assert bool(like2["is_mutual"]) is True


@pytest.mark.asyncio
async def test_get_next_candidate(temp_db):
    u1 = await temp_db.create_or_get_user(20)
    u2 = await temp_db.create_or_get_user(21)

    await temp_db.update_user(u1["id"], is_active=True)
    await temp_db.update_user(u2["id"], is_active=True)

    candidate = await temp_db.get_next_candidate(u1["id"])
    assert candidate["id"] == u2["id"]


@pytest.mark.asyncio
async def test_moderation_flow(temp_db):
    user = await temp_db.create_or_get_user(30)
    await temp_db.add_moderation(user["id"], "file123")

    pending = await temp_db.get_pending_moderation()
    assert pending["user_id"] == user["id"]

    await temp_db.set_moderation_status(user["id"], "approved")
    status = await temp_db.get_user_moderation_status(user["id"])
    assert status == "approved"
