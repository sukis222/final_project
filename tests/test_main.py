import pytest

import src.main as main_module


@pytest.mark.asyncio
async def test_main_starts_polling(monkeypatch):
    called = {}

    async def fake_polling(bot):
        called["bot"] = bot

    monkeypatch.setattr(main_module.dp, "start_polling", fake_polling)
    monkeypatch.setattr(main_module, "bot", object())

    await main_module.main()
    assert "bot" in called
