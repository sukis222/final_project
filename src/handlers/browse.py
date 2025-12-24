from aiogram import Router, F, types
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)

from ..storage import storage

router = Router()


def get_main_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🔄 Начать поиск анкет")],
            [KeyboardButton(text="📝 Изменить анкету")],
            [KeyboardButton(text="❤️ Посмотреть мои лайки")],
            [KeyboardButton(text="⏹️ Остановить поиск")],
        ],
        resize_keyboard=True,
    )


def get_browse_kb(target_user_id: int):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="❤️ Лайк",
                    callback_data=f"like:{target_user_id}",
                ),
                InlineKeyboardButton(
                    text="❌ Пропустить",
                    callback_data=f"skip:{target_user_id}",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="⏹️ Остановить поиск",
                    callback_data="stop_search",
                )
            ],
        ]
    )


def get_like_response_kb(from_user_id: int):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="❤️ Взаимно",
                    callback_data=f"like_back:{from_user_id}",
                ),
                InlineKeyboardButton(
                    text="❌ Пропустить",
                    callback_data=f"reject_like:{from_user_id}",
                ),
            ]
        ]
    )

# Отправка анкеты

async def send_profile(user_tg_id: int, target_user, bot):
    caption = (
        f"👤 {target_user.name}, {target_user.age}\n"
        f"⚧️ {target_user.gender}\n"
        f"🎯 {target_user.goal}\n"
    )

    if target_user.description:
        caption += f"\n📝 {target_user.description}"

    kb = get_browse_kb(target_user.id)

    try:
        if target_user.photo_file_id:
            await bot.send_photo(
                user_tg_id,
                target_user.photo_file_id,
                caption=caption,
                reply_markup=kb,
            )
        else:
            await bot.send_message(
                user_tg_id,
                f"📷 Нет фото\n{caption}",
                reply_markup=kb,
            )
    except Exception:
        await bot.send_message(
            user_tg_id,
            caption,
            reply_markup=kb,
        )

# Демонстрация следующей анкеты

async def show_next_profile(user, bot):
    candidate = await storage.get_next_candidate(user.id)

    if not candidate:
        candidate = await storage.get_any_candidate(user.id)

    if not candidate:
        await bot.send_message(
            user.tg_id,
            "Вы просмотрели все анкеты 👀",
            reply_markup=get_main_menu(),
        )
        return

    await send_profile(user.tg_id, candidate, bot)

# Начать поиск

@router.message(F.text == "🔄 Начать поиск анкет")
async def start_browsing(message: types.Message):
    user = await storage.get_user_by_tg(message.from_user.id)

    if not user or not user.is_active:
        await message.answer(
            "У вас нет активной анкеты.\nСоздайте её через /start"
        )
        return

    await show_next_profile(user, message.bot)

# Лайк

@router.callback_query(F.data.startswith("like:"))
async def process_like(callback: types.CallbackQuery):
    user = await storage.get_user_by_tg(callback.from_user.id)
    if not user:
        await callback.answer("Ошибка")
        return

    to_id = int(callback.data.split(":")[1])

    if user.id == to_id:
        await callback.answer("Нельзя лайкнуть себя")
        return

    if await storage.has_liked(user.id, to_id):
        await callback.answer("Вы уже лайкали")
        return

    like = await storage.add_like(user.id, to_id)
    liked_user = await storage.get_user_by_id(to_id)

    if liked_user and like.is_mutual:
        kb_user = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="Написать",
                        url=f"tg://user?id={liked_user.tg_id}",
                    )
                ]
            ]
        )

        kb_other = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="Написать",
                        url=f"tg://user?id={user.tg_id}",
                    )
                ]
            ]
        )

        await callback.message.bot.send_message(
            user.tg_id,
            f"Взаимный лайк с {liked_user.name}!",
            reply_markup=kb_user,
        )

        await callback.message.bot.send_message(
            liked_user.tg_id,
            f"Взаимный лайк с {user.name}!",
            reply_markup=kb_other,
        )

    if liked_user and not like.is_mutual:
        # 🔔 ТОЛЬКО УВЕДОМЛЕНИЕ
        await callback.message.bot.send_message(
            liked_user.tg_id,
            "❤️ Кто-то поставил вам лайк!\n\n"
            "Нажмите «❤️ Посмотреть мои лайки», чтобы увидеть анкеты 👀",
        )

    await callback.answer("❤️ Лайк")
    # await callback.message.delete()

    await show_next_profile(user, callback.message.bot)

