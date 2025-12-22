from aiogram import F, Router, types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup

from ..storage import storage

router = Router()


async def send_profile_chat(user_obj: types.User, target_user, bot):
    """Отправка анкеты для просмотра"""
    caption = (
        f"👤 {target_user.name}, {target_user.age}\n"
        f"⚧️ {target_user.gender}\n"
        f"🎯 {target_user.goal}\n"
    )

    if target_user.description:
        caption += f"\n📝 {target_user.description}"

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text='❤️ Лайк', callback_data=f'like:{target_user.id}'),
            InlineKeyboardButton(text='❌ Пропустить', callback_data=f'skip:{target_user.id}')
        ],
        [InlineKeyboardButton(text='⏹️ Остановить поиск', callback_data='stop_search')]
    ])

    if target_user.photo_file_id:
        await bot.send_photo(user_obj.id, target_user.photo_file_id, caption=caption, reply_markup=kb)
    else:
        await bot.send_message(user_obj.id, f"📷 Нет фото\n{caption}", reply_markup=kb)


def get_main_menu():
    """Главное меню после создания анкеты"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🔄 Начать поиск анкет")],
            [KeyboardButton(text="📝 Изменить анкету")],
            [KeyboardButton(text="❤️ Посмотреть мои лайки")],
            [KeyboardButton(text="⏹️ Остановить поиск")]
        ],
        resize_keyboard=True
    )


@router.message(F.text == "🔄 Начать поиск анкет")
async def start_browsing_command(message: types.Message):
    user = await storage.get_user_by_tg(message.from_user.id)

    if not user or not user.is_active:
        await message.answer(
            'У вас нет активной анкеты.\n'
            'Создайте её: /start -> 📌 Создать анкету'
        )
        return

    candidate = await storage.get_next_candidate(user.id)

    if not candidate:
        await message.answer(
            'На данный момент нет новых анкет для просмотра 👀\n\n'
            'Попробуйте позже или измените параметры поиска.',
            reply_markup=get_main_menu()
        )
        return

    await send_profile_chat(message.from_user, candidate, message.bot)


@router.message(F.text == "❤️ Посмотреть мои лайки")
async def show_my_likes(message: types.Message):
    user = await storage.get_user_by_tg(message.from_user.id)

    if not user:
        await message.answer('Сначала создайте анкету: /start')
        return

    # Получаем список тех, кто лайкнул текущего пользователя
    likes_to_me = await storage.get_likes_to_user(user.id)

    if not likes_to_me:
        await message.answer('Пока никто не поставил вам лайк ❤️')
        return

    await message.answer(f"❤️ Вас лайкнули {len(likes_to_me)} человек:")

    for like_data in likes_to_me:
        liker_name = like_data.get('from_user_name', 'Неизвестный')
        liker_age = like_data.get('from_user_age', '')
        is_mutual = like_data.get('is_mutual', False)

        # Получаем полную информацию о пользователе для фото
        liker = await storage.get_user_by_id(like_data['from_user_id'])

        if liker:
            mutual_text = " (взаимный ❤️)" if is_mutual else ""

            # Проверяем, лайкали ли мы уже этого пользователя в ответ
            has_liked_back = await storage.has_liked(user.id, liker.id)

            # Создаем клавиатуру с кнопками только если еще не лайкали в ответ
            if not has_liked_back and not is_mutual:
                like_kb = InlineKeyboardMarkup(inline_keyboard=[
                    [
                        InlineKeyboardButton(text='❤️ Лайкнуть в ответ', callback_data=f'like_back:{liker.id}'),
                        InlineKeyboardButton(text='❌ Пропустить', callback_data=f'skip_like:{liker.id}')
                    ]
                ])
            else:
                like_kb = None

            if liker.photo_file_id:
                await message.answer_photo(
                    photo=liker.photo_file_id,
                    caption=f"{liker_name}, {liker_age}{mutual_text}",
                    reply_markup=like_kb
                )
            else:
                await message.answer(
                    f"{liker_name}, {liker_age}{mutual_text}",
                    reply_markup=like_kb
                )


@router.callback_query(F.data.startswith('like:'))
async def process_like(callback: types.CallbackQuery):
    user = await storage.get_user_by_tg(callback.from_user.id)
    if not user:
        await callback.answer('Сначала создайте анкету: /start')
        return

    to_id = callback.data.split(':', 1)[1]

    if to_id == user.id:
        await callback.answer('Нельзя лайкнуть себя.')
        return

    has_liked = await storage.has_liked(user.id, to_id)
    if has_liked:
        await callback.answer('Вы уже лайкали этого пользователя.')
        return

    like = await storage.add_like(user.id, to_id)

    # ОТПРАВЛЯЕМ УВЕДОМЛЕНИЕ ТОМУ, КОГО ЛАЙКНУЛИ
    liked_user = await storage.get_user_by_id(to_id)
    if liked_user:
        # Получаем информацию о том, кто лайкнул
        liker = await storage.get_user_by_id(user.id)

        # Клавиатура для просмотра лайков
        view_likes_kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text='❤️ Посмотреть лайки', callback_data='view_likes')]
        ])

        # Отправляем уведомление тому, кого лайкнули
        await callback.message.bot.send_message(
            liked_user.tg_id,
            f'❤️ Вам поставил лайк {liker.name}!\n'
            f'Если он вам тоже понравится - будет взаимность!',
            reply_markup=view_likes_kb
        )

    # Проверка на взаимный лайк
    if like.is_mutual:
        u_from = await storage.get_user_by_id(user.id)
        u_to = await storage.get_user_by_id(to_id)

        # Сообщение о взаимном лайке (ПОСЛЕДНЕЕ сообщение)
        await callback.message.bot.send_message(
            u_from.tg_id,
            f'🎉 У вас совпадение с {u_to.name}!'
        )
        await callback.message.bot.send_message(
            u_to.tg_id,
            f'🎉 У вас совпадение с {u_from.name}!'
        )

        # Кнопки для начала диалога (ПРЕДПОСЛЕДНЕЕ сообщение)
        kb1 = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text='💬 Начать диалог', url=f'tg://user?id={u_to.tg_id}')]
        ])
        kb2 = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text='💬 Начать диалог', url=f'tg://user?id={u_from.tg_id}')]
        ])

        await callback.message.bot.send_message(u_from.tg_id, 'Начните общение:', reply_markup=kb1)
        await callback.message.bot.send_message(u_to.tg_id, 'Начните общение:', reply_markup=kb2)

    await callback.answer('Лайк сохранён ❤️')

    # Удаляем текущее сообщение (только свою анкету)
    try:
        await callback.message.delete()
    except:
        pass

    # Показываем следующую анкету (автоматически после лайка)
    await show_next_profile(user, callback.message.bot)


@router.callback_query(F.data == 'view_likes')
async def view_likes_callback(callback: types.CallbackQuery):
    user = await storage.get_user_by_tg(callback.from_user.id)

    if not user:
        await callback.answer('Сначала создайте анкету: /start')
        return

    # Получаем список тех, кто лайкнул текущего пользователя
    likes_to_me = await storage.get_likes_to_user(user.id)

    if not likes_to_me:
        await callback.answer('Пока никто не поставил вам лайк')
        await callback.message.answer('Пока никто не поставил вам лайк ❤️')
        return

    await callback.answer('Показываю ваши лайки')

    await callback.message.answer(f"❤️ Вас лайкнули {len(likes_to_me)} человек:")

    for like_data in likes_to_me:
        liker_name = like_data.get('from_user_name', 'Неизвестный')
        liker_age = like_data.get('from_user_age', '')
        is_mutual = like_data.get('is_mutual', False)

        # Получаем полную информацию о пользователе
        liker = await storage.get_user_by_id(like_data['from_user_id'])

        if liker:
            mutual_text = " (взаимный ❤️)" if is_mutual else ""

            # Проверяем, лайкали ли мы уже этого пользователя в ответ
            has_liked_back = await storage.has_liked(user.id, liker.id)

            # Создаем клавиатуру с кнопками только если еще не лайкали в ответ
            if not has_liked_back and not is_mutual:
                like_kb = InlineKeyboardMarkup(inline_keyboard=[
                    [
                        InlineKeyboardButton(text='❤️ Лайкнуть в ответ', callback_data=f'like_back:{liker.id}'),
                        InlineKeyboardButton(text='❌ Пропустить', callback_data=f'skip_like:{liker.id}')
                    ]
                ])
            else:
                like_kb = None

            if liker.photo_file_id:
                await callback.message.answer_photo(
                    photo=liker.photo_file_id,
                    caption=f"{liker_name}, {liker_age}{mutual_text}",
                    reply_markup=like_kb
                )
            else:
                await callback.message.answer(
                    f"{liker_name}, {liker_age}{mutual_text}",
                    reply_markup=like_kb
                )


@router.callback_query(F.data.startswith('like_back:'))
async def like_back_handler(callback: types.CallbackQuery):
    user = await storage.get_user_by_tg(callback.from_user.id)
    to_id = callback.data.split(':', 1)[1]

    has_liked = await storage.has_liked(user.id, to_id)
    if has_liked:
        await callback.answer('Вы уже лайкали этого пользователя.')
        return

    # Ставим лайк в ответ
    like = await storage.add_like(user.id, to_id)

    # Получаем информацию о том, кого лайкнули
    liked_user = await storage.get_user_by_id(to_id)

    if liked_user:
        # Отправляем уведомление о лайке в ответ
        await callback.message.bot.send_message(
            liked_user.tg_id,
            f'❤️ {user.name} поставил вам лайк в ответ!'
        )

    # Проверяем, стал ли лайк взаимным (должен стать взаимным, так как этот пользователь уже лайкал нас)
    if like.is_mutual:
        u_from = await storage.get_user_by_id(user.id)
        u_to = await storage.get_user_by_id(to_id)

        # Сообщение о взаимном лайке (ПОСЛЕДНЕЕ сообщение)
        await callback.message.bot.send_message(
            u_from.tg_id,
            f'🎉 Теперь у вас взаимный лайк с {u_to.name}!'
        )
        await callback.message.bot.send_message(
            u_to.tg_id,
            f'🎉 {u_from.name} ответил взаимностью на ваш лайк!'
        )

        # Кнопки для начала диалога (ПРЕДПОСЛЕДНЕЕ сообщение)
        kb1 = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text='💬 Начать диалог', url=f'tg://user?id={u_to.tg_id}')]
        ])
        kb2 = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text='💬 Начать диалог', url=f'tg://user?id={u_from.tg_id}')]
        ])

        await callback.message.bot.send_message(u_from.tg_id, 'Начните общение:', reply_markup=kb1)
        await callback.message.bot.send_message(u_to.tg_id, 'Начните общение:', reply_markup=kb2)

    await callback.answer('Лайк поставлен ❤️')

    # Отправляем новое сообщение с подтверждением
    if liked_user:
        if like.is_mutual:
            caption = f"Вы поставили взаимный лайк {liked_user.name}! ❤️"
        else:
            caption = f"Вы поставили лайк в ответ {liked_user.name} ❤️"

        await callback.message.answer(caption)


@router.callback_query(F.data.startswith('skip_like:'))
async def skip_like_handler(callback: types.CallbackQuery):
    to_id = callback.data.split(':', 1)[1]
    skipped_user = await storage.get_user_by_id(to_id)

    await callback.answer('Пропущено')

    if skipped_user:
        await callback.message.answer(f"Вы пропустили {skipped_user.name}")


@router.callback_query(F.data.startswith('skip:'))
async def process_skip(callback: types.CallbackQuery):
    user = await storage.get_user_by_tg(callback.from_user.id)

    await callback.answer('Пропущено')

    try:
        await callback.message.delete()
    except:
        pass

    # ВАЖНО: ПОКАЗЫВАЕМ СЛЕДУЮЩУЮ АНКЕТУ ПОСЛЕ ПРОПУСКА
    await show_next_profile(user, callback.message.bot)


async def show_next_profile(user, bot):
    """Показать следующую анкету для просмотра"""
    candidate = await storage.get_next_candidate(user.id)

    if not candidate:
        await bot.send_message(
            user.tg_id,
            'Вы просмотрели все анкеты 👀\n\n'
            'Что дальше?',
            reply_markup=get_main_menu()
        )
        return

    await send_profile_chat(types.User(id=user.tg_id), candidate, bot)


@router.callback_query(F.data == 'stop_search')
async def stop_search(callback: types.CallbackQuery):
    user = await storage.get_user_by_tg(callback.from_user.id)

    if user:
        await callback.message.bot.send_message(
            user.tg_id,
            'Поиск анкет остановлен.\n'
            'Если захотите кого-то найти, нажмите кнопку "🔄 Начать поиск анкет"',
            reply_markup=get_main_menu()
        )

    await callback.answer()


# Дополнительный хэндлер для обработки команды "Остановить поиск"
@router.message(F.text == "⏹️ Остановить поиск")
async def stop_search_command(message: types.Message):
    await message.answer(
        'Поиск анкет остановлен.\n'
        'Если захотите кого-то найти, нажмите кнопку "🔄 Начать поиск анкет"',
        reply_markup=get_main_menu()
    )


@router.callback_query(F.data == 'refill')
async def refill_profile(callback: types.CallbackQuery):
    await callback.message.answer(
        'Чтобы перезаполнить анкету, используйте:\n'
        '/start -> 📌 Создать анкету'
    )
    await callback.answer()


@router.callback_query(F.data == 'continue')
async def continue_browsing(callback: types.CallbackQuery):
    user = await storage.get_user_by_tg(callback.from_user.id)
    await callback.answer()

    if user:
        candidate = await storage.get_next_candidate(user.id)
        if candidate:
            await send_profile_chat(callback.from_user, candidate, callback.message.bot)
        else:
            await callback.message.answer(
                'Нет новых анкет для просмотра 👀\n\n'
                'Что дальше?',
                reply_markup=get_main_menu()
            )
    else:
        await callback.message.answer('Сначала создайте анкету: /start')