# пропуск

@router.callback_query(F.data.startswith("skip:"))
async def process_skip(callback: types.CallbackQuery):
    user = await storage.get_user_by_tg(callback.from_user.id)
    if not user:
        await callback.answer("Сначала создайте анкету")
        return

    try:
        to_id = int(callback.data.split(":")[1])
    except (IndexError, ValueError):
        await callback.answer("Некорректные данные")
        return

    if to_id == user.id:
        await callback.answer("Нельзя пропустить себя")
        return

    await storage.add_skip(user.id, to_id)
    await callback.answer("Пропущено")
    # await callback.message.delete()

    await show_next_profile(user, callback.message.bot)

# мой лайк

@router.message(F.text == "❤️ Посмотреть мои лайки")
async def show_my_likes(message: types.Message):
    user = await storage.get_user_by_tg(message.from_user.id)
    if not user:
        await message.answer("Сначала создайте анкету")
        return

    likes = await storage.get_likes_to_user(user.id)

    if not likes:
        await message.answer("Пока никто не поставил вам лайк ❤️")
        return

    shown = 0

    for item in likes:
        from_user_id = item["from_user_id"]

        # ❗ ЕСЛИ ТЫ УЖЕ ЛАЙКНУЛА В ОТВЕТ — НЕ ПОКАЗЫВАЕМ
        if await storage.has_liked(user.id, from_user_id):
            continue

        liker = await storage.get_user_by_id(from_user_id)
        if not liker:
            continue

        kb = get_like_response_kb(liker.id)

        caption = f"{liker.name}, {liker.age}"

        if liker.photo_file_id:
            await message.answer_photo(
                liker.photo_file_id,
                caption=caption,
                reply_markup=kb,
            )
        else:
            await message.answer(
                caption,
                reply_markup=kb,
            )

        shown += 1

    if shown == 0:
        await message.answer("Нет новых лайков ❤️")


# Взаимный лайк

@router.callback_query(F.data.startswith("like_back:"))
async def like_back(callback: types.CallbackQuery):
    user = await storage.get_user_by_tg(callback.from_user.id)
    to_id = int(callback.data.split(":")[1])

    if await storage.has_liked(user.id, to_id):
        await callback.answer("Вы уже ответили")
        return

    like = await storage.add_like(user.id, to_id)
    other = await storage.get_user_by_id(to_id)

    # await callback.message.delete()

    if like.is_mutual:
        kb_user = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="💬 Написать",
                        url=f"tg://user?id={other.tg_id}",
                    )
                ]
            ]
        )

        kb_other = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="💬 Написать",
                        url=f"tg://user?id={user.tg_id}",
                    )
                ]
            ]
        )

        await callback.message.bot.send_message(
            user.tg_id,
            f"🎉 Взаимный лайк с {other.name}!",
            reply_markup=kb_user,
        )

        await callback.message.bot.send_message(
            other.tg_id,
            f"🎉 Взаимный лайк с {user.name}!",
            reply_markup=kb_other,
        )

    await callback.answer("❤️ Взаимно")

# Отказ от лайка

@router.callback_query(F.data.startswith("reject_like:"))
async def reject_like(callback: types.CallbackQuery):
    # await callback.message.delete()
    await callback.answer("❌ Лайк отклонён")

# Остановить поиск

@router.callback_query(F.data == "stop_search")
async def stop_search_callback(callback: types.CallbackQuery):
    await callback.message.bot.send_message(
        callback.from_user.id,
        "Поиск остановлен.\nНажмите «🔄 Начать поиск анкет»",
        reply_markup=get_main_menu(),
    )
    await callback.answer()


@router.message(F.text == "⏹️ Остановить поиск")
async def stop_search_message(message: types.Message):
    await message.answer(
        "Поиск остановлен.\nНажмите «🔄 Начать поиск анкет»",
        reply_markup=get_main_menu(),
    )
